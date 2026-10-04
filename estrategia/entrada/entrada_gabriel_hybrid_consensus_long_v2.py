"""Candidata independente Gabriel: Híbrida consenso v2 — Compra.

Autoria: Gabriel (fonte do ZIP), adaptação Manus; revisão humana pendente.
Variações relevantes testadas: 0.
Assunção declarada: ``row["gabriel_barras"]`` fornece ``Quantidade`` por
candle na mesma unidade de volume usada pela fonte; ``None`` significa dado
indisponível e, sem esse volume necessário, a função devolve 0. A candidata é
stateless: a supressão causal de sinais consecutivos é reconstruída somente
com os dois últimos candles confirmáveis presentes na linha.

A implementação não importa módulos do projeto, não faz I/O e não envia ordens.
A proteção stop/alvo da fonte não é portada neste par: ela é semanticamente a
mesma proteção já existente em ``saida_daytrader_rr2_v1`` (amplitude média dos
20 candles anteriores, piso de 20 pontos e alvo 2R), portanto uma saída nova
seria duplicação.
"""

from decimal import Decimal, InvalidOperation


_ZERO = Decimal("0")
_ONE = Decimal("1")
_VOLUME_RATIO = Decimal("1.10")
_MOMENTUM_MULTIPLE = Decimal("1.00")
_MIN_VOTES = 5
_WINDOW = 20


def _decimal(value):
    """Converte um valor numérico finito sem fabricar dados ausentes."""
    if value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not number.is_finite():
        return None
    return number


def _bar(raw):
    """Normaliza somente os campos OHLC e Quantidade públicos do contrato."""
    if not isinstance(raw, dict):
        return None
    values = {
        "open": _decimal(raw.get("Abertura")),
        "high": _decimal(raw.get("Maximo")),
        "low": _decimal(raw.get("Minimo")),
        "close": _decimal(raw.get("Fechamento")),
        "volume": _decimal(raw.get("Quantidade")),
    }
    if any(value is None for value in values.values()):
        return None
    if values["volume"] < _ZERO:
        return None
    return values


def _sinal_bruto(atual, anteriores):
    """Replica ``_signal`` da fonte para um candle e seus 20 anteriores."""
    if len(anteriores) < _WINDOW:
        return 0

    recentes20 = anteriores[-_WINDOW:]
    recentes5 = anteriores[-5:]
    sma20 = sum((bar["close"] for bar in recentes20), _ZERO) / Decimal(_WINDOW)
    sma5 = sum((bar["close"] for bar in recentes5), _ZERO) / Decimal(5)
    amplitude_media = (
        sum((bar["high"] - bar["low"] for bar in recentes20), _ZERO)
        / Decimal(_WINDOW)
    )
    volume_medio = (
        sum((bar["volume"] for bar in recentes20), _ZERO)
        / Decimal(_WINDOW)
    )

    # A fonte usa rel_vol=1 somente quando a média de volume é zero. Isso não
    # substitui Quantidade ausente: a ausência já foi rejeitada em _bar.
    rel_vol = atual["volume"] / volume_medio if volume_medio > _ZERO else _ONE
    tendencia = sma5 - sma20
    amplitude_atual = atual["high"] - atual["low"]

    is_trend = abs(tendencia) >= amplitude_media * Decimal("0.20")
    is_expansion = (
        amplitude_atual >= amplitude_media * Decimal("1.15")
        or rel_vol >= _VOLUME_RATIO
    )
    if not (is_trend and is_expansion):
        return 0

    short_momentum = atual["close"] - recentes5[0]["close"]
    long_momentum = atual["close"] - recentes20[0]["close"]
    votes_up = sum(
        (
            tendencia > _ZERO,
            sma5 > sma20,
            short_momentum > _ZERO,
            long_momentum >= amplitude_media * _MOMENTUM_MULTIPLE,
            rel_vol >= _VOLUME_RATIO,
            amplitude_atual >= amplitude_media * Decimal("1.05"),
        )
    )
    if votes_up >= _MIN_VOTES and atual["close"] > atual["open"]:
        return 1
    return 0


def gerar_sinal(row) -> int:
    """Retorna 1 para compra ou 0; esta hipótese não produz venda."""
    if not isinstance(row, dict):
        return 0
    historico = row.get("gabriel_barras") or ()
    # 20 candles anteriores para cada avaliação + candle anterior para
    # reconstruir causalmente a supressão de direção consecutiva da fonte.
    if len(historico) < _WINDOW + 2:
        return 0

    barras = [_bar(raw) for raw in historico[-(_WINDOW + 2):]]
    if any(bar is None for bar in barras):
        return 0

    anterior = _sinal_bruto(barras[-2], barras[-22:-2])
    atual = _sinal_bruto(barras[-1], barras[-21:-1])
    if atual == 0:
        return 0
    return 0 if anterior == atual else atual
