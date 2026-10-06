"""Protecao percentual descrita para o metodo Just: 0,20% de stop e 0,40% de alvo."""

from math import ceil, isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_percentual_just_v01"
STOP_PCT = 0.002
ALVO_PCT = 0.004
TICK_WIN = 5.0


def _distancia_em_ticks(entrada: float, percentual: float) -> float:
    return ceil((entrada * percentual) / TICK_WIN) * TICK_WIN


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionarios.")
    if int(posicao.get("candles_decorridos", 0)) != 0:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    entrada = float(posicao["entrada"])
    if not isfinite(entrada) or entrada <= 0:
        raise ValueError("Preco de entrada invalido.")
    stop_pts = _distancia_em_ticks(entrada, STOP_PCT)
    alvo_pts = _distancia_em_ticks(entrada, ALVO_PCT)
    lado = str(posicao["lado"]).upper()
    if lado == "COMPRA":
        stop, alvo = entrada - stop_pts, entrada + alvo_pts
    elif lado == "VENDA":
        stop, alvo = entrada + stop_pts, entrada - alvo_pts
    else:
        raise ValueError(f"Lado invalido: {lado}")
    return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}


def diagnosticar_saida(row: dict, posicao: dict):
    if int(posicao.get("candles_decorridos", 0)) != 0:
        return None
    entrada = float(posicao["entrada"])
    stop = _distancia_em_ticks(entrada, STOP_PCT)
    alvo = _distancia_em_ticks(entrada, ALVO_PCT)
    return f"Metodo Just: stop de {stop:.0f} pontos e alvo de {alvo:.0f} pontos (2R)."


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
