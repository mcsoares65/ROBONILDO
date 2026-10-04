"""Falso rompimento confirmado para compra, adaptado do pacote strategies."""

from estrategia.entrada._daytrader_ohlc import gerar_sinal_compat


def gerar_sinal(row) -> int:
    return gerar_sinal_compat(row, "failed_break_long_v2")
