"""Rompimento confirmado da faixa de abertura — ChatGPT v1.

Autoria: ChatGPT (OpenAI), a pedido de Marcio Soares. Revisao humana e do
conselho: pendentes. ``v1`` e a versao propria deste cartucho, nao a VERSAO
do projeto.

Hipotese: dias direcionais frequentemente deixam uma faixa inicial curta e
continuam quando o primeiro candle fecha alem dela com tendencia, momento e
geometria coerentes. A faixa usa somente candles fechados do proprio pregao.

Variacoes relevantes testadas antes da submissao (Regra 11.2): nenhuma. Esta
e a primeira formulacao; os limites foram definidos antes do ranking oficial.
Sem dependencia de data, evento ou preco absoluto (Regra 11.3).
Resultado financeiro: ainda nao medido; aguarda revisao do PR (Regra 12).
"""

HORA_INICIO_FAIXA = "09:00"
HORA_FIM_FAIXA = "10:00"
HORA_FIM_ENTRADA = "12:30"
MIN_CANDLES_FAIXA = 3
SEPARACAO_MIN_ATR = 0.20
EXCESSO_MIN_ATR = 0.05
EXCESSO_MAX_ATR = 0.75
CORPO_MINIMO = 0.50
FECHAMENTO_FORTE = 0.70
RSI_COMPRA = (53.0, 74.0)
RSI_VENDA = (26.0, 47.0)


def _finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero == numero and abs(numero) != float("inf") else None


def _sessao(row):
    dt = row.get("dt")
    if not hasattr(dt, "date"):
        return []
    dia = dt.date()
    return [
        candle for candle in (row.get("ohlc_recentes") or ())
        if isinstance(candle, dict)
        and hasattr(candle.get("dt"), "date")
        and candle["dt"].date() == dia
    ]


def gerar_sinal(row) -> int:
    if not isinstance(row, dict):
        raise TypeError("row precisa ser um dicionario")
    dt = row.get("dt")
    if not hasattr(dt, "strftime"):
        return 0
    hora = dt.strftime("%H:%M")
    if not (HORA_FIM_FAIXA <= hora <= HORA_FIM_ENTRADA):
        return 0

    sessao = _sessao(row)
    faixa = [
        c for c in sessao
        if HORA_INICIO_FAIXA <= c["dt"].strftime("%H:%M") < HORA_FIM_FAIXA
    ]
    entre_faixa_e_atual = [
        c for c in sessao
        if HORA_FIM_FAIXA <= c["dt"].strftime("%H:%M") < hora
    ]
    if len(faixa) < MIN_CANDLES_FAIXA:
        return 0

    campos = (
        _finito(row.get("Abertura")), _finito(row.get("Maximo")),
        _finito(row.get("Minimo")), _finito(row.get("Fechamento")),
        _finito(row.get("MA21")), _finito(row.get("MA50")),
        _finito(row.get("atr")), _finito(row.get("rsi")),
        _finito(row.get("macd")), _finito(row.get("macd_signal")),
    )
    if any(v is None for v in campos):
        return 0
    abertura, maxima, minima, fechamento, ma21, ma50, atr, rsi, macd, macd_signal = campos
    if atr <= 0 or maxima <= minima:
        return 0

    try:
        topo = max(float(c["Maximo"]) for c in faixa)
        fundo = min(float(c["Minimo"]) for c in faixa)
        fechamentos_anteriores = [float(c["Fechamento"]) for c in entre_faixa_e_atual]
    except (KeyError, TypeError, ValueError):
        return 0

    # Apenas o primeiro fechamento fora da faixa participa. Assim o cartucho
    # nao persegue o mercado depois que a oportunidade original passou.
    if any(f > topo or f < fundo for f in fechamentos_anteriores):
        return 0

    amplitude = maxima - minima
    corpo = abs(fechamento - abertura) / amplitude
    local = (fechamento - minima) / amplitude
    separacao = abs(ma21 - ma50) / atr
    if corpo < CORPO_MINIMO or separacao < SEPARACAO_MIN_ATR:
        return 0

    excesso_compra = (fechamento - topo) / atr
    if (
        row.get("trend") == 1
        and EXCESSO_MIN_ATR <= excesso_compra <= EXCESSO_MAX_ATR
        and fechamento > abertura and local >= FECHAMENTO_FORTE
        and RSI_COMPRA[0] <= rsi <= RSI_COMPRA[1]
        and macd > macd_signal
    ):
        return 1

    excesso_venda = (fundo - fechamento) / atr
    if (
        row.get("trend") == -1
        and EXCESSO_MIN_ATR <= excesso_venda <= EXCESSO_MAX_ATR
        and fechamento < abertura and local <= 1.0 - FECHAMENTO_FORTE
        and RSI_VENDA[0] <= rsi <= RSI_VENDA[1]
        and macd < macd_signal
    ):
        return -1
    return 0


__all__ = ["gerar_sinal"]
