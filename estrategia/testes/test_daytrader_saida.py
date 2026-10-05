"""V465 (laboratorio, saidas): saida comum do pacote strategies (stop 1,25x e alvo 2R).
Arquivo `test_*`: o classificador nao o trata como candidata.
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/testes -p 'test_*.py'"""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from estrategia.saida.desclassificadas.saida_daytrader_rr2_v1 import avaliar_saida


def candle_dict(indice, abertura=100.0, maxima=105.0, minima=95.0, fechamento=100.0):
    return {
        "dt": datetime(2026, 1, 2, 9, 0) + timedelta(minutes=15 * indice),
        "Abertura": abertura,
        "Maximo": maxima,
        "Minimo": minima,
        "Fechamento": fechamento,
    }


class SaidaDaytraderImportada(unittest.TestCase):
    def test_saida_comum_reproduz_stop_125_e_alvo_2r(self):
        # Os 20 candles anteriores têm amplitude de 100 pontos. Logo:
        # stop = 100 * 1,25 = 125; alvo = 2R = 250.
        candles = [candle_dict(i, 1_000, 1_050, 950, 1_000) for i in range(21)]
        candles.append(candle_dict(21, 1_000, 1_020, 980, 1_000))
        row = {"ohlc_recentes": tuple(candles)}

        compra = avaliar_saida(row, {"lado": "COMPRA", "entrada": 1_000, "candles_decorridos": 0})
        venda = avaliar_saida(row, {"lado": "VENDA", "entrada": 1_000, "candles_decorridos": 0})
        self.assertEqual((compra["novo_stop"], compra["novo_alvo"]), (875.0, 1_250.0))
        self.assertEqual((venda["novo_stop"], venda["novo_alvo"]), (1_125.0, 750.0))

    def test_saida_nao_fecha_antecipadamente(self):
        resposta = avaliar_saida({}, {"lado": "COMPRA", "entrada": 1_000, "candles_decorridos": 1})
        self.assertEqual(resposta, {"fechar": False, "novo_stop": None, "novo_alvo": None})


if __name__ == "__main__":
    unittest.main()
