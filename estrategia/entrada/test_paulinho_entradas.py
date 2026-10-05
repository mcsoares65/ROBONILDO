"""V466 (laboratorio, entradas): cartuchos do metodo Just explicados por Paulinho.
Arquivo com prefixo `_`: o classificador nao o trata como candidata (Regra 7).
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/entrada -p '_test_*.py'"""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from estrategia.entrada._paulinho_just import (
    sinal_fechamento_anterior,
    sinal_origem_intradiaria,
)


def candle(dt, abertura, maxima, minima, fechamento):
    return {
        "dt": dt,
        "Abertura": abertura,
        "Maximo": maxima,
        "Minimo": minima,
        "Fechamento": fechamento,
    }


class EstrategiasPaulinho(unittest.TestCase):
    def test_rejeicao_de_alta_a_partir_do_fechamento_anterior_vende(self):
        d1 = datetime(2026, 9, 1, 18, 0)
        d2 = datetime(2026, 9, 2, 9, 0)
        row = {"ohlc_recentes": (
            candle(d1, 99_900, 100_100, 99_800, 100_000),
            candle(d2, 100_550, 100_650, 100_500, 100_620),
            candle(d2 + timedelta(minutes=15), 100_620, 100_640, 100_520, 100_550),
        )}
        self.assertEqual(sinal_fechamento_anterior(row), -1)


    def test_rejeicao_de_baixa_a_partir_do_fechamento_anterior_compra(self):
        d1 = datetime(2026, 9, 1, 18, 0)
        d2 = datetime(2026, 9, 2, 9, 0)
        row = {"ohlc_recentes": (
            candle(d1, 100_100, 100_200, 99_900, 100_000),
            candle(d2, 99_450, 99_500, 99_350, 99_380),
            candle(d2 + timedelta(minutes=15), 99_380, 99_500, 99_360, 99_450),
        )}
        self.assertEqual(sinal_fechamento_anterior(row), 1)


    def test_origem_intradiaria_e_ancorada_antes_da_confirmacao(self):
        inicio = datetime(2026, 9, 2, 9, 0)
        row = {"ohlc_recentes": (
            candle(inicio, 100_050, 100_100, 100_000, 100_050),
            candle(inicio + timedelta(minutes=15), 100_200, 100_300, 100_100, 100_250),
            candle(inicio + timedelta(minutes=30), 100_550, 100_650, 100_500, 100_620),
            candle(inicio + timedelta(minutes=45), 100_620, 100_640, 100_520, 100_550),
        )}
        self.assertEqual(sinal_origem_intradiaria(row), -1)


    def test_sem_rejeicao_confirmada_nao_antecipa_operacao(self):
        d1 = datetime(2026, 9, 1, 18, 0)
        d2 = datetime(2026, 9, 2, 9, 0)
        row = {"ohlc_recentes": (
            candle(d1, 99_900, 100_100, 99_800, 100_000),
            candle(d2, 100_550, 100_700, 100_500, 100_650),
            candle(d2 + timedelta(minutes=15), 100_650, 100_800, 100_620, 100_780),
        )}
        self.assertEqual(sinal_fechamento_anterior(row), 0)


if __name__ == "__main__":
    unittest.main()
