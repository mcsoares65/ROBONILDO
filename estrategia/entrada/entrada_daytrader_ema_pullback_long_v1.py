"""Pullback de tendência para compra, adaptado do pacote strategies."""

from estrategia.entrada._daytrader_ohlc import gerar_sinal_compat


def gerar_sinal(row) -> int:
    return gerar_sinal_compat(row, "ema_pullback_long")
