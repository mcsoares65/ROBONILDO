"""Candidata independente Gabriel — SMC quebra + reteste v3 (compra).

Autoria: Gabriel (fonte do ZIP) / adaptação Manus; revisão humana pendente.
Esta é uma candidata, não titular, e não foi executada na classificação oficial
nem contra histórico. Variações relevantes testadas antes desta versão: 0.
O ``v3`` é a versão própria da hipótese na fonte, não a versão V465 do projeto.

A regra foi portada sem importar módulos do projeto, I/O, rede, arquivo, estado
acumulado ou ``exec``/``eval``. O estado originalmente mantido pela classe Gen3
é reconstruído causalmente, do candle mais antigo disponível ao candle atual,
a partir de ``row['gabriel_barras']``. A janela de até 96 candles é suficiente
para os TTLs da hipótese; exige-se o aquecimento original de 60 candles
anteriores. A hipótese não usa volume/Quantidade: a assunção de quantidade por
candle, quando esse campo está ausente, é portanto não aplicável; nenhuma
Quantidade ausente é convertida em zero ou usada como substituto.

Origem: ``smc_structure_retest_v3.py`` do ZIP. Parâmetros e limiares foram
preservados, inclusive ATR simples de 20 ranges, sweep, BOS, FVG, reteste,
TTL, invalidação, risco máximo de 100 pontos, arredondamento em 5 pontos e RR
2,00. Fonte SHA256:
1a5a878cdb50750ff28165227c919536fedea51b2e33a824b3c2221b26706b52.
"""

from decimal import Decimal, InvalidOperation, ROUND_CEILING


STRATEGY_KEY = "smc_structure_retest_v3"
LIQUIDITY_LOOKBACK = 20
BOS_LOOKBACK = 12
SWEEP_TO_BOS_TTL = 12
RETEST_TTL = 8
ATR_PERIOD = 20
MIN_IMPULSE_ATR = Decimal("0.90")
MIN_FVG_ATR = Decimal("0.08")
RETEST_CLOSE_FRACTION = Decimal("0.50")
RISK_BUDGET_BRL = Decimal("20.00")
POINT_VALUE_BRL = Decimal("0.20")
REWARD_RISK = Decimal("2.00")
TICK = Decimal("5")
MAX_STOP_POINTS = RISK_BUDGET_BRL / POINT_VALUE_BRL
ZERO = Decimal("0")


def _decimal(value):
    """Converte um campo OHLC finito sem inventar valores ausentes."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"OHLC inválido: {value!r}") from error
    if not number.is_finite():
        raise ValueError(f"OHLC não finito: {value!r}")
    return number


def _bars(row):
    """Lê somente a janela pública Gabriel e normaliza os quatro preços."""
    if not isinstance(row, dict):
        return ()
    raw = row.get("gabriel_barras")
    if not raw:
        return ()
    try:
        if len(raw) < 61:
            return ()
        source = raw[-96:]
    except (TypeError, ValueError):
        return ()

    bars = []
    try:
        for candle in source:
            if not isinstance(candle, dict):
                return ()
            bars.append({
                "open": _decimal(candle["Abertura"]),
                "high": _decimal(candle["Maximo"]),
                "low": _decimal(candle["Minimo"]),
                "close": _decimal(candle["Fechamento"]),
            })
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return ()
    return tuple(bars)


def _atr(prior):
    """A mesma média de ranges usada por gen3.core.atr."""
    sample = prior[-ATR_PERIOD:]
    if not sample:
        return ZERO
    return sum((bar["high"] - bar["low"] for bar in sample), ZERO) / Decimal(len(sample))


def _round_up_tick(points):
    """Cópia local de round_up_tick, inclusive sua regra para points <= 0."""
    if points <= ZERO:
        return TICK
    units = (points / TICK).to_integral_value(rounding=ROUND_CEILING)
    return units * TICK


def _risk_levels(stop_points):
    """Retorna (stop em pontos, alvo em pontos), ou None se o gate reprovar."""
    stop = _round_up_tick(stop_points)
    if stop <= ZERO or stop > MAX_STOP_POINTS:
        return None
    target = _round_up_tick(stop * REWARD_RISK)
    return stop, target


def _replay(bars):
    """Reconstitui a máquina causal e devolve sinal e níveis do último candle."""
    sweep = None
    fvg = None
    last_signal = 0
    last_levels = None

    for index, bar in enumerate(bars):
        prior = bars[:index]
        last_signal = 0
        last_levels = None
        if len(prior) < 60:
            continue

        current_atr = _atr(prior)
        if current_atr <= ZERO:
            continue

        if sweep and sweep["age"] >= SWEEP_TO_BOS_TTL:
            sweep = None
        if fvg and fvg["age"] >= RETEST_TTL:
            fvg = None
        if sweep:
            sweep["age"] += 1
        if fvg:
            fvg["age"] += 1

        # 1. Sweep de liquidez.
        recent = prior[-LIQUIDITY_LOOKBACK:]
        prior_low = min(candidate["low"] for candidate in recent)
        if bar["low"] < prior_low and bar["close"] > prior_low:
            pre_bos_high = max(candidate["high"] for candidate in prior[-BOS_LOOKBACK:])
            sweep = {
                "low": bar["low"],
                "bos_level": pre_bos_high,
                "age": 0,
            }
            fvg = None
            continue

        # 2. BOS + impulso + FVG.
        if sweep and fvg is None:
            bos_level = sweep["bos_level"]
            impulse = bar["close"] - bar["open"]
            fvg_lower = prior[-2]["high"]
            fvg_upper = bar["low"]
            bullish_fvg = (
                fvg_upper > fvg_lower
                and (fvg_upper - fvg_lower) >= current_atr * MIN_FVG_ATR
            )
            strong_impulse = impulse >= current_atr * MIN_IMPULSE_ATR
            if bar["close"] > bos_level and strong_impulse and bullish_fvg:
                fvg = {
                    "lower": fvg_lower,
                    "upper": fvg_upper,
                    "mid": (fvg_lower + fvg_upper) / Decimal("2"),
                    "sweep_low": sweep["low"],
                    "bos_level": bos_level,
                    "age": 0,
                }
                continue

        # 3. Reteste + confirmação.
        if fvg:
            if bar["close"] < fvg["lower"] or bar["low"] <= fvg["sweep_low"]:
                fvg = None
                sweep = None
                continue

            touched = bar["low"] <= fvg["upper"] and bar["high"] >= fvg["lower"]
            close_threshold = fvg["lower"] + (
                (fvg["upper"] - fvg["lower"]) * RETEST_CLOSE_FRACTION
            )
            confirmed = (
                touched
                and bar["close"] >= close_threshold
                and bar["close"] > bar["open"]
            )
            if confirmed:
                stop_level = min(fvg["sweep_low"], fvg["lower"]) - Decimal("5")
                levels = _risk_levels(bar["close"] - stop_level)
                fvg = None
                sweep = None
                if levels is not None:
                    last_signal = 1
                    last_levels = levels

    return last_signal, last_levels


def gerar_sinal(row) -> int:
    """Retorna somente 1 (compra) ou 0; a hipótese original não vende."""
    bars = _bars(row)
    if not bars:
        return 0
    signal, _ = _replay(bars)
    return signal


__all__ = ["STRATEGY_KEY", "gerar_sinal"]
