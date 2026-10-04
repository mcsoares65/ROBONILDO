"""Candidata Gabriel ``compression_breakout_v3`` para entrada compradora.

Autoria: Gabriel (fonte do ZIP) / adaptação Manus. Variações testadas: 0.
Revisão humana: pendente. A adaptação é candidata, não titular, e não foi
executada na classificação oficial nem em histórico.

A fonte original usa ``Quantidade`` como volume de cada candle. Assunção
explícita: ``row["gabriel_barras"]`` preserva essa unidade como quantidade por
candle; ``None`` significa dado ausente, nunca volume zero. Sem quantidade no
candle atual ou nos 20 candles de referência, esta função fecha a oportunidade
com 0. A janela recebida é causal: o último candle é o atual e os anteriores
são o histórico já fechado.

A fonte foi adaptada sem imports do projeto, I/O, rede, estado acumulado,
``exec`` ou ``eval``. SHA-256 da fonte original:

bdfda453cf27d015d48a85f2b7584deee034d0f6201ffbaf549908b0f28d394a

Regra portada: cinco candles consecutivos de compressão Bollinger dentro de
Keltner, rompimento comprador acima das máximas dos 20 candles anteriores,
fechamento positivo, expansão de range por ATR médio simples e volume relativo
mínimo de 1,80. O gate de risco da fonte (stop arredondado ao tick de 5, até
100 pontos) também é aplicado antes de emitir o sinal.
"""

from decimal import Decimal, InvalidOperation, ROUND_CEILING
from statistics import pstdev


PERIODO = 20
SQUEEZE_BARS = 5
BB_STD = Decimal("2.00")
KC_ATR = Decimal("1.50")
VOLUME_RATIO = Decimal("1.80")
TICK = Decimal("5")
MAX_STOP_POINTS = Decimal("20.00") / Decimal("0.20")
REWARD_RISK = Decimal("2.00")
MIN_PRIOR_BARS = 60


def _decimal(value):
    """Converte um campo primitivo sem aceitar valores não finitos."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None


def _bar(value):
    """Extrai OHLC e quantidade sem inventar volume ausente."""
    if not isinstance(value, dict):
        return None
    abertura = _decimal(value.get("Abertura"))
    maxima = _decimal(value.get("Maximo"))
    minima = _decimal(value.get("Minimo"))
    fechamento = _decimal(value.get("Fechamento"))
    if None in (abertura, maxima, minima, fechamento):
        return None

    quantidade_raw = value.get("Quantidade")
    quantidade = (
        None if quantidade_raw is None else _decimal(quantidade_raw)
    )
    if quantidade_raw is not None and quantidade is None:
        return None
    return {
        "open": abertura,
        "high": maxima,
        "low": minima,
        "close": fechamento,
        "volume": quantidade,
    }


def _barras(row):
    if not isinstance(row, dict):
        return None
    raw = row.get("gabriel_barras") or ()
    if len(raw) < MIN_PRIOR_BARS + 1:
        return None
    barras = [_bar(item) for item in raw]
    if any(item is None for item in barras):
        return None
    return barras


def _ema(values):
    """EMA local idêntica à rotina ``gen3.core.ema`` para período 20."""
    if not values:
        return Decimal("0")
    alpha = Decimal("2") / Decimal(PERIODO + 1)
    result = values[0]
    for value in values[1:]:
        result = value * alpha + result * (Decimal("1") - alpha)
    return result


def _desvio_padrao(values):
    """Pstdev convertido pela mesma rota float->texto da fonte gen3."""
    if len(values) < 2:
        return Decimal("0")
    return Decimal(str(pstdev([float(value) for value in values])))


def _atr(barras):
    recentes = barras[-PERIODO:]
    return sum(
        (item["high"] - item["low"] for item in recentes),
        Decimal("0"),
    ) / Decimal(PERIODO)


def _squeeze_at(barras):
    if len(barras) < PERIODO + 1:
        return False
    recentes = barras[-PERIODO:]
    fechamentos = [item["close"] for item in recentes]
    meio_bb = sum(fechamentos, Decimal("0")) / Decimal(PERIODO)
    desvio = _desvio_padrao(fechamentos)
    meio_kc = _ema(fechamentos)
    amplitude_atr = _atr(recentes)
    bb_superior = meio_bb + desvio * BB_STD
    bb_inferior = meio_bb - desvio * BB_STD
    kc_superior = meio_kc + amplitude_atr * KC_ATR
    kc_inferior = meio_kc - amplitude_atr * KC_ATR
    return bb_superior < kc_superior and bb_inferior > kc_inferior


def _arredondar_para_cima_tick(points):
    if points <= Decimal("0"):
        return TICK
    units = (points / TICK).to_integral_value(rounding=ROUND_CEILING)
    return units * TICK


def _stop_points(barra, anteriores):
    """Stop bruto da fonte: mínimo do candle e dos três anteriores, menos 5."""
    stop_level = min(
        barra["low"],
        *(item["low"] for item in anteriores[-3:]),
    ) - Decimal("5")
    return barra["close"] - stop_level


def gerar_sinal(row) -> int:
    """Retorna 1 somente quando a hipótese original confirma a compra."""
    barras = _barras(row)
    if barras is None:
        return 0

    barra = barras[-1]
    anteriores = barras[:-1]
    if not all(
        _squeeze_at(anteriores[: len(anteriores) - deslocamento])
        for deslocamento in range(SQUEEZE_BARS)
    ):
        return 0

    comprimidas = anteriores[-PERIODO:]
    volumes = [item["volume"] for item in comprimidas]
    volume_atual = barra["volume"]
    # None é ausência; não é convertido silenciosamente em zero.
    if volume_atual is None or any(volume is None for volume in volumes):
        return 0
    volume_medio = sum(volumes, Decimal("0")) / Decimal(PERIODO)
    volume_ok = (
        volume_medio > Decimal("0")
        and volume_atual >= volume_medio * VOLUME_RATIO
    )

    range_expansion = (
        barra["high"] - barra["low"]
    ) >= _atr(anteriores)
    breakout = (
        barra["close"] > max(item["high"] for item in comprimidas)
        and barra["close"] > barra["open"]
    )
    if not (volume_ok and range_expansion and breakout):
        return 0

    stop = _arredondar_para_cima_tick(_stop_points(barra, anteriores))
    if stop <= Decimal("0") or stop > MAX_STOP_POINTS:
        return 0
    return 1


__all__ = ["gerar_sinal"]
