"""Candidata Gabriel: Momentum Expansion v3 — compra.

Autoria: Gabriel (fonte original do ZIP) / adaptação Manus; revisão humana
pendente. Esta é uma candidata independente, não titular, e a numeração ``v3``
é a contagem própria da hipótese, não a VERSAO do projeto. Variações testadas
antes desta versão: 0. Resultado oficial ainda não medido.

A porta foi portada de ``gen3/momentum_expansion_v3.py`` sem imports do
projeto, I/O, rede, arquivo, estado global acumulado, ``exec`` ou ``eval``.
A hipótese original é long-only e exige 60 candles anteriores, volume anômalo
(z-score de 30), corpo >= 0,70 ATR, rompimento da máxima de 10 candles,
fechamento acima da VWAP da sessão e extensão <= 1,50 ATR sobre a EMA20.

Assunção explícita de quantidade: ``Quantidade`` por candle é usada como o
volume compatível com ``Bar.volume`` da fonte. O motor V465 fornece no máximo
96 barras e o timeframe V465 é de 15 minutos; isso cobre a sessão de 09:00 a
18:15 para reconstruir a VWAP causalmente da janela. Se qualquer Quantidade
necessária estiver ausente (``None``), a função devolve 0; ausência nunca é
substituída por zero. O risco da fonte (orçamento R$20 / ponto R$0,20) também
é preservado: sinais cujo stop arredondado exceda 100 pontos são suprimidos.

Contrato: ``gerar_sinal(row) -> -1 | 0 | 1``. A saída de risco/alvo da fonte
foi separada em ``saida_gabriel_momentum_expansion_v3.py``.
"""

from decimal import Decimal, ROUND_CEILING, InvalidOperation
from statistics import pstdev


ZERO = Decimal("0")
TICK = Decimal("5")
Z_PERIOD = 30
ATR_PERIOD = 20
BREAKOUT_LOOKBACK = 10
EMA_SOURCE_BARS = 60
MIN_VOLUME_Z = Decimal("1.50")
MIN_BODY_ATR = Decimal("0.70")
MAX_EXTENSION_ATR = Decimal("1.50")
MAX_STOP_POINTS = Decimal("100")  # R$20,00 / R$0,20 por ponto, cópia da fonte


def _decimal(value):
    """Converte um valor finito sem transformar dado ausente em zero."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() else None


def _bar(value):
    if not isinstance(value, dict):
        return None
    dt = value.get("dt")
    if dt is None or not hasattr(dt, "date"):
        return None
    abertura = _decimal(value.get("Abertura"))
    maxima = _decimal(value.get("Maximo"))
    minima = _decimal(value.get("Minimo"))
    fechamento = _decimal(value.get("Fechamento"))
    if None in (abertura, maxima, minima, fechamento):
        return None
    quantidade = None
    if "Quantidade" in value and value["Quantidade"] is not None:
        quantidade = _decimal(value["Quantidade"])
        if quantidade is None or quantidade < ZERO:
            return None
    return {
        "dt": dt,
        "open": abertura,
        "high": maxima,
        "low": minima,
        "close": fechamento,
        "volume": quantidade,
    }


def _bars(row):
    if not isinstance(row, dict):
        return None
    raw = row.get("gabriel_barras")
    if not raw:
        return None
    bars = []
    for item in raw:
        parsed = _bar(item)
        if parsed is None:
            return None
        bars.append(parsed)
    return bars


def _ema(values, period):
    if not values:
        return ZERO
    alpha = Decimal("2") / Decimal(period + 1)
    result = values[0]
    for value in values[1:]:
        result = value * alpha + result * (Decimal("1") - alpha)
    return result


def _atr(bars, period=ATR_PERIOD):
    source = bars[-period:]
    if not source:
        return ZERO
    return sum((item["high"] - item["low"] for item in source), ZERO) / Decimal(len(source))


def _volume_zscore(current, prior):
    source = prior[-Z_PERIOD:]
    if current["volume"] is None or any(item["volume"] is None for item in source):
        return None
    volumes = [item["volume"] for item in source]
    mean = sum(volumes, ZERO) / Decimal(len(volumes))
    deviation = Decimal(str(pstdev([float(value) for value in volumes])))
    if deviation > ZERO:
        return (current["volume"] - mean) / deviation
    return ZERO


def _session_vwap(bars, current):
    """Replica a atualização da VWAP atual, sem carregar estado entre chamadas."""
    try:
        session_date = current["dt"].date()
    except AttributeError:
        return None

    numerator = ZERO
    denominator = ZERO
    for item in bars:
        try:
            same_session = item["dt"].date() == session_date
        except AttributeError:
            return None
        if not same_session:
            continue
        # A VWAP original recebe o volume de todos os candles da sessão.
        if item["volume"] is None:
            return None
        typical = (item["high"] + item["low"] + item["close"]) / Decimal("3")
        numerator += typical * item["volume"]
        denominator += item["volume"]

    if denominator > ZERO:
        return numerator / denominator
    return current["close"]


def _round_up_tick(points):
    if points <= ZERO:
        return TICK
    units = (points / TICK).to_integral_value(rounding=ROUND_CEILING)
    return units * TICK


def _risk_points(current, prior):
    stop_level = min(
        current["low"],
        *(item["low"] for item in prior[-3:]),
    ) - TICK
    return _round_up_tick(current["close"] - stop_level)


def _sinal_momentum(current, prior, vwap):
    zscore = _volume_zscore(current, prior)
    if zscore is None:
        return 0

    current_atr = _atr(prior, ATR_PERIOD)
    if current_atr <= ZERO:
        return 0

    body_ok = (
        current["close"] - current["open"]
        >= current_atr * MIN_BODY_ATR
    )
    breakout = current["close"] > max(item["high"] for item in prior[-BREAKOUT_LOOKBACK:])
    ema20 = _ema([item["close"] for item in prior[-EMA_SOURCE_BARS:]], 20)
    extension_ok = current["close"] - ema20 <= current_atr * MAX_EXTENSION_ATR

    if not (
        zscore >= MIN_VOLUME_Z
        and body_ok
        and breakout
        and current["close"] > vwap
        and extension_ok
    ):
        return 0

    # O _risk_intent da fonte recusa stops arredondados acima do máximo.
    return 1 if _risk_points(current, prior) <= MAX_STOP_POINTS else 0


def gerar_sinal(row) -> int:
    """Gera somente compra quando toda a porta causal da fonte é satisfeita."""
    bars = _bars(row)
    if bars is None or len(bars) < EMA_SOURCE_BARS + 1:
        return 0

    prior = bars[:-1]
    current = bars[-1]
    vwap = _session_vwap(bars, current)
    if vwap is None:
        return 0
    return _sinal_momentum(current, prior, vwap)


__all__ = ["gerar_sinal"]
