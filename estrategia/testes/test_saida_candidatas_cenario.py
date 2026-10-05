"""LABORATORIO (saidas): cada candidata abre stop/alvo coerentes em compra e em venda
e administra a posicao depois da abertura. Linhas montadas a mao, sem dados reais.
Arquivo `test_*`: o classificador nao o trata como candidata.
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/testes -p 'test_*.py'"""
import importlib.util
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from apoio_cartuchos import caminho_cartucho  # noqa: E402


def carregar(pasta, nome):
    spec = importlib.util.spec_from_file_location(nome, caminho_cartucho(pasta, nome))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def candle(dt, o, h, l, c):
    return {"dt": dt, "Abertura": float(o), "Maximo": float(h), "Minimo": float(l), "Fechamento": float(c)}


def linha(candles, **extra):
    ultimo = candles[-1]
    base = {"dt": ultimo["dt"], "Abertura": ultimo["Abertura"], "Maximo": ultimo["Maximo"],
            "Minimo": ultimo["Minimo"], "Fechamento": ultimo["Fechamento"], "MA21": ultimo["Fechamento"],
            "MA50": ultimo["Fechamento"], "trend": 0, "atr": 200.0, "atr_relativo": 1.0, "rsi": 50.0,
            "rsi_subindo": False, "rsi_descendo": False, "stoch": 50.0, "stoch_subindo": False,
            "stoch_descendo": False, "ohlc_recentes": tuple(candles)}
    base.update(extra)
    return base


def sequencia(inicio, ohlcs):
    return [candle(inicio + timedelta(minutes=15 * i), *x) for i, x in enumerate(ohlcs)]


def janela_saida(n=12, base=100000.0, passo=0.0, folga=60.0):
    inicio = datetime(2026, 3, 4, 13, 0)
    return sequencia(inicio, [(base + passo * i, base + passo * i + folga, base + passo * i - folga,
                               base + passo * i) for i in range(n)])


def pos(lado="COMPRA", entrada=100000.0, candles=0, maxima=None, minima=None):
    return {"lado": lado, "entrada": entrada, "candles_decorridos": candles,
            "maxima_desde_entrada": entrada if maxima is None else maxima,
            "minima_desde_entrada": entrada if minima is None else minima,
            "resultado_flutuante_pts": 0.0}


class SaidasAbertura(unittest.TestCase):
    NOMES = ["saida_atr_fixo_claude_v1", "saida_alvo_media_claude_v1", "saida_alvo_meio_range_claude_v1",
             "saida_tendencia_trailing_claude_v1", "saida_breakeven_claude_v1"]

    def test_abertura_coerente_em_compra_e_venda(self):
        row = linha(janela_saida(), atr=200.0, MA21=100500.0)
        for nome in self.NOMES:
            m = carregar("saida", nome)
            c = m.avaliar_saida(row, pos("COMPRA"))
            v = m.avaliar_saida(row, pos("VENDA"))
            self.assertFalse(c["fechar"])
            self.assertLess(c["novo_stop"], 100000.0, nome)
            self.assertGreater(v["novo_stop"], 100000.0, nome)
            if c["novo_alvo"] is not None:
                self.assertGreater(c["novo_alvo"], 100000.0, nome)
                self.assertLess(v["novo_alvo"], 100000.0, nome)

    def test_atr_invalido_recusa_abrir(self):
        for nome in ["saida_atr_fixo_claude_v1", "saida_alvo_media_claude_v1", "saida_alvo_meio_range_claude_v1"]:
            m = carregar("saida", nome)
            with self.assertRaises(ValueError):
                m.avaliar_saida(linha(janela_saida(), atr=None), pos())

    def test_atr_fixo_niveis(self):
        m = carregar("saida", "saida_atr_fixo_claude_v1")
        r = m.avaliar_saida(linha(janela_saida(), atr=200.0), pos("COMPRA"))
        self.assertAlmostEqual(r["novo_stop"], 100000.0 - 240.0)
        self.assertAlmostEqual(r["novo_alvo"], 100000.0 + 360.0)

    def test_alvo_media_usa_ma21_quando_compensa(self):
        m = carregar("saida", "saida_alvo_media_claude_v1")
        longe = m.avaliar_saida(linha(janela_saida(), atr=200.0, MA21=101500.0), pos("COMPRA"))
        self.assertEqual(longe["novo_alvo"], 101500.0)
        perto = m.avaliar_saida(linha(janela_saida(), atr=200.0, MA21=100050.0), pos("COMPRA"))
        risco = 100000.0 - perto["novo_stop"]
        self.assertAlmostEqual(perto["novo_alvo"], 100000.0 + 1.55 * risco)
        atras = m.avaliar_saida(linha(janela_saida(), atr=200.0, MA21=99000.0), pos("COMPRA"))
        self.assertGreater(atras["novo_alvo"], 100000.0)                 # MA21 do lado errado: usa 1,55R

    def test_alvo_meio_range(self):
        m = carregar("saida", "saida_alvo_meio_range_claude_v1")
        j = sequencia(datetime(2026, 3, 4, 13, 0), [(100000, 100700, 99800, 100100)] * 12)
        r = m.avaliar_saida(linha(j, atr=200.0), pos("COMPRA", entrada=99900.0))
        self.assertAlmostEqual(r["novo_alvo"], (100700.0 + 99800.0) / 2.0)
        self.assertAlmostEqual(r["novo_stop"], 99800.0 - 50.0)


class SaidasDepoisDaAbertura(unittest.TestCase):
    def test_trailing(self):
        m = carregar("saida", "saida_tendencia_trailing_claude_v1")
        r = m.avaliar_saida(linha(janela_saida(), atr=200.0, Fechamento=100450.0),
                            pos("COMPRA", candles=3, maxima=100900.0))
        self.assertTrue(r["fechar"])
        r = m.avaliar_saida(linha(janela_saida(), atr=200.0, Fechamento=100600.0),
                            pos("COMPRA", candles=3, maxima=100900.0))
        self.assertFalse(r["fechar"])
        r = m.avaliar_saida(linha(janela_saida(), atr=200.0, Fechamento=100450.0),
                            pos("COMPRA", candles=1, maxima=100900.0))
        self.assertFalse(r["fechar"])
        v = m.avaliar_saida(linha(janela_saida(), atr=200.0, Fechamento=99550.0),
                            pos("VENDA", candles=3, minima=99100.0))
        self.assertTrue(v["fechar"])
        self.assertIsNone(m.avaliar_saida(linha(janela_saida()), pos(candles=0))["novo_alvo"])

    def test_breakeven(self):
        m = carregar("saida", "saida_breakeven_claude_v1")
        r = m.avaliar_saida(linha(janela_saida(), atr=200.0), pos("COMPRA", candles=2, maxima=100250.0))
        self.assertEqual(r["novo_stop"], 100000.0)
        r = m.avaliar_saida(linha(janela_saida(), atr=200.0), pos("COMPRA", candles=2, maxima=100150.0))
        self.assertIsNone(r["novo_stop"])
        v = m.avaliar_saida(linha(janela_saida(), atr=200.0), pos("VENDA", candles=2, minima=99750.0))
        self.assertEqual(v["novo_stop"], 100000.0)


if __name__ == "__main__":
    unittest.main()
