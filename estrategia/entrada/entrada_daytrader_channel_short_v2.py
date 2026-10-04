"""Reversão de canal confirmada para venda, adaptada do pacote strategies."""

from estrategia.entrada._daytrader_ohlc import gerar_sinal_compat


def gerar_sinal(row) -> int:
    return gerar_sinal_compat(row, "channel_short_v2")
