"""Entrada Rompimento — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Entra a favor da tendência quando o fechamento rompe o topo (ou o fundo) dos
três candles anteriores do mesmo pregão, com corpo forte, fechamento no
extremo do candle, RSI e estocástico confirmando.

Origem: Porta 4 de estrategia/entrada/entrada_manus_v1.py (autoria Manus). Extração LITERAL: nenhum limiar, horário ou condição foi
alterado. Isola uma única ideia que hoje só existe combinada com outras num
agregador; não duplica nenhum arquivo existente (Regra 6) porque, sozinha, ela
produz sinais diferentes dos do agregador.
Variações testadas antes desta versão (Regra 11.2): nenhuma.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""


ROMPIMENTO_LOOKBACK = 3
ROMPIMENTO_DISTANCIA_MIN = 90.0
ROMPIMENTO_DISTANCIA_MAX = 260.0
ROMPIMENTO_SEPARACAO_MIN = 175.0
ROMPIMENTO_ATR_REL_MIN = 0.75
ROMPIMENTO_ATR_REL_MAX = 1.60
ROMPIMENTO_CORPO_MIN = 0.55
ROMPIMENTO_FECHAMENTO_EXTREMO = 0.75
ROMPIMENTO_RSI_COMPRA = 55.0
ROMPIMENTO_RSI_VENDA = 45.0
ROMPIMENTO_STOCH_COMPRA_MIN = 50.0
ROMPIMENTO_STOCH_COMPRA_MAX = 88.0
ROMPIMENTO_STOCH_VENDA_MIN = 12.0
ROMPIMENTO_STOCH_VENDA_MAX = 50.0


def _candles_anteriores_do_pregao(row):
    """Os três candles fechados anteriores, sem atravessar o pregão."""
    ohlc = row.get("ohlc_recentes") or ()
    dt_atual = row.get("dt")
    if dt_atual is None or len(ohlc) < ROMPIMENTO_LOOKBACK + 1:
        return ()
    data_atual = dt_atual.date()
    anteriores = []
    for candle in ohlc[:-1]:
        dt_candle = candle.get("dt")
        if dt_candle is not None and dt_candle.date() == data_atual:
            anteriores.append(candle)
    return tuple(anteriores[-ROMPIMENTO_LOOKBACK:])


def gerar_sinal(row) -> int:
    tendencia = int(row["trend"])
    if tendencia == 0:
        return 0
    hora = row["dt"].strftime("%H:%M")
    amplitude = float(row["Maximo"]) - float(row["Minimo"])
    corpo = abs(float(row["Fechamento"]) - float(row["Abertura"]))
    separacao_medias = abs(float(row["MA21"]) - float(row["MA50"]))

    anteriores = _candles_anteriores_do_pregao(row)
    rsi = float(row.get("rsi", 50.0))
    atr_relativo = float(row["atr_relativo"])
    distancia_ma21 = float(row["distancia_ma21"])
    fechamento = float(row["Fechamento"])
    abertura = float(row["Abertura"])
    minimo = float(row["Minimo"])
    maximo = float(row["Maximo"])
    stoch = float(row["stoch"])

    horario_valido = not ("11:45" <= hora <= "13:15" or hora >= "17:15")
    regime_valido = (
        len(anteriores) == ROMPIMENTO_LOOKBACK
        and horario_valido
        and ROMPIMENTO_DISTANCIA_MIN <= distancia_ma21 <= ROMPIMENTO_DISTANCIA_MAX
        and separacao_medias >= ROMPIMENTO_SEPARACAO_MIN
        and ROMPIMENTO_ATR_REL_MIN <= atr_relativo <= ROMPIMENTO_ATR_REL_MAX
        and amplitude > 0.0
        and corpo >= ROMPIMENTO_CORPO_MIN * amplitude
    )
    if not regime_valido:
        return 0

    topo_anterior = max(float(c["Maximo"]) for c in anteriores)
    fundo_anterior = min(float(c["Minimo"]) for c in anteriores)
    posicao_fechamento = (fechamento - minimo) / amplitude

    if (
        tendencia == 1
        and fechamento > topo_anterior
        and fechamento > abertura
        and posicao_fechamento >= ROMPIMENTO_FECHAMENTO_EXTREMO
        and rsi >= ROMPIMENTO_RSI_COMPRA
        and ROMPIMENTO_STOCH_COMPRA_MIN <= stoch <= ROMPIMENTO_STOCH_COMPRA_MAX
        and row["stoch_subindo"]
    ):
        return 1
    if (
        tendencia == -1
        and fechamento < fundo_anterior
        and fechamento < abertura
        and posicao_fechamento <= 1.0 - ROMPIMENTO_FECHAMENTO_EXTREMO
        and rsi <= ROMPIMENTO_RSI_VENDA
        and ROMPIMENTO_STOCH_VENDA_MIN <= stoch <= ROMPIMENTO_STOCH_VENDA_MAX
        and row["stoch_descendo"]
    ):
        return -1
    return 0
