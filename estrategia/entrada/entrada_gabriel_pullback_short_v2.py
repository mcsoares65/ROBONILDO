"""Candidata independente: Pullback confirmado v2 — venda.

Autoria: Gabriel, do ZIP/fonte original ``pullback_short_v2.py``; adaptação
Manus para o contrato V465. A numeração ``v2`` identifica a hipótese de
origem/adaptação, não a VERSAO do projeto. Variações testadas: 0. Revisão
humana: pendente. Esta candidata não foi validada por classificação oficial
nem por histórico.

A fonte original mantém uma fila e recebe ``Bar.volume``. A adaptação
reconstrói causalmente a decisão usando apenas ``row["gabriel_barras"]``:
20 candles anteriores para a regra atual e mais um candle anterior para
reproduzir a supressão de direção consecutiva, sem estado global. Assume-se
que ``Quantidade`` representa a quantidade por candle correspondente ao
volume usado pela fonte; a unidade e a paridade live/replay ainda não foram
confirmadas. ``Quantidade`` ausente (``None``), inválida ou negativa em
qualquer candle indispensável faz a função retornar 0; ausência nunca é
substituída por zero.

A regra de stop/alvo da fonte é a mesma proteção já existente em
``saida_daytrader_rr2_v1`` (stop de 1,25 vezes a amplitude média de 20 candles,
piso de 20 pontos e alvo de 2R), portanto não há cartucho de saída Gabriel
duplicado nesta adaptação.

Contrato: ``gerar_sinal(row) -> -1 | 0 | 1``. Não importa módulos do projeto,
não faz I/O, rede, arquivo, ``exec``/``eval`` e não mantém memória entre
chamadas.
"""

from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")
JANELA = 20
SLOPE_MULTIPLE = Decimal("0.35")
MIN_VOLUME_RATIO = Decimal("1.00")
REGIME_MULTIPLE = Decimal("0.20")


def _decimal(valor):
    """Converte somente números finitos; dado ausente permanece indisponível."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return numero if numero.is_finite() else None


def _barra(candle):
    """Extrai OHLC e Quantidade sem transformar ausência em volume zero."""
    if not isinstance(candle, dict):
        return None
    abertura = _decimal(candle.get("Abertura"))
    maxima = _decimal(candle.get("Maximo"))
    minima = _decimal(candle.get("Minimo"))
    fechamento = _decimal(candle.get("Fechamento"))
    quantidade = _decimal(candle.get("Quantidade"))
    if None in (abertura, maxima, minima, fechamento, quantidade):
        return None
    if maxima < minima or quantidade < ZERO:
        return None
    return {
        "open": abertura,
        "high": maxima,
        "low": minima,
        "close": fechamento,
        "quantity": quantidade,
    }


def _sinal_bruto(barras) -> int:
    """Avalia um candle atual sem aplicar a memória de direção da fonte."""
    if len(barras) < JANELA + 1:
        return 0

    atuais = barras[-(JANELA + 1):]
    if any(barra is None for barra in atuais):
        return 0

    atual = atuais[-1]
    anteriores = atuais[:-1]
    recentes20 = anteriores[-JANELA:]
    recentes5 = anteriores[-5:]

    fechamentos20 = [barra["close"] for barra in recentes20]
    sma20 = sum(fechamentos20, ZERO) / Decimal(JANELA)
    sma5 = sum((barra["close"] for barra in recentes5), ZERO) / Decimal(5)
    amplitudes = [barra["high"] - barra["low"] for barra in recentes20]
    amplitude_media20 = sum(amplitudes, ZERO) / Decimal(JANELA)
    volumes = [barra["quantity"] for barra in recentes20]
    volume_medio20 = sum(volumes, ZERO) / Decimal(JANELA)
    relacao_volume = (
        atual["quantity"] / volume_medio20
        if volume_medio20 > ZERO
        else Decimal("1")
    )

    tendencia = sma5 - sma20
    em_tendencia = abs(tendencia) >= amplitude_media20 * REGIME_MULTIPLE
    if not em_tendencia:
        return 0

    anterior = anteriores[-1]
    if (
        tendencia < -amplitude_media20 * SLOPE_MULTIPLE
        and atual["high"] >= sma5
        and atual["close"] < sma5
        and atual["close"] < anterior["close"]
        and relacao_volume >= MIN_VOLUME_RATIO
        and (atual["open"] - atual["close"]) > ZERO
    ):
        return -1
    return 0


def gerar_sinal(row) -> int:
    """Retorna -1 para venda confirmada ou 0 quando a hipótese não dispara."""
    if not isinstance(row, dict):
        return 0

    historico = row.get("gabriel_barras") or ()
    # 20 candles anteriores para a regra atual + o candle anterior e seus
    # 20 precedentes para reconstituir _last_direction sem manter estado.
    if len(historico) < JANELA + 2:
        return 0

    barras = [_barra(candle) for candle in historico[-(JANELA + 2):]]
    if any(barra is None for barra in barras):
        return 0

    sinal_atual = _sinal_bruto(barras[-(JANELA + 1):])
    if sinal_atual == 0:
        return 0

    # Na fonte, um sinal igual ao último sinal emitido é suprimido; como a
    # única direção possível é venda e qualquer candle sem sinal zera a
    # memória, o candle anterior basta para reconstruir essa causalidade.
    sinal_anterior = _sinal_bruto(barras[:-1])
    return 0 if sinal_anterior == sinal_atual else sinal_atual


__all__ = ["gerar_sinal"]
