"""Laboratorio (saida composta): stop estrutural limitado a 1,80 ATR, alvo na MA21 quando
ha 1R de distancia (senao 1,55R) e corte das 18h so depois das 18:00.
Arquivo `test_*`: o classificador nao o trata como candidata.
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/saida -p 'test_*.py'"""
import importlib.util
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))


def carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "estrategia" / "saida" / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def janela(minima, maxima, n=5, hora=datetime(2026, 3, 4, 13, 0)):
    return tuple({"dt": hora + timedelta(minutes=15 * i), "Abertura": 0.0, "Maximo": float(maxima),
                  "Minimo": float(minima), "Fechamento": 0.0} for i in range(n))


def linha(candles, atr=200.0, ma21=100000.0, hora=datetime(2026, 3, 4, 13, 0)):
    return {"dt": hora, "atr": atr, "MA21": ma21, "ohlc_recentes": candles}


def pos(lado="COMPRA", entrada=100000.0, candles=0, flutuante=0.0):
    return {"lado": lado, "entrada": entrada, "candles_decorridos": candles,
            "resultado_flutuante_pts": flutuante}


class Abertura(unittest.TestCase):
    m = carregar("saida_composta_stop_atr_alvo_ma21_claude_v1")

    def test_stop_estrutural_dentro_do_limite_de_atr(self):
        row = linha(janela(99900, 100100), atr=200.0)          # risco 100 < 1,8*200
        c = self.m.avaliar_saida(row, pos("COMPRA"))
        v = self.m.avaliar_saida(row, pos("VENDA"))
        self.assertEqual(c["novo_stop"], 99900.0)
        self.assertEqual(v["novo_stop"], 100100.0)

    def test_stop_limitado_a_1_8_atr(self):
        row = linha(janela(99000, 101000), atr=200.0)          # estrutural 1000 -> cap 360
        self.assertAlmostEqual(self.m.avaliar_saida(row, pos("COMPRA"))["novo_stop"], 99640.0)
        self.assertAlmostEqual(self.m.avaliar_saida(row, pos("VENDA"))["novo_stop"], 100360.0)

    def test_alvo_na_ma21_quando_ha_1r_de_distancia(self):
        row = linha(janela(99900, 100100), ma21=100300.0)      # distancia 300 >= 1R (100)
        self.assertEqual(self.m.avaliar_saida(row, pos("COMPRA"))["novo_alvo"], 100300.0)
        row = linha(janela(99900, 100100), ma21=99700.0)
        self.assertEqual(self.m.avaliar_saida(row, pos("VENDA"))["novo_alvo"], 99700.0)

    def test_alvo_1_55r_quando_a_ma21_esta_perto_ou_do_lado_errado(self):
        row = linha(janela(99900, 100100), ma21=100050.0)      # so 50 pts
        self.assertAlmostEqual(self.m.avaliar_saida(row, pos("COMPRA"))["novo_alvo"], 100155.0)
        row = linha(janela(99900, 100100), ma21=99800.0)       # MA21 contra a compra
        self.assertAlmostEqual(self.m.avaliar_saida(row, pos("COMPRA"))["novo_alvo"], 100155.0)

    def test_alvo_usa_risco_estrutural_original_quando_ha_cap(self):
        row = linha(janela(99000, 101000), atr=200.0, ma21=100000.0)
        self.assertAlmostEqual(self.m.avaliar_saida(row, pos("COMPRA"))["novo_alvo"], 101550.0)

    def test_sem_atr_valido_preserva_o_stop_estrutural(self):
        row = linha(janela(99900, 100100), atr=None)
        self.assertEqual(self.m.avaliar_saida(row, pos("COMPRA"))["novo_stop"], 99900.0)

    def test_entradas_invalidas(self):
        with self.assertRaises(ValueError):
            self.m.avaliar_saida(linha(janela(99900, 100100)), pos("XPTO"))
        with self.assertRaises(ValueError):
            self.m.avaliar_saida(linha(janela(99900, 100100, n=3)), pos("COMPRA"))
        with self.assertRaises(ValueError):                       # stop acima da entrada
            self.m.avaliar_saida(linha(janela(100100, 100200)), pos("COMPRA"))
        with self.assertRaises(TypeError):
            self.m.avaliar_saida(None, pos())


class CorteDas18h(unittest.TestCase):
    m = carregar("saida_composta_stop_atr_alvo_ma21_claude_v1")

    def test_fecha_depois_das_18_com_perda_de_meio_atr(self):
        row = linha(janela(99900, 100100), atr=200.0, hora=datetime(2026, 3, 4, 18, 0))
        self.assertTrue(self.m.avaliar_saida(row, pos(candles=2, flutuante=-100.0))["fechar"])

    def test_nao_fecha_antes_das_18_ou_com_perda_menor(self):
        cedo = linha(janela(99900, 100100), atr=200.0, hora=datetime(2026, 3, 4, 17, 45))
        self.assertFalse(self.m.avaliar_saida(cedo, pos(candles=2, flutuante=-500.0))["fechar"])
        tarde = linha(janela(99900, 100100), atr=200.0, hora=datetime(2026, 3, 4, 18, 15))
        self.assertFalse(self.m.avaliar_saida(tarde, pos(candles=2, flutuante=-99.0))["fechar"])
        self.assertFalse(self.m.avaliar_saida(tarde, pos(candles=2, flutuante=300.0))["fechar"])

    def test_depois_da_abertura_nao_mexe_em_stop_nem_alvo(self):
        r = self.m.avaliar_saida(linha(janela(99900, 100100)), pos(candles=3))
        self.assertEqual(r, {"fechar": False, "novo_stop": None, "novo_alvo": None})


if __name__ == "__main__":
    unittest.main()
