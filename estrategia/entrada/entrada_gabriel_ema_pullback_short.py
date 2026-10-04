"""Candidata independente: ``ema_pullback_short``.

Autoria: Gabriel (fonte do ZIP ``strategies``) / adaptação Manus.
Variações testadas antes desta versão: 0. Revisão humana integral: pendente.
A fonte original emite venda quando a tendência SMA(5)-SMA(20) é descendente,
passa o filtro de regime e o candle atual faz o pullback definido pela fonte.
A memória de supressão de sinais consecutivos é reconstruída causalmente a
partir de ``row["gabriel_barras"]``; não há estado entre chamadas.

Quantidade por candle: não é necessária para a decisão desta hipótese. A
fonte calcula ``rel_vol``, mas nunca o usa em um filtro, sinal ou saída; por
isso ``Quantidade=None`` não é convertido em zero nem bloqueia uma decisão.
Se uma futura derivação tornar volume necessário, a ausência deverá retornar
0, sem fabricar volume.

Esta é uma candidata, não titular, e não alegará validação oficial. O arquivo
não importa módulos do projeto e não faz I/O, rede, exec/eval ou histórico.
"""

from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")
JANELA = 20
SLOPE_MULTIPLE = Decimal("0.25")
REGIME_THRESHOLD = Decimal("0.20")
PULLBACK_FRACTION = Decimal("0.50")


def _numero(valor) -> Decimal:
    """Converte um OHLC finito sem depender do tipo numérico do motor."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as erro:
        raise ValueError(f"OHLC inválido: {valor!r}") from erro
    if not numero.is_finite():
        raise ValueError(f"OHLC não finito: {valor!r}")
    return numero


def _candle(candle: dict) -> dict[str, Decimal]:
    return {
        "high": _numero(candle["Maximo"]),
        "low": _numero(candle["Minimo"]),
        "close": _numero(candle["Fechamento"]),
    }


def _sinal_bruto(candle: dict[str, Decimal], prior: list[dict[str, Decimal]]) -> int:
    """Replica ``_signal`` da fonte para um candle e seus 20 anteriores."""
    if len(prior) < JANELA:
        return 0

    recentes20 = prior[-JANELA:]
    recentes5 = prior[-5:]
    sma20 = sum((item["close"] for item in recentes20), ZERO) / Decimal(JANELA)
    sma5 = sum((item["close"] for item in recentes5), ZERO) / Decimal(5)
    media_amplitude = (
        sum((item["high"] - item["low"] for item in recentes20), ZERO)
        / Decimal(JANELA)
    )
    tendencia = sma5 - sma20

    # PARAMETERS da fonte: regime_filter="trend".
    if abs(tendencia) < media_amplitude * REGIME_THRESHOLD:
        return 0

    # PARAMETERS da fonte: slope_multiple="0.25" e pullback_fraction="0.50".
    if (
        tendencia < -media_amplitude * SLOPE_MULTIPLE
        and candle["high"] >= sma5
        and candle["close"] < sma5 + media_amplitude * PULLBACK_FRACTION
    ):
        return -1
    return 0


def gerar_sinal(row) -> int:
    """Retorna ``-1`` (venda) ou ``0`` usando somente candles já fornecidos."""
    if not isinstance(row, dict):
        return 0

    historico = row.get("gabriel_barras") or ()
    # Com 20 candles anteriores e o candle atual há informação suficiente para
    # a primeira avaliação; com 22 também se reconstrói o filtro do candle
    # anterior, equivalente a _last_direction sem manter memória própria.
    if len(historico) < JANELA + 1:
        return 0

    try:
        atual = _candle(historico[-1])
        anteriores = [_candle(item) for item in historico[-(JANELA + 1):-1]]
        sinal = _sinal_bruto(atual, anteriores)
        if sinal == 0:
            return 0

        # No original, um sinal só é suprimido quando o candle imediatamente
        # anterior também satisfez a regra; qualquer candle sem sinal zera a
        # direção lembrada. Com apenas 21 candles, o anterior tinha menos de
        # 20 precedentes e portanto era necessariamente sem sinal.
        if len(historico) >= JANELA + 2:
            candle_anterior = _candle(historico[-2])
            precedentes_anterior = [
                _candle(item) for item in historico[-(JANELA + 2):-2]
            ]
            if _sinal_bruto(candle_anterior, precedentes_anterior) == sinal:
                return 0
        return sinal
    except (KeyError, TypeError, ValueError, IndexError):
        # Dados indispensáveis de OHLC ausentes ou inválidos não geram entrada.
        return 0


__all__ = ["gerar_sinal"]
