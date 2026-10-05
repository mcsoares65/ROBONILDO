"""Liberacao de compressao com rompimento direcional — ChatGPT v1.

Autoria: ChatGPT (OpenAI), a pedido de Marcio Soares. Revisao humana e do
conselho: pendentes. ``v1`` e a versao propria deste cartucho.

Hipotese: quando oito candles permanecem numa faixa curta em multiplos de ATR,
o primeiro fechamento alem da estrutura, com corpo forte e confirmacao de
MA/RSI/MACD, pode iniciar uma perna direcional independente das portas atuais.

Variacoes relevantes testadas antes da submissao (Regra 11.2): nenhuma.
Sem dependencia de data, evento ou preco absoluto (Regra 11.3).
Resultado financeiro: ainda nao medido; aguarda revisao do PR (Regra 12).
"""

JANELA_COMPRESSAO = 8
FAIXA_MAX_ATR = 2.40
ROMPIMENTO_MIN_ATR = 0.05
ROMPIMENTO_MAX_ATR = 0.80
AMPLITUDE_CANDLE_MIN_ATR = 0.65
CORPO_MINIMO = 0.55
FECHAMENTO_FORTE = 0.72
ATR_RELATIVO = (0.70, 1.45)
HORA_INICIO = "10:00"
HORA_FIM = "17:30"


def _finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero == numero and abs(numero) != float("inf") else None


def _ohlc(candle):
    if not isinstance(candle, dict):
        return None
    valores = tuple(_finito(candle.get(k)) for k in ("Abertura", "Maximo", "Minimo", "Fechamento"))
    return None if any(v is None for v in valores) else valores


def gerar_sinal(row) -> int:
    if not isinstance(row, dict):
        raise TypeError("row precisa ser um dicionario")
    dt = row.get("dt")
    hora = dt.strftime("%H:%M") if hasattr(dt, "strftime") else ""
    if not (HORA_INICIO <= hora <= HORA_FIM):
        return 0

    bruto = row.get("ohlc_recentes") or ()
    if len(bruto) < JANELA_COMPRESSAO + 1:
        return 0
    anteriores = [_ohlc(c) for c in bruto[-(JANELA_COMPRESSAO + 1):-1]]
    atual = _ohlc(bruto[-1])
    if atual is None or any(c is None for c in anteriores):
        return 0

    atr = _finito(row.get("atr"))
    atr_rel = _finito(row.get("atr_relativo"))
    rsi = _finito(row.get("rsi"))
    macd = _finito(row.get("macd"))
    macd_signal = _finito(row.get("macd_signal"))
    ma21 = _finito(row.get("MA21"))
    ma50 = _finito(row.get("MA50"))
    if any(v is None for v in (atr, atr_rel, rsi, macd, macd_signal, ma21, ma50)) or atr <= 0:
        return 0
    if not (ATR_RELATIVO[0] <= atr_rel <= ATR_RELATIVO[1]):
        return 0

    topo = max(c[1] for c in anteriores)
    fundo = min(c[2] for c in anteriores)
    if (topo - fundo) / atr > FAIXA_MAX_ATR:
        return 0

    abertura, maxima, minima, fechamento = atual
    amplitude = maxima - minima
    if amplitude <= 0 or amplitude / atr < AMPLITUDE_CANDLE_MIN_ATR:
        return 0
    corpo = abs(fechamento - abertura) / amplitude
    local = (fechamento - minima) / amplitude
    if corpo < CORPO_MINIMO:
        return 0

    excesso_compra = (fechamento - topo) / atr
    if (
        row.get("trend") == 1 and ma21 > ma50
        and ROMPIMENTO_MIN_ATR <= excesso_compra <= ROMPIMENTO_MAX_ATR
        and fechamento > abertura and local >= FECHAMENTO_FORTE
        and rsi >= 53.0 and macd > macd_signal
    ):
        return 1

    excesso_venda = (fundo - fechamento) / atr
    if (
        row.get("trend") == -1 and ma21 < ma50
        and ROMPIMENTO_MIN_ATR <= excesso_venda <= ROMPIMENTO_MAX_ATR
        and fechamento < abertura and local <= 1.0 - FECHAMENTO_FORTE
        and rsi <= 47.0 and macd < macd_signal
    ):
        return -1
    return 0


__all__ = ["gerar_sinal"]
