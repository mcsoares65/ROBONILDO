"""Adaptador comum das estratégias OHLC recebidas no pacote ``strategies``.

O pacote original usa objetos ``Bar`` e mantém uma fila interna. O Robonildo
exige cartuchos funcionais ``gerar_sinal(row)``. Esta ponte reproduz as regras
compatíveis apenas com OHLC usando os 22 candles fechados fornecidos pelo motor:
20 para a regra atual e mais um para reproduzir, sem estado global, a supressão
de sinais idênticos em candles consecutivos.

O arquivo começa com ``_`` para não ser tratado como cartucho pelo
``classificacao.py``. Somente os módulos públicos ao lado dele participam do
ranking.
"""

from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")
JANELA = 20


def _decimal(valor) -> Decimal:
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as erro:
        raise ValueError(f"OHLC inválido: {valor!r}") from erro
    if not numero.is_finite():
        raise ValueError(f"OHLC não finito: {valor!r}")
    return numero


def _candles(row: dict) -> list[dict[str, Decimal]]:
    historico = row.get("ohlc_recentes") or ()
    if len(historico) < JANELA + 2:
        return []
    return [
        {
            "open": _decimal(candle["Abertura"]),
            "high": _decimal(candle["Maximo"]),
            "low": _decimal(candle["Minimo"]),
            "close": _decimal(candle["Fechamento"]),
        }
        for candle in historico[-(JANELA + 2):]
    ]


def _estatisticas(prior: list[dict[str, Decimal]]):
    recentes20 = prior[-20:]
    recentes5 = prior[-5:]
    sma20 = sum((c["close"] for c in recentes20), ZERO) / Decimal(20)
    sma5 = sum((c["close"] for c in recentes5), ZERO) / Decimal(5)
    amplitude_media = (
        sum((c["high"] - c["low"] for c in recentes20), ZERO)
        / Decimal(20)
    )
    return recentes20, sma20, sma5, amplitude_media, sma5 - sma20


def _local_fechamento(candle: dict[str, Decimal]) -> Decimal:
    amplitude = candle["high"] - candle["low"]
    if amplitude <= ZERO:
        return Decimal("0.50")
    return (candle["close"] - candle["low"]) / amplitude


def _canal(candle, prior, lado: int, versao: int) -> int:
    _, sma20, _, amplitude, tendencia = _estatisticas(prior)
    if abs(tendencia) > amplitude * Decimal("0.35"):
        return 0

    if versao == 1:
        limite_tendencia = Decimal("0.30")
        desvio = Decimal("1.25")
    else:
        limite_tendencia = Decimal("0.20")
        desvio = Decimal("1.50")

    if abs(tendencia) > amplitude * limite_tendencia:
        return 0

    distancia = candle["close"] - sma20
    if lado == 1:
        extremo = distancia <= -(amplitude * desvio)
        confirmacao = (
            versao == 1
            or (_local_fechamento(candle) >= Decimal("0.65")
                and candle["close"] > candle["open"])
        )
    else:
        extremo = distancia >= amplitude * desvio
        confirmacao = (
            versao == 1
            or (_local_fechamento(candle) <= Decimal("0.35")
                and candle["close"] < candle["open"])
        )
    return lado if extremo and confirmacao else 0


def _ema_pullback_long(candle, prior) -> int:
    _, _, sma5, amplitude, tendencia = _estatisticas(prior)
    if abs(tendencia) < amplitude * Decimal("0.20"):
        return 0
    if (
        tendencia > amplitude * Decimal("0.25")
        and candle["low"] <= sma5
        and candle["close"] > sma5 - amplitude * Decimal("0.50")
    ):
        return 1
    return 0


def _falso_rompimento(candle, prior, lado: int, versao: int) -> int:
    recentes, _, _, amplitude, tendencia = _estatisticas(prior)
    if abs(tendencia) > amplitude * Decimal("0.35"):
        return 0

    if lado == 1:
        nivel = min(c["low"] for c in recentes)
        rompeu = candle["low"] < nivel
        reentrou = candle["close"] >= nivel + amplitude * (
            Decimal("0.20") if versao == 2 else ZERO
        )
        confirmou = (
            versao == 1
            or (candle["close"] > candle["open"]
                and _local_fechamento(candle) >= Decimal("0.60"))
        )
    else:
        nivel = max(c["high"] for c in recentes)
        rompeu = candle["high"] > nivel
        reentrou = candle["close"] <= nivel - amplitude * (
            Decimal("0.20") if versao == 2 else ZERO
        )
        confirmou = (
            versao == 1
            or (candle["close"] < candle["open"]
                and _local_fechamento(candle) <= Decimal("0.40"))
        )
    return lado if rompeu and reentrou and confirmou else 0


def _sinal_bruto(estrategia: str, candle, prior) -> int:
    regras = {
        "channel_reversion_long": lambda: _canal(candle, prior, 1, 1),
        "channel_reversion_short": lambda: _canal(candle, prior, -1, 1),
        "channel_long_v2": lambda: _canal(candle, prior, 1, 2),
        "channel_short_v2": lambda: _canal(candle, prior, -1, 2),
        "ema_pullback_long": lambda: _ema_pullback_long(candle, prior),
        "failed_break_long": lambda: _falso_rompimento(candle, prior, 1, 1),
        "failed_break_short": lambda: _falso_rompimento(candle, prior, -1, 1),
        "failed_break_long_v2": lambda: _falso_rompimento(candle, prior, 1, 2),
        "failed_break_short_v2": lambda: _falso_rompimento(candle, prior, -1, 2),
    }
    try:
        return regras[estrategia]()
    except KeyError as erro:
        raise ValueError(f"Estratégia importada desconhecida: {estrategia}") from erro


def gerar_sinal_compat(row: dict, estrategia: str) -> int:
    """Reproduz o ``on_bar`` original sem guardar estado entre chamadas."""
    if not isinstance(row, dict):
        raise TypeError("row precisa ser um dicionário.")
    candles = _candles(row)
    if not candles:
        return 0

    atual = _sinal_bruto(estrategia, candles[-1], candles[-21:-1])
    if atual == 0:
        return 0

    # No código recebido, _last_direction só é zerado quando o candle anterior
    # não satisfaz a regra. Comparar os dois sinais brutos reproduz exatamente
    # essa memória sem contaminar execuções sucessivas do laboratório.
    anterior = _sinal_bruto(estrategia, candles[-2], candles[-22:-2])
    return 0 if anterior == atual else atual


__all__ = ["gerar_sinal_compat"]
