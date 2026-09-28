"""Breakeven + trailing ATR + alvo dinâmico — consolidação da linha DeepSeek.

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).
O "v04" no nome é numeração própria deste autor, NÃO a VERSAO do projeto
(versionamento.py, hoje V455) e NÃO sequencial com saida_chatgpt_v3 —
autores diferentes, contadores independentes (Regra 6).

Regra 11.2 — declaração de variações testadas nesta linha:
  v01 (conceitual): breakeven 1.0R + trailing 0.75×ATR armado em 1.5R +
                    alvo fixo 1.55R.
  v02 (conceitual): breakeven precoce em 0.8R + alvo dinâmico por ATR.
  v03 (conceitual): breakeven 1.0R + trailing 0.75×ATR + trava de fim de
                    pregão (mesma fórmula da saida_chatgpt_v3).
  v04 (esta): consolida o que sobreviveu das três anteriores — breakeven
              1.0R (evita stop prematuro em ruído), trailing 0.75×ATR
              armado em 1.5R (deixa tendência respirar), alvo dinâmico
              que cresce 0.40×ATR quando MFE já passou de 1.2R (captura
              dias de tendência forte), trava de fim de pregão idêntica
              à do titular. Nenhuma variação foi rodada contra o bloco
              de Validação ainda — os números são convenção pública de
              gestão de risco, não ajuste contra o dataset.

Regra 11.3 — nenhuma lógica depende de data específica, evento de
calendário ou preço absoluto do WINFUT. "17:15" é corte operacional
genérico de fim de pregão (mesmo já usado por outros cartuchos do
laboratório). Todos os níveis são derivados de row["ohlc_recentes"],
ATR corrente e estado da posição.

Regra 3 — sem I/O, sem rede, sem import de qualquer módulo do projeto
(inclusive configuracao.py). Todas as constantes abaixo são cópias
explícitas e documentadas.

Regra 1 v8 — este cartucho é o ÚNICO responsável pelo stop e pelo alvo
da posição desde a abertura. O motor não calcula nem garante nenhum piso
de segurança. Se este arquivo falhar em definir um nível, a posição
fica sem proteção de preço até o corte de horário — responsabilidade
inteira do cartucho, conforme a Regra 1.
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
GATILHO_ALVO_EXTRA_R = 1.2
ALVO_EXTRA_ATR = 0.40
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


def _janela_estrutural(row):
    """Últimos SWING_LOOKBACK_CANDLES+1 candles fechados, ou None."""
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        return None
    return janela


def _protecao_inicial(row, posicao):
    """Stop estrutural + alvo em RR fixo — definidos uma única vez na abertura.

    Mesma fórmula do baseline e da saida_chatgpt_v3 (extraída da janela
    de candles fechados em row["ohlc_recentes"]), para que a abertura
    deste cartucho seja comportamentalmente idêntica ao titular atual.
    """
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = _janela_estrutural(row)
    if janela is None:
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
    """Reconstrói o risco estrutural a cada candle — o cartucho é stateless
    por design (Regra 3: nada de estado global acumulando candles)."""
    janela = _janela_estrutural(row)
    if janela is None:
        return None
    if lado == "COMPRA":
        risco = entrada - min(float(c["Minimo"]) for c in janela)
    else:
        risco = max(float(c["Maximo"]) for c in janela) - entrada
    return risco if risco > 0 else None


def avaliar_saida(row, posicao):
    """Contrato oficial da Regra 1 v8: dict com fechar/novo_stop/novo_alvo.

    Fluxo por candle:
      candles == 0  → abertura: stop estrutural + alvo 1.55R (fixados).
      candles > 0   → mantém alvo base; breakeven em +1.0R; trailing
                      0.75×ATR armado em +1.5R (nunca abaixo do breakeven);
                      alvo cresce +0.40×ATR se MFE ≥ 1.2R; trava de fim
                      de pregão após 17:15 (mesma fórmula do titular).
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

    # --- Stop: breakeven ou trailing, nunca afrouxa ---
    novo_stop = None
    if r_mfe >= GATILHO_TRAILING_R and mfe is not None:
        candidato = (mfe - ATR_TRAILING * atr) if lado == "COMPRA" \
                    else (mfe + ATR_TRAILING * atr)
        if lado == "COMPRA":
            novo_stop = max(candidato, entrada)
        else:
            novo_stop = min(candidato, entrada)
    elif r_mfe >= GATILHO_BREAKEVEN_R:
        novo_stop = entrada

    # --- Alvo: base 1.55R, cresce +0.40×ATR se MFE já passou de 1.2R ---
    alvo_candidato = (entrada + RELACAO_RISCO_RETORNO * risco_original) \
                     if lado == "COMPRA" \
                     else (entrada - RELACAO_RISCO_RETORNO * risco_original)
    if r_mfe >= GATILHO_ALVO_EXTRA_R and atr > 0:
        extra = ALVO_EXTRA_ATR * atr
        alvo_candidato = (alvo_candidato + extra) if lado == "COMPRA" \
                         else (alvo_candidato - extra)

    # --- Trava de fim de pregão (mesma fórmula da saida_chatgpt_v3) ---
    fechar = False
    hora = _horario(row)
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    if hora is not None and hora >= HORARIO_INICIO_PROTECAO:
        limite = max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR_PERDA * atr)
        fechar = resultado <= -limite

    return {
        "fechar": bool(fechar),
        "novo_stop": novo_stop,
        "novo_alvo": alvo_candidato,
    }


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