"""Candidata independente: Pullback confirmado v2 — Compra.

Autoria: Gabriel, a partir do ZIP/fonte original; adaptação Manus.
Revisão humana pendente. Variações testadas: 0.
A hipótese original usa volume por candle; assume-se que ``Quantidade`` é a
mesma medida de quantidade de contratos/candle esperada pela fonte. ``None``
indica volume indisponível e não é convertido em zero: sem toda a quantidade
necessária, a função retorna 0. Esta é uma candidata, não uma titular, e não
há alegação de validação, classificação oficial ou teste histórico.

A fila e ``_last_direction`` da fonte orientada a objetos são reconstruídos
causalmente a partir de ``row["gabriel_barras"]``. São necessários 22 candles:
20 anteriores ao candle atual, mais o candle anterior para reproduzir a
supressão de sinais idênticos consecutivos.
"""

from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")
JANELA = 20
SLOPE_MULTIPLE = Decimal("0.30")
MIN_VOLUME_RATIO = Decimal("0.95")
REGIME_THRESHOLD = Decimal("0.20")


def _numero(valor, nome: str) -> Decimal:
    """Converte um campo numérico sem aceitar valores não finitos."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as erro:
        raise ValueError(f"{nome} inválido: {valor!r}") from erro
    if not numero.is_finite():
        raise ValueError(f"{nome} não finito: {valor!r}")
    return numero


def _ohlc(candle: dict) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Lê exatamente as chaves OHLC fornecidas pelo contrato Gabriel."""
    return (
        _numero(candle["Abertura"], "Abertura"),
        _numero(candle["Maximo"], "Maximo"),
        _numero(candle["Minimo"], "Minimo"),
        _numero(candle["Fechamento"], "Fechamento"),
    )


def _quantidade(candle: dict) -> Decimal | None:
    """Retorna None para quantidade ausente, sem fabricar volume."""
    quantidade = candle.get("Quantidade")
    if quantidade is None:
        return None
    numero = _numero(quantidade, "Quantidade")
    if numero < ZERO:
        raise ValueError(f"Quantidade negativa: {quantidade!r}")
    return numero


def _sinal_bruto(candle: dict, anteriores: list[dict]) -> int:
    """Reproduz a condição de ``_signal`` da fonte para um candle."""
    if len(anteriores) != JANELA:
        return 0

    atual_open, atual_high, atual_low, atual_close = _ohlc(candle)
    anteriores_ohlc = [_ohlc(item) for item in anteriores]
    quantidades = [_quantidade(item) for item in anteriores]
    quantidade_atual = _quantidade(candle)

    # A fonte usa volume do candle atual e dos 20 anteriores. Ausência em
    # qualquer desses pontos torna a decisão não portável; não usar zero.
    if quantidade_atual is None or any(item is None for item in quantidades):
        return 0
    volumes = [item for item in quantidades if item is not None]

    fechamentos = [item[3] for item in anteriores_ohlc]
    sma20 = sum(fechamentos, ZERO) / Decimal(JANELA)
    sma5 = sum(fechamentos[-5:], ZERO) / Decimal(5)
    media_amplitude = (
        sum((item[1] - item[2] for item in anteriores_ohlc), ZERO)
        / Decimal(JANELA)
    )
    media_volume = sum(volumes, ZERO) / Decimal(JANELA)

    rel_volume = (
        quantidade_atual / media_volume if media_volume > ZERO else Decimal("1")
    )
    tendencia = sma5 - sma20

    # regime_filter == "trend" é o único regime da fonte original.
    if abs(tendencia) < media_amplitude * REGIME_THRESHOLD:
        return 0

    # pullback_fraction = 0.35 é lido pela fonte original, mas não entra na
    # condição efetiva do sinal; preserva-se essa peculiaridade sem inventar
    # uma condição que a fonte não possui.
    if (
        tendencia > media_amplitude * SLOPE_MULTIPLE
        and atual_low <= sma5
        and atual_close > sma5
        and atual_close > anteriores_ohlc[-1][3]
        and rel_volume >= MIN_VOLUME_RATIO
        and (atual_close - atual_open) > ZERO
    ):
        return 1
    return 0


def gerar_sinal(row) -> int:
    """Retorna 1 para compra confirmada, ou 0 quando não há sinal seguro."""
    if not isinstance(row, dict):
        raise TypeError("row precisa ser um dicionário.")

    historico = row.get("gabriel_barras") or ()
    # A fonte necessita de 20 candles anteriores para o candle atual e de
    # mais um candle anterior para reconstruir _last_direction sem estado.
    if len(historico) < JANELA + 2:
        return 0

    barras = list(historico)
    atual = barras[-1]
    anteriores = barras[-(JANELA + 1):-1]
    sinal_atual = _sinal_bruto(atual, anteriores)
    if sinal_atual == 0:
        return 0

    candle_anterior = barras[-2]
    anteriores_do_anterior = barras[-(JANELA + 2):-2]
    sinal_anterior = _sinal_bruto(candle_anterior, anteriores_do_anterior)

    # on_bar zera _last_direction quando não há sinal e omite um novo sinal
    # quando a direção atual é igual à última direção sinalizada.
    return 0 if sinal_anterior == sinal_atual else sinal_atual


__all__ = ["gerar_sinal"]
