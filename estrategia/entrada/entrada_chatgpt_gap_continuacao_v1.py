"""Continuacao confirmada de gap intradiario — ChatGPT v1.

Autoria: ChatGPT (OpenAI), a pedido de Marcio Soares. Revisao humana e do
conselho: pendentes. ``v1`` e a versao propria deste cartucho.

Hipotese: um gap moderado contra o fechamento do pregao anterior, quando nao e
preenchido e recebe confirmacao direcional nos primeiros candles, pode produzir
uma perna que as tres portas baseadas em MA/estocastico nao isolam.

Variacoes relevantes testadas antes da submissao (Regra 11.2): nenhuma.
Sem dependencia de data, evento ou preco absoluto (Regra 11.3).
Resultado financeiro: ainda nao medido; aguarda revisao do PR (Regra 12).
"""

GAP_MIN_ATR = 0.35
GAP_MAX_ATR = 1.60
MIN_CANDLES_ATUAIS = 3
HORA_INICIO = "09:30"
HORA_FIM = "11:30"
CORPO_MINIMO = 0.45
FECHAMENTO_FORTE = 0.65


def _finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero == numero and abs(numero) != float("inf") else None


def gerar_sinal(row) -> int:
    if not isinstance(row, dict):
        raise TypeError("row precisa ser um dicionario")
    dt = row.get("dt")
    if not hasattr(dt, "date") or not hasattr(dt, "strftime"):
        return 0
    hora = dt.strftime("%H:%M")
    if not (HORA_INICIO <= hora <= HORA_FIM):
        return 0

    janela = row.get("ohlc_recentes") or ()
    dia = dt.date()
    atuais = [c for c in janela if hasattr(c.get("dt"), "date") and c["dt"].date() == dia]
    anteriores = [c for c in janela if hasattr(c.get("dt"), "date") and c["dt"].date() < dia]
    if len(atuais) < MIN_CANDLES_ATUAIS or not anteriores:
        return 0

    try:
        fechamento_anterior = float(anteriores[-1]["Fechamento"])
        abertura_dia = float(atuais[0]["Abertura"])
        abertura = float(row["Abertura"])
        maxima = float(row["Maximo"])
        minima = float(row["Minimo"])
        fechamento = float(row["Fechamento"])
        maximas_confirmacao = [float(c["Maximo"]) for c in atuais[:-1]]
        minimas_confirmacao = [float(c["Minimo"]) for c in atuais[:-1]]
    except (KeyError, TypeError, ValueError):
        return 0

    atr = _finito(row.get("atr"))
    rsi = _finito(row.get("rsi"))
    macd = _finito(row.get("macd"))
    macd_signal = _finito(row.get("macd_signal"))
    if any(v is None for v in (atr, rsi, macd, macd_signal)) or atr <= 0 or maxima <= minima:
        return 0

    gap = (abertura_dia - fechamento_anterior) / atr
    if not (GAP_MIN_ATR <= abs(gap) <= GAP_MAX_ATR):
        return 0
    amplitude = maxima - minima
    corpo = abs(fechamento - abertura) / amplitude
    local = (fechamento - minima) / amplitude
    if corpo < CORPO_MINIMO:
        return 0

    # Confirmacao somente no primeiro fechamento que supera os candles ja
    # formados no dia; o gap precisa continuar aberto no momento do sinal.
    if (
        gap > 0 and row.get("trend") == 1
        and fechamento > max(maximas_confirmacao)
        and min(float(c["Minimo"]) for c in atuais) > fechamento_anterior
        and fechamento > abertura and local >= FECHAMENTO_FORTE
        and rsi >= 54.0 and macd > macd_signal
    ):
        return 1
    if (
        gap < 0 and row.get("trend") == -1
        and fechamento < min(minimas_confirmacao)
        and max(float(c["Maximo"]) for c in atuais) < fechamento_anterior
        and fechamento < abertura and local <= 1.0 - FECHAMENTO_FORTE
        and rsi <= 46.0 and macd < macd_signal
    ):
        return -1
    return 0


__all__ = ["gerar_sinal"]
