import unittest

from estrategia.saida.saida_eficiencia_adaptativa_v01 import avaliar_saida


def candle(abertura, maxima, minima, fechamento):
    return {
        "Abertura": abertura,
        "Maximo": maxima,
        "Minimo": minima,
        "Fechamento": fechamento,
    }


class SaidaEficienciaAdaptativaTest(unittest.TestCase):
    def setUp(self):
        self.base = [
            candle(96, 98, 94, 97),
            candle(97, 99, 93, 98),
            candle(98, 101, 95, 100),
            candle(100, 102, 96, 101),
            candle(101, 103, 90, 100),
        ]

    def test_abertura_compra_define_stop_sem_alvo(self):
        resposta = avaliar_saida(
            {"ohlc_recentes": self.base},
            {"lado": "COMPRA", "entrada": 100, "candles_decorridos": 0},
        )
        self.assertEqual(90, resposta["novo_stop"])
        self.assertIsNone(resposta["novo_alvo"])

    def test_nao_ativa_antes_de_um_r(self):
        serie = self.base + [candle(100, 106, 99, 105)]
        resposta = avaliar_saida(
            {"ohlc_recentes": serie},
            {"lado": "COMPRA", "entrada": 100, "candles_decorridos": 1},
        )
        self.assertIsNone(resposta["novo_stop"])

    def test_stop_de_compra_funciona_como_catraca(self):
        serie2 = self.base + [
            candle(100, 111, 99, 109),
            candle(109, 114, 108, 113),
        ]
        pos2 = {"lado": "COMPRA", "entrada": 100, "candles_decorridos": 2}
        stop2 = avaliar_saida({"ohlc_recentes": serie2}, pos2)["novo_stop"]

        serie3 = serie2 + [candle(113, 114, 105, 106)]
        pos3 = {"lado": "COMPRA", "entrada": 100, "candles_decorridos": 3}
        stop3 = avaliar_saida({"ohlc_recentes": serie3}, pos3)["novo_stop"]
        self.assertGreaterEqual(stop3, stop2)

    def test_abertura_venda_define_stop_sem_alvo(self):
        resposta = avaliar_saida(
            {"ohlc_recentes": self.base},
            {"lado": "VENDA", "entrada": 100, "candles_decorridos": 0},
        )
        self.assertEqual(103, resposta["novo_stop"])
        self.assertIsNone(resposta["novo_alvo"])

    def test_stop_de_venda_funciona_como_catraca(self):
        base = [
            candle(104, 106, 102, 103),
            candle(103, 105, 101, 102),
            candle(102, 104, 99, 101),
            candle(101, 103, 98, 100),
            candle(100, 110, 97, 100),
        ]
        serie2 = base + [
            candle(100, 101, 89, 91),
            candle(91, 92, 86, 87),
        ]
        pos2 = {"lado": "VENDA", "entrada": 100, "candles_decorridos": 2}
        stop2 = avaliar_saida({"ohlc_recentes": serie2}, pos2)["novo_stop"]

        serie3 = serie2 + [candle(87, 96, 86, 95)]
        pos3 = {"lado": "VENDA", "entrada": 100, "candles_decorridos": 3}
        stop3 = avaliar_saida({"ohlc_recentes": serie3}, pos3)["novo_stop"]
        self.assertLessEqual(stop3, stop2)


if __name__ == "__main__":
    unittest.main()
