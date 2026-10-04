"""Reversao confirmada a 0,60% do fechamento anterior (metodo Just/WIN)."""

from estrategia.entrada._paulinho_just import sinal_fechamento_anterior


def gerar_sinal(row) -> int:
    return sinal_fechamento_anterior(row)
