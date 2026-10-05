"""Reversão de canal confirmada para compra, adaptada do pacote strategies."""

from estrategia.entrada.auxiliar.daytrader_ohlc import gerar_sinal_compat


def gerar_sinal(row) -> int:
    return gerar_sinal_compat(row, "channel_long_v2")
