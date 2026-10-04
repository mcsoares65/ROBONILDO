"""Candidata independente de entrada: Gabriel ``dual_momentum_long``.

Autoria: Gabriel do ZIP original; adaptação Manus. Revisão humana pendente.
Variações testadas: 0. Esta é uma adaptação direta dos parâmetros padrão da
fonte, não uma alegação de validação ou rentabilidade.

A fonte original usa uma fila stateful; aqui a memória é reconstruída
causalmente a partir de ``row["gabriel_barras"]`` (até 96 candles), sem estado
global. A janela precisa conter os 20 candles anteriores e o candle atual.
Para reproduzir a supressão de sinais idênticos consecutivos, o candle anterior
é recalculado quando disponível. A assunção de integração é que
``Quantidade`` representa quantidade por candle na unidade esperada pela fonte.
Como essa unidade não foi confirmada, qualquer Quantidade ausente nos candles
necessários faz a função retornar 0; ausência nunca é convertida em zero.

A fonte também calcula stop de 1,25 vezes a amplitude média de 20 candles,
com piso de 20 pontos, e alvo 2R (com mínimo stop + 5). Essa regra é
tecnicamente idêntica a ``saida_daytrader_rr2_v1`` já existente; por isso esta
candidata não cria uma saída duplicada.
"""

from decimal import Decimal, InvalidOperation


_ZERO = Decimal("0")
_JANELA = 20
_VOLUME_RATIO = Decimal("1.05")
_MOMENTUM_MULTIPLE = Decimal("0.75")


def _numero(valor):
    """Converte um campo numérico sem aceitar NaN ou infinito."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not numero.is_finite():
        return None
    return numero


def _candle(bruto):
    """Normaliza apenas OHLC e Quantidade; dado inválido torna-se indisponível."""
    if not isinstance(bruto, dict):
        return None
    abertura = _numero(bruto.get("Abertura"))
    maxima = _numero(bruto.get("Maximo"))
    minima = _numero(bruto.get("Minimo"))
    fechamento = _numero(bruto.get("Fechamento"))
    quantidade = _numero(bruto.get("Quantidade"))
    if None in (abertura, maxima, minima, fechamento, quantidade):
        return None
    return {
        "open": abertura,
        "high": maxima,
        "low": minima,
        "close": fechamento,
        "volume": quantidade,
    }


def _normalizar_barras(row):
    if not isinstance(row, dict):
        return []
    brutas = row.get("gabriel_barras") or ()
    if not isinstance(brutas, (list, tuple)):
        return []
    normalizadas = []
    for bruto in brutas:
        candle = _candle(bruto)
        if candle is None:
            # Não há substituição silenciosa de Quantidade ausente por zero.
            return []
        normalizadas.append(candle)
    return normalizadas


def _sinal_bruto(atual, anteriores):
    """Calcula o sinal de um candle contra exatamente os 20 candles anteriores."""
    if len(anteriores) < _JANELA:
        return 0

    recentes20 = anteriores[-_JANELA:]
    recentes5 = anteriores[-5:]
    amplitudes = [candle["high"] - candle["low"] for candle in recentes20]
    media_amplitude = sum(amplitudes, _ZERO) / Decimal(_JANELA)

    volumes = [candle["volume"] for candle in recentes20]
    media_volume = sum(volumes, _ZERO) / Decimal(_JANELA)
    rel_volume = (
        atual["volume"] / media_volume if media_volume > _ZERO else Decimal("1")
    )

    sma20 = sum((candle["close"] for candle in recentes20), _ZERO) / Decimal(_JANELA)
    sma5 = sum((candle["close"] for candle in recentes5), _ZERO) / Decimal(5)
    tendencia = sma5 - sma20
    amplitude_atual = atual["high"] - atual["low"]

    is_trend = abs(tendencia) >= media_amplitude * Decimal("0.20")
    is_expansion = (
        amplitude_atual >= media_amplitude * Decimal("1.15")
        or rel_volume >= Decimal("1.10")
    )
    if not (is_trend and is_expansion):
        return 0

    momentum_curto = atual["close"] - recentes5[0]["close"]
    momentum_longo = atual["close"] - recentes20[0]["close"]
    if (
        tendencia > _ZERO
        and momentum_curto > _ZERO
        and momentum_longo > media_amplitude * _MOMENTUM_MULTIPLE
        and rel_volume >= _VOLUME_RATIO
    ):
        return 1
    return 0


def gerar_sinal(row) -> int:
    """Retorna 1 para compra dual-momentum confirmada; caso contrário, 0."""
    barras = _normalizar_barras(row)
    if len(barras) < _JANELA + 1:
        return 0

    atual = barras[-1]
    sinal_atual = _sinal_bruto(atual, barras[:-1])
    if sinal_atual == 0:
        return 0

    # No original, um sinal None zera _last_direction. Como esta hipótese é
    # long-only, o sinal bruto do candle imediatamente anterior é suficiente
    # para reconstruir causalmente essa supressão sem memória entre chamadas.
    sinal_anterior = 0
    if len(barras) >= _JANELA + 2:
        sinal_anterior = _sinal_bruto(barras[-2], barras[-(2 + _JANELA):-2])
    return 0 if sinal_anterior == sinal_atual else sinal_atual


__all__ = ["gerar_sinal"]
