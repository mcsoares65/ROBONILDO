"""Falso rompimento para venda, adaptado do pacote strategies."""

from estrategia.entrada.auxiliar.daytrader_ohlc import gerar_sinal_compat


def gerar_sinal(row) -> int:
    return gerar_sinal_compat(row, "failed_break_short")
