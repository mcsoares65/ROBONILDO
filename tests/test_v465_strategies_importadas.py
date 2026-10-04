"""V465 - adaptação do pacote strategies aos cartuchos do Robonildo."""

import importlib
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor import Candle, construir_row
from estrategia.entrada._daytrader_ohlc import gerar_sinal_compat
from estrategia.saida.saida_daytrader_rr2_v1 import avaliar_saida


ENTRADAS = (
    "entrada_daytrader_channel_reversion_long_v1",
    "entrada_daytrader_channel_reversion_short_v1",
    "entrada_daytrader_channel_long_v2",
    "entrada_daytrader_channel_short_v2",
    "entrada_daytrader_ema_pullback_long_v1",
    "entrada_daytrader_failed_break_long_v1",
    "entrada_daytrader_failed_break_short_v1",
    "entrada_daytrader_failed_break_long_v2",
    "entrada_daytrader_failed_break_short_v2",
)


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

    def test_nove_cartuchos_publicos_respeitam_dominio_do_contrato(self):
        row = {"ohlc_recentes": tuple(candle_dict(i) for i in range(22))}
        for nome in ENTRADAS:
            with self.subTest(nome):
                modulo = importlib.import_module(f"estrategia.entrada.{nome}")
                self.assertIn(modulo.gerar_sinal(row), (-1, 0, 1))

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
