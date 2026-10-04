"""Candidata independente Gabriel — trend pullback v3 (compra).

Autoria: Gabriel (fonte do ZIP) / adaptação Manus; revisão humana pendente.
Esta é uma candidata, não titular, e não foi executada na classificação oficial
nem contra histórico. Variações relevantes testadas antes desta versão: 0.
O ``v3`` é a versão própria da hipótese na fonte, não a versão V465 do projeto.

Origem: ``gen3/trend_pullback_v3.py`` do ZIP. A hipótese preserva a tendência
por EMA 20/50 e inclinação mínima de 0,12 ATR, VWAP diária incluindo o candle
atual, toque da EMA rápida, rejeição compradora por pavio inferior e razão de
volume 1,10 sobre os 20 candles anteriores. Fonte SHA256:
ad917a7d85515ff467eaf172be46d1ac92cf9b9e45b58bfa4b027662a47da1a3.

A assunção de quantidade por candle é que ``Quantidade`` em
``row['gabriel_barras']`` representa o volume por candle correspondente a
``Bar.volume`` na fonte; a unidade/paridade live-replay ainda requer revisão
humana. Como volume é indispensável para a hipótese, qualquer ``Quantidade``
ausente ou inválida necessária ao VWAP, à média dos 20 candles ou ao candle
atual faz a função devolver 0. Quantidade ausente nunca é convertida em zero.
A reconstrução é causal, sem estado global, usando somente os até 96 candles
entregues pelo motor; assume que essa janela contém o histórico da sessão atual
necessário à VWAP. Não há I/O, rede, arquivo, importação de módulos do projeto,
``exec`` ou ``eval``.
"""

from decimal import Decimal, InvalidOperation


EMA_FAST_PERIOD = 20
EMA_SLOW_PERIOD = 50
SLOPE_BARS = 5
ATR_PERIOD = 20
MIN_SLOPE_ATR = Decimal("0.12")
VOLUME_RATIO = Decimal("1.10")
MIN_LOWER_WICK_BODY = Decimal("0.80")
WARMUP_BARS = 60
MAX_BARS = 96
ZERO = Decimal("0")
ONE = Decimal("1")


def _decimal(value):
    """Converte preço finito; dado inválido não vira valor fabricado."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"Valor numérico inválido: {value!r}") from error
    if not number.is_finite():
        raise ValueError(f"Valor numérico não finito: {value!r}")
    return number


def _quantidade(value):
    """Retorna Decimal ou None; zero válido não é confundido com ausente."""
    if value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"Quantidade inválida: {value!r}") from error
    if not number.is_finite() or number < ZERO:
        raise ValueError(f"Quantidade inválida: {value!r}")
    return number


def _bars(row):
    """Lê apenas gabriel_barras e normaliza OHLC, data e Quantidade."""
    if not isinstance(row, dict):
        return ()
    raw = row.get("gabriel_barras")
    if not raw:
        return ()
    try:
        if len(raw) < WARMUP_BARS + 1:
            return ()
        source = raw[-MAX_BARS:]
    except (TypeError, ValueError):
        return ()

    bars = []
    try:
        for candle in source:
            if not isinstance(candle, dict):
                return ()
            timestamp = candle["dt"]
            session_date = timestamp.date()
            bars.append(
                {
                    "open": _decimal(candle["Abertura"]),
                    "high": _decimal(candle["Maximo"]),
                    "low": _decimal(candle["Minimo"]),
                    "close": _decimal(candle["Fechamento"]),
                    "quantity": _quantidade(candle.get("Quantidade")),
                    "session_date": session_date,
                }
            )
    except (AttributeError, KeyError, TypeError, ValueError, InvalidOperation):
        return ()
    return tuple(bars)


def _ema(values, period):
    if not values:
        return ZERO
    alpha = Decimal("2") / Decimal(period + 1)
    result = values[0]
    for value in values[1:]:
        result = value * alpha + result * (ONE - alpha)
    return result


def _atr(prior):
    sample = prior[-ATR_PERIOD:]
    if not sample:
        return ZERO
    return sum((bar["high"] - bar["low"] for bar in sample), ZERO) / Decimal(len(sample))


def _session_vwap(prior, current):
    """Replica a atualização da VWAP antes do sinal do candle atual."""
    session_date = current["session_date"]
    session = [bar for bar in prior + (current,) if bar["session_date"] == session_date]
    if any(bar["quantity"] is None for bar in session):
        return None
    pv = ZERO
    volume = ZERO
    for bar in session:
        typical = (bar["high"] + bar["low"] + bar["close"]) / Decimal("3")
        pv += typical * bar["quantity"]
        volume += bar["quantity"]
    if volume > ZERO:
        return pv / volume
    return current["close"]


def _volume_ok(prior, current):
    """A condição original; ausência necessária reprova o sinal."""
    recent = prior[-ATR_PERIOD:]
    if current["quantity"] is None or any(bar["quantity"] is None for bar in recent):
        return False
    average = sum((bar["quantity"] for bar in recent), ZERO) / Decimal(len(recent))
    return average > ZERO and current["quantity"] >= average * VOLUME_RATIO


def gerar_sinal(row) -> int:
    """Retorna 1 para compra; a hipótese original não possui venda."""
    bars = _bars(row)
    if not bars:
        return 0

    current = bars[-1]
    prior = bars[:-1]
    if len(prior) < WARMUP_BARS:
        return 0

    vwap = _session_vwap(prior, current)
    if vwap is None:
        return 0

    closes = [bar["close"] for bar in prior[-80:]]
    ema_fast = _ema(closes, EMA_FAST_PERIOD)
    ema_slow = _ema(closes, EMA_SLOW_PERIOD)
    ema_fast_old = _ema(closes[:-SLOPE_BARS], EMA_FAST_PERIOD)
    current_atr = _atr(prior)
    if current_atr <= ZERO:
        return 0

    slope_ok = (
        ema_fast > ema_slow
        and ema_fast - ema_fast_old >= current_atr * MIN_SLOPE_ATR
    )
    if not slope_ok or current["close"] <= vwap:
        return 0

    body = abs(current["close"] - current["open"])
    lower_wick = min(current["open"], current["close"]) - current["low"]
    rejection = (
        current["close"] > current["open"]
        and lower_wick >= max(ONE, body * MIN_LOWER_WICK_BODY)
    )
    pullback_touch = current["low"] <= ema_fast and current["close"] >= ema_fast
    return 1 if pullback_touch and rejection and _volume_ok(prior, current) else 0


__all__ = ["gerar_sinal"]
