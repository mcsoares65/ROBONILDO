import importlib.util
import unittest
from datetime import datetime
from pathlib import Path


CAMINHO = (Path(__file__).resolve().parents[1] / "saida" /
           "saida_chatgpt_estrutura_assimetrica_v1.py")
SPEC = importlib.util.spec_from_file_location("saida_chatgpt_estrutura_assimetrica_v1", CAMINHO)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def row(atr=100.0):
    candles = [
        {"Minimo": 900.0, "Maximo": 1_080.0},
        {"Minimo": 920.0, "Maximo": 1_070.0},
        {"Minimo": 940.0, "Maximo": 1_060.0},
        {"Minimo": 950.0, "Maximo": 1_050.0},
    ]
    return {"dt": datetime(2026, 1, 2, 10, 0), "atr": atr,
            "ohlc_recentes": candles}


class SaidaEstruturaAtrRR19Test(unittest.TestCase):
    def test_compra_limita_stop_e_preserva_alvo_estrutural(self):
        pos = {"entrada": 1_200.0, "lado": "COMPRA", "candles_decorridos": 0}
        r = MOD.avaliar_saida(row(), pos)
        self.assertEqual(r["novo_stop"], 990.0)
        self.assertEqual(r["novo_alvo"], 1_770.0)
        self.assertFalse(r["fechar"])

    def test_venda_limita_stop_e_preserva_alvo_estrutural(self):
        pos = {"entrada": 800.0, "lado": "VENDA", "candles_decorridos": 0}
        r = MOD.avaliar_saida(row(), pos)
        self.assertEqual(r["novo_stop"], 1_010.0)
        self.assertEqual(r["novo_alvo"], 366.0)
        self.assertFalse(r["fechar"])

    def test_depois_da_abertura_nao_antecipa_saida(self):
        pos = {"entrada": 1_200.0, "lado": "COMPRA", "candles_decorridos": 1}
        self.assertEqual(MOD.avaliar_saida(row(), pos), {
            "fechar": False, "novo_stop": None, "novo_alvo": None})


if __name__ == "__main__":
    unittest.main()
