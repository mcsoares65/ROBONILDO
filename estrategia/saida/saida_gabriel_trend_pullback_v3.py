"""Saída candidata independente Gabriel — trend pullback v3.

Autoria: Gabriel (fonte do ZIP) / adaptação Manus; revisão humana pendente.
Esta é uma candidata, não titular, e não foi executada na classificação oficial
nem contra histórico. Variações relevantes testadas antes desta versão: 0.
O ``v3`` é a versão própria da hipótese na fonte, não a versão V465 do projeto.

Origem: ``gen3/trend_pullback_v3.py`` do ZIP. Fonte SHA256:
ad917a7d85515ff467eaf172be46d1ac92cf9b9e45b58bfa4b027662a47da1a3.
A proteção é tecnicamente distinta de ``saida_daytrader_rr2_v1``: a fonte usa
``structural_low = min(últimos 5 candles anteriores + candle atual) - 5``,
stop em pontos igual ao fechamento menos esse nível, arredondamento para cima
em passos de 5, gate máximo de 100 pontos e alvo de 2R arredondado. Na abertura,
esses pontos são convertidos em preços absolutos relativos a
``posicao['entrada']``; a hipótese original é somente de compra. VENDA,
exigida pelo cruzamento S001 da V465, usa espelho estrutural de cinco
candles e gate de 100 pontos: adaptação Manus, não regra original Gabriel.

A assunção de quantidade por candle é a mesma da entrada pareada: ``Quantidade``
representa o volume por candle correspondente a ``Bar.volume``. A saída não
fabrica nem converte Quantidade ausente em zero; o filtro de volume pertence à
entrada, e o risco abaixo usa somente OHLC. Não duplica
``saida_daytrader_rr2_v1`` (que usa amplitude média de 20 candles, piso de 20 e
multiplicador 1,25). Não há I/O, rede, arquivo, importação de módulos do
projeto, estado global, ``exec`` ou ``eval``.
"""

from decimal import Decimal, InvalidOperation, ROUND_CEILING
from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_gabriel_trend_pullback_v3"
WARMUP_BARS = 60
MAX_BARS = 96
STRUCTURE_LOOKBACK = 5
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
        raise ValueError(f"Valor OHLC inválido: {value!r}") from error
    if not number.is_finite():
        raise ValueError(f"Valor OHLC não finito: {value!r}")
    return number


def _bars(row):
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
            bars.append(
                {
                    "open": _decimal(candle["Abertura"]),
                    "high": _decimal(candle["Maximo"]),
                    "low": _decimal(candle["Minimo"]),
                    "close": _decimal(candle["Fechamento"]),
                }
            )
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return ()
    return tuple(bars)


def _round_up_tick(points):
    if points <= ZERO:
        return TICK
    units = (points / TICK).to_integral_value(rounding=ROUND_CEILING)
    return units * TICK


def _protection_points(row, lado):
    bars = _bars(row)
    if not bars:
        raise ValueError("Histórico Gabriel insuficiente para a proteção inicial.")
    current = bars[-1]
    prior = bars[:-1]
    if len(prior) < WARMUP_BARS:
        raise ValueError("São necessários 60 candles anteriores para a proteção inicial.")

    janela = prior[-STRUCTURE_LOOKBACK:] + (current,)
    if lado == "COMPRA":
        nivel = min(bar["low"] for bar in janela) - TICK
        distancia = current["close"] - nivel
    else:
        nivel = max(bar["high"] for bar in janela) + TICK
        distancia = nivel - current["close"]
    if distancia <= ZERO:
        raise ValueError("Stop estrutural inválido.")
    # A compra pareada já passou no gate da entrada; cap atende S001 quando
    # este cartucho é cruzado com entrada distinta.
    stop_points = min(_round_up_tick(distancia), MAX_STOP_POINTS)
    target_points = _round_up_tick(stop_points * REWARD_RISK)
    return stop_points, target_points


def avaliar_saida(row: dict, posicao: dict) -> dict:
    """Define stop/alvo absolutos na abertura e não reconfigura depois."""
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    try:
        candles = int(posicao.get("candles_decorridos", 0))
    except (TypeError, ValueError) as error:
        raise ValueError("candles_decorridos inválido.") from error
    if candles != 0:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    lado = str(posicao.get("lado", "")).upper()
    if lado not in ("COMPRA", "VENDA"):
        raise ValueError("Lado inválido.")
    try:
        entrada = float(posicao["entrada"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Entrada inválida.") from error
    if not isfinite(entrada):
        raise ValueError("Entrada não finita.")

    stop_points, target_points = _protection_points(row, lado)
    sentido = 1 if lado == "COMPRA" else -1
    stop = entrada - sentido * float(stop_points)
    target = entrada + sentido * float(target_points)
    if not isfinite(stop) or not isfinite(target):
        raise ValueError("Proteção inicial não finita.")
    return {"fechar": False, "novo_stop": stop, "novo_alvo": target}


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida"]
