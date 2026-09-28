"""Breakeven + trailing ATR com trava de fim de pregão — candidata de saída.

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).

Regra 6 — o "v1" no nome é numeração própria deste autor, não a VERSAO do
projeto (versionamento.py).

Regra 11.2 — declaração de variações testadas:
  Esta é a 1ª submissão formal desta ideia ao laboratório. Os gatilhos
  (1.0R para breakeven, 1.5R para armar trailing, 0.75×ATR de trailing)
  são valores de convenção pública de gestão de risco, não ajustados
  contra o dataset oficial. Variações de limiar dentro do bloco de
  Desenvolvimento ainda não foram rodadas.

Regra 11.3 — nenhuma lógica depende de data específica, evento ou preço
absoluto. O horário 17:15 é um corte operacional de fim de pregão (mesmo
espírito da saida_chatgpt_v3), não uma dependência do dataset. Todos os
níveis são calculados a partir de row["ohlc_recentes"], ATR corrente e
estado da posição — nada fixo em pontos.

Regra 3 — sem I/O, sem rede, sem import de qualquer módulo do projeto
(inclusive configuracao.py). Constantes copiadas explicitamente.

Regra 1 v8 — este cartucho é o ÚNICO responsável pelo stop/alvo da posição
desde a abertura. O motor não calcula nada. A abertura define o stop
estrutural + alvo 1.55R; candles seguintes só reconfiguram stop por
breakeven/trailing — nunca afrouxam, nunca inventam alvo novo.
"""

from math import isfinite

# ---------------------------------------------------------------------------
# Constantes copiadas (Regra 3: nunca importadas de configuracao.py)
# ---------------------------------------------------------------------------
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
GATILHO_BREAKEVEN_R = 1.0
GATILHO_TRAILING_R = 1.5
ATR_TRAILING = 0.75
HORARIO_INICIO_PROTECAO = "17:15"
PERDA_MINIMA_PONTOS = 275.0
MULTIPLICADOR_ATR_PERDA = 0.25


def _numero_finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _horario(row):
    valor = row.get("dt")
    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except (TypeError, ValueError):
            return None
    return None


def _protecao_inicial(row, posicao):
    """Stop estrutural + alvo em RR fixo, definidos uma única vez na abertura."""
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")

    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
        risco = stop - entrada
        alvo = entrada - RELACAO_RISCO_RETORNO * risco
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if risco <= 0 or not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Proteção inicial inválida para {lado}.")
    return stop, alvo, risco


def _risco_original(row, lado, entrada):
    """Risco estrutural reconstruído a cada candle — o cartucho é stateless
    por design (Regra 3: nada de estado global acumulando candles)."""
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        return None
    if lado == "COMPRA":
        risco = entrada - min(float(c["Minimo"]) for c in janela)
    else:
        risco = max(float(c["Maximo"]) for c in janela) - entrada
    return risco if risco > 0 else None


def avaliar_saida(row, posicao):
    """Contrato oficial da Regra 1 v8: devolve dict com fechar/novo_stop/novo_alvo.

    Fluxo:
      candles == 0  → abertura: stop estrutural + alvo 1.55R (fixados).
      candles > 0   → mantém alvo; reconfigura stop por breakeven/trailing;
                      aplica trava de fim de pregão após 17:15.
    """
    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")

    if candles == 0:
        stop, alvo, _ = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    risco_original = _risco_original(row, lado, entrada)
    if risco_original is None:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    if lado == "COMPRA":
        mfe = _numero_finito(posicao.get("maxima_desde_entrada"))
        ganho_mfe = (mfe - entrada) if mfe is not None else 0.0
    else:
        mfe = _numero_finito(posicao.get("minima_desde_entrada"))
        ganho_mfe = (entrada - mfe) if mfe is not None else 0.0

    r_mfe = ganho_mfe / risco_original
    atr = _numero_finito(row.get("atr")) or 0.0
    novo_stop = None

    if r_mfe >= GATILHO_TRAILING_R and mfe is not None:
        candidato = (mfe - ATR_TRAILING * atr) if lado == "COMPRA" \
                    else (mfe + ATR_TRAILING * atr)
        # Nunca pior que breakeven — o trailing nunca afrouxa por trás.
        if lado == "COMPRA":
            novo_stop = max(candidato, entrada)
        else:
            novo_stop = min(candidato, entrada)
    elif r_mfe >= GATILHO_BREAKEVEN_R:
        novo_stop = entrada

    fechar = False
    hora = _horario(row)
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    if hora is not None and hora >= HORARIO_INICIO_PROTECAO:
        limite = max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR_PERDA * atr)
        fechar = resultado <= -limite

    return {"fechar": bool(fechar), "novo_stop": novo_stop, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    """Explicação textual usada pela narração de fechamento (V440)."""
    decisao = avaliar_saida(row, posicao)
    if not decisao["fechar"]:
        return None
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    return (
        "Proteção de fim de pregão acionada: a posição permaneceu negativa "
        f"e atingiu {abs(resultado):.0f} pontos de perda."
    )


__all__ = ["avaliar_saida", "diagnosticar_saida"]