"""Saída candidata independente Gabriel — SMC quebra + reteste v3.

Autoria: Gabriel (fonte do ZIP) / adaptação Manus; revisão humana pendente.
Esta é uma candidata, não titular, e não foi executada na classificação oficial
nem contra histórico. Variações relevantes testadas antes desta versão: 0.
O ``v3`` é a versão própria da hipótese na fonte, não a versão V465 do projeto.

A regra de proteção é tecnicamente distinta de ``saida_daytrader_rr2_v1``:
o stop desta hipótese é ``min(sweep_low, fvg_lower) - 5`` pontos e o alvo é
2R, com o mesmo arredondamento para cima em passos de 5 e gate de no máximo
100 pontos da fonte. A saída reconstrói causalmente o sweep/BOS/FVG/reteste do
candle atual a partir de ``row['gabriel_barras']``; não mantém estado e não
importa módulos do projeto. Na abertura, converte os pontos da fonte em preços
absolutos relativos a ``posicao['entrada']``. A hipótese não usa volume/
Quantidade: a assunção de quantidade por candle é não aplicável; Quantidade
ausente nunca é substituída por zero.

O S001 da V465 cruza esta saída com entradas que não fazem sweep/FVG e exige
proteção também para VENDA. Somente nesses cruzamentos há fallback Manus:
extremo dos seis candles recentes +/- 5 pontos, teto de 100 pontos e alvo 2R.
Não é parte da fonte Gabriel e não foi validado em ranking/mercado.

Origem: ``smc_structure_retest_v3.py`` do ZIP. Fonte SHA256:
1a5a878cdb50750ff28165227c919536fedea51b2e33a824b3c2221b26706b52.
"""

from decimal import Decimal, InvalidOperation, ROUND_CEILING
from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_gabriel_smc_structure_retest_v3"
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
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"OHLC inválido: {value!r}") from error
    if not number.is_finite():
        raise ValueError(f"OHLC não finito: {value!r}")
    return number


def _bars(row):
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
    sample = prior[-ATR_PERIOD:]
    if not sample:
        return ZERO
    return sum((bar["high"] - bar["low"] for bar in sample), ZERO) / Decimal(len(sample))


def _round_up_tick(points):
    if points <= ZERO:
        return TICK
    units = (points / TICK).to_integral_value(rounding=ROUND_CEILING)
    return units * TICK


def _replay_levels(bars):
    """Retorna os níveis em pontos somente se o último candle confirmou entrada."""
    sweep = None
    fvg = None
    levels = None

    for index, bar in enumerate(bars):
        prior = bars[:index]
        levels = None
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

        recent = prior[-LIQUIDITY_LOOKBACK:]
        prior_low = min(candidate["low"] for candidate in recent)
        if bar["low"] < prior_low and bar["close"] > prior_low:
            pre_bos_high = max(candidate["high"] for candidate in prior[-BOS_LOOKBACK:])
            sweep = {"low": bar["low"], "bos_level": pre_bos_high, "age": 0}
            fvg = None
            continue

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
                    "sweep_low": sweep["low"],
                    "age": 0,
                }
                continue

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
                stop_points = _round_up_tick(bar["close"] - stop_level)
                if stop_points <= ZERO or stop_points > MAX_STOP_POINTS:
                    levels = None
                else:
                    levels = (stop_points, _round_up_tick(stop_points * REWARD_RISK))
                fvg = None
                sweep = None

    return levels


def _protecao_inicial(row, posicao):
    lado = str(posicao.get("lado", "")).upper()
    if lado not in ("COMPRA", "VENDA"):
        raise ValueError("Lado inválido.")
    try:
        entrada = float(posicao["entrada"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Entrada inválida.") from error
    if not isfinite(entrada):
        raise ValueError("Entrada não finita.")

    barras = _bars(row)
    levels = _replay_levels(barras) if lado == "COMPRA" else None
    if levels is None:
        if len(barras) < 6:
            raise ValueError("Contexto insuficiente para proteção S001.")
        recente = barras[-6:]
        ultimo = recente[-1]
        if lado == "COMPRA":
            distancia = ultimo["close"] - min(b["low"] for b in recente) + TICK
        else:
            distancia = max(b["high"] for b in recente) - ultimo["close"] + TICK
        stop = min(MAX_STOP_POINTS, _round_up_tick(max(distancia, TICK)))
        levels = (stop, _round_up_tick(stop * REWARD_RISK))
    stop_points, target_points = levels
    sentido = 1 if lado == "COMPRA" else -1
    stop = entrada - sentido * float(stop_points)
    target = entrada + sentido * float(target_points)
    if not isfinite(stop) or not isfinite(target):
        raise ValueError("Proteção inicial não finita.")
    return stop, target


def avaliar_saida(row: dict, posicao: dict) -> dict:
    """Define proteção absoluta na abertura e não reconfigura depois."""
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    try:
        candles = int(posicao.get("candles_decorridos", 0))
    except (TypeError, ValueError) as error:
        raise ValueError("candles_decorridos inválido.") from error
    if candles == 0:
        stop, target = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": target}
    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida"]
