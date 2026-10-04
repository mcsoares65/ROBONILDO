"""Candidata independente: Inside bar + expansão — compra.

Autoria: Gabriel, do ZIP original; adaptação Manus para o contrato V465.
Variações testadas: 0. Revisão humana: pendente.

A fonte original mantém estado numa fila e recebe ``Bar.volume``. Aqui a
causalidade é reconstruída somente a partir de ``row["gabriel_barras"]``:
os últimos 22 candles bastam para a decisão atual e para saber se o candle
anterior teria deixado a direção ativa. ``Quantidade`` é assumida como a
medida por candle correspondente ao volume da fonte; a unidade/paridade live
não foi confirmada. Quantidade ausente ou inválida não é convertida em zero:
como o volume é indispensável à hipótese, a função retorna 0.

Esta é uma candidata, não titular, e não declara validação ou rentabilidade.
"""

from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")
JANELA = 20
MULTIPLICADOR_EXPANSAO = Decimal("1.15")
RAZAO_VOLUME = Decimal("1.00")
RAZAO_VOLUME_EXPANSAO = Decimal("1.10")


def _decimal(valor):
    """Converte número finito sem inventar valor para dado ausente."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return numero if numero.is_finite() else None


def _barra(candle):
    """Extrai OHLC e Quantidade; ``None`` significa dado indisponível."""
    if not isinstance(candle, dict):
        return None
    abertura = _decimal(candle.get("Abertura"))
    maxima = _decimal(candle.get("Maximo"))
    minima = _decimal(candle.get("Minimo"))
    fechamento = _decimal(candle.get("Fechamento"))
    quantidade = _decimal(candle.get("Quantidade"))
    if None in (abertura, maxima, minima, fechamento, quantidade):
        return None
    if quantidade < ZERO:
        return None
    return {
        "open": abertura,
        "high": maxima,
        "low": minima,
        "close": fechamento,
        "quantity": quantidade,
    }


def _sinal_bruto(barras):
    """Avalia uma barra atual sem aplicar a supressão de direção repetida."""
    if len(barras) < JANELA + 1:
        return 0

    atual = barras[-1]
    anteriores = barras[-(JANELA + 1):-1]
    if any(_barra(candle) is None for candle in barras[-(JANELA + 1):]):
        return 0
    atual = _barra(atual)
    anteriores = [_barra(candle) for candle in anteriores]

    amplitudes = [candle["high"] - candle["low"] for candle in anteriores]
    media_amplitude = sum(amplitudes, ZERO) / Decimal(JANELA)
    volumes = [candle["quantity"] for candle in anteriores]
    media_volume = sum(volumes, ZERO) / Decimal(JANELA)
    relacao_volume = (
        atual["quantity"] / media_volume if media_volume > ZERO else Decimal("1")
    )
    amplitude_atual = atual["high"] - atual["low"]
    expansao = (
        amplitude_atual >= media_amplitude * MULTIPLICADOR_EXPANSAO
        or relacao_volume >= RAZAO_VOLUME_EXPANSAO
    )
    if not expansao:
        return 0

    mae = anteriores[-1]
    anterior_mae = anteriores[-2]
    inside = (
        mae["high"] <= anterior_mae["high"]
        and mae["low"] >= anterior_mae["low"]
    )
    if (
        inside
        and atual["close"] > mae["high"]
        and relacao_volume >= RAZAO_VOLUME
    ):
        return 1
    return 0


def gerar_sinal(row) -> int:
    """Retorna 1 para compra e 0 caso contrário, sem memória entre chamadas."""
    if not isinstance(row, dict):
        return 0
    historico = row.get("gabriel_barras") or ()
    if len(historico) < JANELA + 2:
        return 0

    # O candle atual e seus 20 anteriores são a janela mínima da fonte. A
    # barra anterior é também reconstituída quando há 22 candles para
    # reproduzir _last_direction sem manter estado global.
    barras = list(historico[-(JANELA + 2):])
    # Quando a barra anterior também é reconstituída, sua janela de volume
    # faz parte da decisão causal; sem ela não é seguro inferir se a direção
    # já estava ativa. Em ambos os casos, nenhum dado ausente vira zero.
    if any(_barra(candle) is None for candle in barras):
        return 0
    sinal_atual = _sinal_bruto(barras[-(JANELA + 1):])
    if sinal_atual == 0:
        return 0

    sinal_anterior = _sinal_bruto(barras[:-1])
    return 0 if sinal_anterior == sinal_atual else sinal_atual


__all__ = ["gerar_sinal"]
