"""Candidata independente da hipótese ``structure_retest_long_v2``.

Autoria: Gabriel, a partir da fonte do ZIP; adaptação Manus. Revisão humana
pendente. Variações testadas antes desta versão: 0. A numeração ``v2`` no
nome identifica a versão da hipótese original de Gabriel, não a VERSAO do
projeto.

A adaptação reconstrói, de forma causal e sem estado global, a fila de candles
que a fonte mantinha usando ``row["gabriel_barras"]``. A fonte depende de
``Bar.volume``; assume-se que ``Quantidade`` seja a quantidade por candle na
mesma unidade esperada pela fonte. Se qualquer quantidade necessária estiver
ausente (``None``), o sinal é fechado em 0; quantidade ausente nunca é
substituída por zero.

A fonte emitia ``OrderIntent`` com stop de pontos e alvo de 2R. Essa proteção é
semanticamente idêntica à já existente em ``saida_daytrader_rr2_v1``; por isso
não é criada uma saída Gabriel duplicada. Este arquivo implementa somente
``gerar_sinal(row) -> -1 | 0 | 1`` e não afirma validação oficial.

Não importa módulos do projeto, não faz I/O, rede, leitura de arquivos,
``exec``/``eval`` nem mantém memória entre chamadas.
"""

from decimal import Decimal, InvalidOperation


_ZERO = Decimal("0")
_LOOKBACK = 20
_RETEST_FRACTION = Decimal("0.35")
_VOLUME_RATIO = Decimal("1.00")
_TREND_THRESHOLD = Decimal("0.20")
_EXPANSION_RANGE_RATIO = Decimal("1.15")
_EXPANSION_VOLUME_RATIO = Decimal("1.10")


def _decimal(value):
    """Converte um número finito para Decimal, ou devolve None se inválido."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() else None


def _normalizar_barras(row):
    """Lê apenas o contrato público Gabriel, preservando volume ausente."""
    if not isinstance(row, dict):
        raise TypeError("row precisa ser um dicionário.")

    historico = row.get("gabriel_barras") or ()
    barras = []
    for candle in historico:
        if not isinstance(candle, dict):
            return None
        abertura = _decimal(candle.get("Abertura"))
        maxima = _decimal(candle.get("Maximo"))
        minima = _decimal(candle.get("Minimo"))
        fechamento = _decimal(candle.get("Fechamento"))
        if None in (abertura, maxima, minima, fechamento):
            return None
        if maxima < minima:
            return None

        quantidade_bruta = candle.get("Quantidade")
        quantidade = (
            None
            if quantidade_bruta is None
            else _decimal(quantidade_bruta)
        )
        if quantidade is not None and quantidade < _ZERO:
            return None
        if quantidade_bruta is not None and quantidade is None:
            return None

        barras.append(
            {
                "open": abertura,
                "high": maxima,
                "low": minima,
                "close": fechamento,
                "volume": quantidade,
            }
        )
    return barras


def _sinal_bruto_at(barras, indice):
    """Calcula o sinal da fonte no índice, antes da supressão de repetição."""
    if indice < _LOOKBACK:
        return None

    atual = barras[indice]
    anterior = barras[:indice]
    recentes20 = anterior[-_LOOKBACK:]
    recentes5 = anterior[-5:]

    # A hipótese original calcula rel_vol em todo candle; volume é dado
    # indispensável, inclusive quando a expansão de range já seria suficiente.
    volumes = [candle["volume"] for candle in recentes20]
    if atual["volume"] is None or any(volume is None for volume in volumes):
        return None

    sma20 = sum((candle["close"] for candle in recentes20), _ZERO) / Decimal(_LOOKBACK)
    sma5 = sum((candle["close"] for candle in recentes5), _ZERO) / Decimal(5)
    avg_range20 = (
        sum((candle["high"] - candle["low"] for candle in recentes20), _ZERO)
        / Decimal(_LOOKBACK)
    )
    avg_volume20 = sum(volumes, _ZERO) / Decimal(_LOOKBACK)
    rel_volume = (
        atual["volume"] / avg_volume20
        if avg_volume20 > _ZERO
        else Decimal("1")
    )

    trend = sma5 - sma20
    current_range = atual["high"] - atual["low"]
    is_trend = abs(trend) >= avg_range20 * _TREND_THRESHOLD
    is_expansion = (
        current_range >= avg_range20 * _EXPANSION_RANGE_RATIO
        or rel_volume >= _EXPANSION_VOLUME_RATIO
    )
    if not (is_trend and is_expansion):
        return None

    prev_bar = anterior[-1]
    # Igual à fonte: o nível exclui o candle imediatamente anterior, que é o
    # candle que confirmou o rompimento antes do reteste atual.
    base = anterior[:-1][-_LOOKBACK:]
    if not base:
        return None
    level_hi = max(candle["high"] for candle in base)
    tolerance = avg_range20 * _RETEST_FRACTION

    prev_break_up = prev_bar["close"] > level_hi
    if (
        prev_break_up
        and atual["low"] <= level_hi + tolerance
        and atual["close"] > level_hi
        and atual["close"] > atual["open"]
        and rel_volume >= _VOLUME_RATIO
    ):
        return 1
    return None


def gerar_sinal(row) -> int:
    """Retorna compra (1) ou nada (0), sem emitir venda para esta hipótese."""
    barras = _normalizar_barras(row)
    if barras is None or len(barras) < _LOOKBACK + 1:
        return 0

    indice_atual = len(barras) - 1
    sinal_atual = _sinal_bruto_at(barras, indice_atual)
    if sinal_atual is None:
        return 0

    # A fonte zera _last_direction quando o candle anterior não gera sinal e
    # suprime apenas a repetição de um sinal consecutivo. Com a janela causal,
    # o sinal bruto do índice anterior reproduz essa transição sem memória.
    if indice_atual >= _LOOKBACK + 1:
        sinal_anterior = _sinal_bruto_at(barras, indice_atual - 1)
        if sinal_anterior == sinal_atual:
            return 0
    return int(sinal_atual)


__all__ = ["gerar_sinal"]
