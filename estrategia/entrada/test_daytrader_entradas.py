"""V465 (laboratorio, entradas): ponte `auxiliar/daytrader_ohlc` do pacote strategies.
Arquivo `test_*`: o classificador nao o trata como candidata.
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/entrada -p 'test_*.py'"""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from motor import Candle, construir_row
from estrategia.entrada.auxiliar.daytrader_ohlc import gerar_sinal_compat


def candle_dict(indice, abertura=100.0, maxima=105.0, minima=95.0, fechamento=100.0):
    return {
        "dt": datetime(2026, 1, 2, 9, 0) + timedelta(minutes=15 * indice),
        "Abertura": abertura,
        "Maximo": maxima,
        "Minimo": minima,
        "Fechamento": fechamento,
    }


class EstrategiasImportadas(unittest.TestCase):
    def test_motor_fornece_janela_ohlc_ampliada_sem_mudar_o_candle_atual(self):
        inicio = datetime(2026, 1, 2, 9, 0)
        candles = [
            Candle(
                horario=inicio + timedelta(minutes=15 * i),
                abertura=100_000.0 + i,
                maxima=100_020.0 + i,
                minima=99_980.0 + i,
                fechamento=100_005.0 + i,
            )
            for i in range(120)
        ]
        row = construir_row(candles)
        self.assertIsNotNone(row)
        self.assertEqual(len(row["ohlc_recentes"]), 96)
        self.assertEqual(row["ohlc_recentes"][-1]["dt"], candles[-1].horario)


    def test_reversao_de_canal_compra(self):
        candles = [candle_dict(i) for i in range(21)]
        candles.append(candle_dict(21, abertura=90, maxima=91, minima=85, fechamento=87))
        row = {"ohlc_recentes": tuple(candles)}
        self.assertEqual(gerar_sinal_compat(row, "channel_reversion_long"), 1)


    def test_falso_rompimento_venda(self):
        candles = [candle_dict(i) for i in range(21)]
        candles.append(candle_dict(21, abertura=106, maxima=107, minima=99, fechamento=104))
        row = {"ohlc_recentes": tuple(candles)}
        self.assertEqual(gerar_sinal_compat(row, "failed_break_short"), -1)


    def test_sinal_repetido_no_candle_seguinte_e_suprimido(self):
        candles = [candle_dict(i) for i in range(20)]
        candles.append(candle_dict(20, abertura=90, maxima=91, minima=84, fechamento=86))
        candles.append(candle_dict(21, abertura=89, maxima=90, minima=83, fechamento=85))
        row = {"ohlc_recentes": tuple(candles)}
        self.assertEqual(gerar_sinal_compat(row, "channel_reversion_long"), 0)


if __name__ == "__main__":
    unittest.main()
