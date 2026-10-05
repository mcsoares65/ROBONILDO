"""Reversao confirmada a 0,60% da origem intradiaria (metodo Just/WIN)."""

from estrategia.entrada.auxiliar.paulinho_just import sinal_origem_intradiaria


def gerar_sinal(row) -> int:
    return sinal_origem_intradiaria(row)
