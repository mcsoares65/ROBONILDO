"""Proteção separada das estratégias OHLC importadas do pacote ``strategies``.

As nove entradas compatíveis do pacote original calculavam a mesma proteção:
stop de 1,25 vez a amplitude média dos 20 candles anteriores, com piso de
20 pontos, e alvo de 2R. Este cartucho preserva essa fórmula sem manter estado
e sem fechar antecipadamente a posição.
"""

from decimal import Decimal
from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_daytrader_rr2_v1"
JANELA = 20
MULTIPLICADOR_STOP = Decimal("1.25")
STOP_MINIMO = Decimal("20")
RR = Decimal("2")


def _numero(valor) -> Decimal:
    try:
        numero = Decimal(str(valor))
    except Exception as erro:
        raise ValueError(f"Valor OHLC inválido: {valor!r}") from erro
    if not numero.is_finite():
        raise ValueError(f"Valor OHLC não finito: {valor!r}")
    return numero


def _distancias(row: dict) -> tuple[Decimal, Decimal]:
    ohlc = row.get("ohlc_recentes") or ()
    if len(ohlc) < JANELA + 1:
        raise ValueError("São necessários 20 candles anteriores para a proteção.")

    anteriores = ohlc[-(JANELA + 1):-1]
    amplitudes = [
        _numero(candle["Maximo"]) - _numero(candle["Minimo"])
        for candle in anteriores
    ]
    media = sum(amplitudes, Decimal("0")) / Decimal(JANELA)
    stop = max(STOP_MINIMO, (media * MULTIPLICADOR_STOP).quantize(Decimal("1")))
    alvo = max(stop + Decimal("5"), (stop * RR).quantize(Decimal("1")))
    return stop, alvo


def _protecao_inicial(row: dict, posicao: dict) -> tuple[float, float]:
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    stop_pts, alvo_pts = _distancias(row)
    stop_pts_f = float(stop_pts)
    alvo_pts_f = float(alvo_pts)

    if lado == "COMPRA":
        stop, alvo = entrada - stop_pts_f, entrada + alvo_pts_f
    elif lado == "VENDA":
        stop, alvo = entrada + stop_pts_f, entrada - alvo_pts_f
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if not isfinite(stop) or not isfinite(alvo):
        raise ValueError("Proteção inicial não finita.")
    return stop, alvo


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    if int(posicao.get("candles_decorridos", 0)) == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row: dict, posicao: dict):
    if int(posicao.get("candles_decorridos", 0)) != 0:
        return None
    stop, alvo = _distancias(row)
    return f"Proteção importada: stop de {stop:.0f} pontos e alvo de {alvo:.0f} pontos (2R)."


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
