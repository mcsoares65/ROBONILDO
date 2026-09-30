"""Saída por confluência de indicadores — realiza lucro em reversão confirmada.

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).
O "v04" no nome é numeração própria deste autor, NÃO a VERSAO do projeto
(versionamento.py, hoje V457) e NÃO sequencial com a saida_chatgpt_v4 —
autores diferentes, contadores independentes (Regra 6).

Regra 11.2 — declaração de variações testadas nesta linha:
  v01 (conceitual): breakeven em 1.0R + trailing 0.75×ATR armado em 1.5R.
  v02 (conceitual): breakeven precoce em 0.8R + alvo dinâmico por ATR.
  v03 (conceitual): breakeven 1.0R + trailing 0.75×ATR + alvo que cresce
                    0.40×ATR quando MFE passa de 1.2R.
  v04 (esta): mudança de família. As três anteriores mexiam no STOP
              (localização de risco) e todas foram refutadas pelo padrão
              dos 46 testes do documento C — qualquer stop que se move
              perde para o stop estrutural fixo. Esta versão NÃO toca no
              stop depois da abertura. Ela fecha a posição quando a
              reversão é confirmada por indicadores, mantendo o stop
              estrutural intacto. É família diferente, não iteracão da
              anterior.

Regra 11.3 — nenhuma lógica depende de data específica, evento de
calendário ou preço absoluto do WINFUT. Todos os gatilhos usam campos de
`row` que já existem no construir_row() do motor.

Regra 3 — sem I/O, sem rede, sem import de módulo do projeto (inclusive
configuracao.py). Todas as constantes são cópias explícitas.

Regra 1 v8 — este cartucho é o ÚNICO responsável pelo stop e pelo alvo da
posição desde a abertura. O motor não calcula nem garante piso de segurança.

Motivação medida: a saida_chatgpt_v4 (titular atual) só reage a horário e
perda flutuante — é cega ao estado do mercado. Operação real de 30/09/2026
(COMPRA @ 187720, 14:15): a posição chegou a +205 pts às 15:01 e devolveu
236 pts sem que o cartucho titular fizesse nada. Este cartucho olha para o
mercado e fecha quando a reversão é confirmada por pelo menos 2 dos 3
indicadores, sem tocar no stop nem no alvo.
"""

from math import isfinite

# ---------------------------------------------------------------------------
# Constantes copiadas (Regra 3: nunca importadas de configuracao.py)
# ---------------------------------------------------------------------------
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
HORARIO_INICIO_PROTECAO = "17:15"
PERDA_MINIMA_PONTOS = 275.0
MULTIPLICADOR_ATR_PERDA = 0.25
CONFLUENCIA_MINIMA = 2  # de 3 indicadores


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
    """Stop estrutural + alvo 1,55R, definidos uma única vez na abertura.

    Mesma fórmula do baseline e da saida_chatgpt_v4 (extraída da janela de
    candles fechados em row["ohlc_recentes"]), para que a abertura deste
    cartucho seja comportamentalmente idêntica ao titular atual. Nada muda
    na abertura — o que muda é o que acontece nos candles seguintes.
    """
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para proteção inicial.")

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
        raise ValueError("Proteção inicial inválida.")
    return stop, alvo


def _indicadores_contra(row, lado):
    """Devolve quantos dos 3 indicadores confirmam reversão contra a posição.

    Lado COMPRA → reversão é sinal de baixa:
      - MACD cruzou para baixo (macd_cross_down).
      - Estocástico saiu da zona de sobrecompra (stoch_cross_down_80).
      - RSI está caindo (rsi_descendo).

    Lado VENDA → reversão é sinal de alta:
      - MACD cruzou para cima (macd_cross_up).
      - Estocástico saiu da zona de sobrevenda (stoch_cross_up_20).
      - RSI está subindo (rsi_subindo).
    """
    contagem = 0

    if lado == "COMPRA":
        if bool(row.get("macd_cross_down")):
            contagem += 1
        if bool(row.get("stoch_cross_down_80")):
            contagem += 1
        if bool(row.get("rsi_descendo")):
            contagem += 1
    else:
        if bool(row.get("macd_cross_up")):
            contagem += 1
        if bool(row.get("stoch_cross_up_20")):
            contagem += 1
        if bool(row.get("rsi_subindo")):
            contagem += 1

    return contagem


def _limite_perda_fim_pregiao(atr):
    return max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR_PERDA * atr)


def avaliar_saida(row, posicao):
    """Contrato oficial da Regra 1 v8: dict com fechar/novo_stop/novo_alvo.

    Fluxo por candle:
      candles == 0  → abertura: stop estrutural + alvo 1.55R (fixados).
      candles > 0   → NÃO toca no stop nem no alvo. Só decide se fecha:
                       (a) trava de fim de pregão (idêntica ao titular), ou
                       (b) reversão confirmada por >=2 de 3 indicadores,
                           se a posição está no lucro.
    """
    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")

    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    lado = str(posicao["lado"]).upper()
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    atr = _numero_finito(row.get("atr")) or 0.0

    # Trava de fim de pregão — mesma fórmula da saida_chatgpt_v4
    fechar_por_horario = False
    hora = _horario(row)
    if hora is not None and hora >= HORARIO_INICIO_PROTECAO:
        limite = _limite_perda_fim_pregiao(atr)
        fechar_por_horario = resultado <= -limite

    # Fechamento por reversão confirmada — só quando a posição está no lucro.
    # Não olha stop nem alvo: o stop estrutural continua onde está.
    fechar_por_reversao = False
    if not fechar_por_horario and resultado > 0:
        contra = _indicadores_contra(row, lado)
        fechar_por_reversao = contra >= CONFLUENCIA_MINIMA

    return {
        "fechar": bool(fechar_por_horario or fechar_por_reversao),
        "novo_stop": None,
        "novo_alvo": None,
    }


def diagnosticar_saida(row, posicao):
    """Explicação textual usada pela narração de fechamento (V440)."""
    candles = _numero_finito(posicao.get("candles_decorridos")) or 0
    if candles == 0:
        return None

    lado = str(posicao["lado"]).upper()
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0

    # Trava de fim de pregão tem precedência na explicação
    hora = _horario(row)
    atr = _numero_finito(row.get("atr")) or 0.0
    if hora is not None and hora >= HORARIO_INICIO_PROTECAO:
        limite = _limite_perda_fim_pregiao(atr)
        if resultado <= -limite:
            return (
                "Proteção de fim de pregão acionada: a posição permaneceu "
                f"negativa e atingiu {abs(resultado):.0f} pontos de perda."
            )

    # Reversão confirmada — só se a posição está no lucro
    if resultado > 0:
        contra = _indicadores_contra(row, lado)
        if contra >= CONFLUENCIA_MINIMA:
            return (
                f"Reversão confirmada por {contra} de 3 indicadores contra a "
                f"posição. Realizando lucro de {resultado:.0f} pts antes que "
                f"devolva."
            )
    return None


__all__ = ["avaliar_saida", "diagnosticar_saida"]