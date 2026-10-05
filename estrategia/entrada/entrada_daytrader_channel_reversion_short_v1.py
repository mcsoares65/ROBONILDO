"""Reversão de canal para venda, adaptada do pacote strategies."""

from estrategia.entrada.auxiliar.daytrader_ohlc import gerar_sinal_compat


def gerar_sinal(row) -> int:
    return gerar_sinal_compat(row, "channel_reversion_short")
