"""Regras mensuraveis extraidas da explicacao publica do metodo Just.

O entrevistado descreve duas referencias de exaustao: variacao percentual em
relacao ao fechamento anterior e variacao a partir da origem do movimento. No
WIN, ele informa que a primeira faixa comeca em 0,60%. Como o Robonildo decide
somente em candle fechado, esta adaptacao exige rejeicao confirmada da faixa;
nao tenta simular a ordem limite intrabar mostrada no video.
"""

from math import isfinite


VARIACAO_WIN = 0.006


def _candles(row: dict) -> list[dict]:
    historico = list(row.get("ohlc_recentes") or ())
    validos = []
    for candle in historico:
        try:
            abertura = float(candle["Abertura"])
            maxima = float(candle["Maximo"])
            minima = float(candle["Minimo"])
            fechamento = float(candle["Fechamento"])
            dt = candle["dt"]
        except (KeyError, TypeError, ValueError):
            return []
        if not all(isfinite(v) for v in (abertura, maxima, minima, fechamento)):
            return []
        validos.append({
            "dt": dt,
            "Abertura": abertura,
            "Maximo": maxima,
            "Minimo": minima,
            "Fechamento": fechamento,
        })
    return validos


def _data(candle: dict):
    dt = candle["dt"]
    return dt.date() if hasattr(dt, "date") else str(dt)[:10]


def _rejeicao(atual: dict, anterior: dict, superior: float, inferior: float) -> int:
    """Confirma falha da faixa no fechamento; sinais simultaneos se anulam."""
    venda = (
        max(anterior["Maximo"], atual["Maximo"]) >= superior
        and atual["Fechamento"] < superior
        and atual["Fechamento"] < atual["Abertura"]
    )
    compra = (
        min(anterior["Minimo"], atual["Minimo"]) <= inferior
        and atual["Fechamento"] > inferior
        and atual["Fechamento"] > atual["Abertura"]
    )
    if compra == venda:
        return 0
    return 1 if compra else -1


def sinal_fechamento_anterior(row: dict) -> int:
    candles = _candles(row)
    if len(candles) < 3:
        return 0
    atual, anterior = candles[-1], candles[-2]
    data_atual = _data(atual)
    sessoes_anteriores = [c for c in candles[:-1] if _data(c) != data_atual]
    if not sessoes_anteriores:
        return 0
    fechamento_anterior = sessoes_anteriores[-1]["Fechamento"]
    return _rejeicao(
        atual,
        anterior,
        fechamento_anterior * (1.0 + VARIACAO_WIN),
        fechamento_anterior * (1.0 - VARIACAO_WIN),
    )


def sinal_origem_intradiaria(row: dict) -> int:
    candles = _candles(row)
    if len(candles) < 4:
        return 0
    atual, anterior = candles[-1], candles[-2]
    data_atual = _data(atual)
    # A origem precisa existir antes dos dois candles usados na confirmacao.
    base = [c for c in candles[:-2] if _data(c) == data_atual]
    if not base:
        return 0
    origem_baixa = min(c["Minimo"] for c in base)
    origem_alta = max(c["Maximo"] for c in base)
    return _rejeicao(
        atual,
        anterior,
        origem_baixa * (1.0 + VARIACAO_WIN),
        origem_alta * (1.0 - VARIACAO_WIN),
    )


__all__ = ["sinal_fechamento_anterior", "sinal_origem_intradiaria"]
