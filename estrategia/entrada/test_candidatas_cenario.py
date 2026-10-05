"""LABORATORIO (entradas): cada candidata dispara no setup certo, em compra e em venda
(espelho), e fica quieta fora dele. Linhas montadas a mao, sem dados reais.
Arquivo com prefixo `_`: o classificador nao o trata como candidata (Regra 7).
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/entrada -p '_test_*.py'"""
import importlib.util
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))


def carregar(pasta, nome):
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "estrategia" / pasta / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def candle(dt, o, h, l, c):
    return {"dt": dt, "Abertura": float(o), "Maximo": float(h), "Minimo": float(l), "Fechamento": float(c)}


def espelha(candles, centro=200000.0):
    """Reflete os precos em torno de `centro`: toda condicao de compra vira de venda."""
    return [candle(c["dt"], centro - c["Abertura"], centro - c["Minimo"], centro - c["Maximo"],
                   centro - c["Fechamento"]) for c in candles]


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


DIA = datetime(2026, 3, 4, 9, 0)


class EntradaAbertura(unittest.TestCase):
    m = carregar("entrada", "entrada_abertura_continuacao_claude_v1")

    def setUp(self):
        self.c = sequencia(DIA, [(100000, 100150, 99950, 100120), (100120, 100300, 100100, 100280),
                                 (100280, 100500, 100270, 100480)])

    def test_compra_e_venda(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=300.0, MA21=100000.0)), 1)
        e = espelha(self.c)
        self.assertEqual(self.m.gerar_sinal(linha(e, atr=300.0, MA21=100000.0)), -1)

    def test_quieta_fora_do_setup(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=600.0, MA21=100000.0)), 0)   # arranque < 1 ATR
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=300.0, MA21=100900.0)), 0)   # abaixo da MA21
        tarde = [dict(x, dt=x["dt"] + timedelta(minutes=15)) for x in self.c]               # 09:15..09:45
        self.assertEqual(self.m.gerar_sinal(linha(tarde, atr=300.0, MA21=100000.0)), 0)


class EntradaFimTarde(unittest.TestCase):
    m = carregar("entrada", "entrada_fim_tarde_rompimento_claude_v1")

    def setUp(self):
        base = datetime(2026, 3, 4, 14, 30)
        ohlcs = [(100000 + 10 * i, 100050 + 10 * i, 99980 + 10 * i, 100020 + 10 * i) for i in range(8)]
        ohlcs.append((100100, 100300, 100090, 100280))                     # rompe a maxima anterior
        self.c = sequencia(base, ohlcs)                                    # ultimo rotulo: 16:30

    def test_compra_e_venda(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, trend=1, MA21=100000.0, rsi=62.0)), 1)
        self.assertEqual(self.m.gerar_sinal(linha(espelha(self.c), trend=-1, MA21=100000.0, rsi=38.0)), -1)

    def test_quieta_fora_do_setup(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, trend=1, MA21=100000.0, rsi=82.0)), 0)
        self.assertEqual(self.m.gerar_sinal(linha(self.c, trend=1, MA21=100000.0, rsi=62.0, atr_relativo=1.3)), 0)
        self.assertEqual(self.m.gerar_sinal(linha(self.c, trend=-1, MA21=100000.0, rsi=62.0)), 0)
        cedo = [dict(x, dt=x["dt"] - timedelta(hours=1)) for x in self.c]
        self.assertEqual(self.m.gerar_sinal(linha(cedo, trend=1, MA21=100000.0, rsi=62.0)), 0)


class EntradaPausa(unittest.TestCase):
    m = carregar("entrada", "entrada_pausa_apos_impulso_claude_v1")

    def setUp(self):
        base = datetime(2026, 3, 4, 13, 0)
        self.c = sequencia(base, [(100000, 100400, 100000, 100400), (100390, 100380, 100250, 100330)])
        # corrige a maxima da pausa para ser coerente com o candle
        self.c[1]["Maximo"] = 100395.0

    def test_compra_e_venda(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=300.0, atr_relativo=1.4)), 1)
        self.assertEqual(self.m.gerar_sinal(linha(espelha(self.c), atr=300.0, atr_relativo=1.4)), -1)

    def test_quieta_fora_do_setup(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=300.0, atr_relativo=1.0)), 0)     # mercado calmo
        devolveu = [self.c[0], dict(self.c[1], Minimo=100100.0)]
        self.assertEqual(self.m.gerar_sinal(linha(devolveu, atr=300.0, atr_relativo=1.4)), 0)   # devolveu > 50%


class EntradaRetornoMedia(unittest.TestCase):
    m = carregar("entrada", "entrada_retorno_media_claude_v1")

    def setUp(self):
        base = datetime(2026, 3, 4, 14, 0)
        self.c = sequencia(base, [(99830, 99840, 99760, 99770), (99775, 99800, 99770, 99790)])

    def test_compra_e_venda(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=100.0, MA21=100000.0, rsi=20.0, rsi_subindo=True)), 1)
        self.assertEqual(self.m.gerar_sinal(linha(espelha(self.c), atr=100.0, MA21=100000.0, rsi=80.0,
                                                  rsi_descendo=True)), -1)

    def test_quieta_fora_do_setup(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=100.0, MA21=100000.0, rsi=40.0, rsi_subindo=True)), 0)
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=100.0, MA21=99900.0, rsi=20.0, rsi_subindo=True)), 0)
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=100.0, MA21=100000.0, rsi=20.0, rsi_subindo=False)), 0)


class EntradaPullback(unittest.TestCase):
    m = carregar("entrada", "entrada_pullback_tendencia_claude_v1")

    def setUp(self):
        base = datetime(2026, 3, 4, 12, 0)
        ohlcs = [(100000 + 100 * i, 100060 + 100 * i, 99950 + 100 * i, 100050 + 100 * i) for i in range(8)]
        ohlcs += [(100750, 100760, 100580, 100600), (100600, 100620, 100500, 100550),
                  (100550, 100620, 100520, 100580), (100580, 100720, 100570, 100700)]
        self.c = sequencia(base, ohlcs)

    def test_compra_e_venda(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, trend=1, atr=300.0)), 1)
        self.assertEqual(self.m.gerar_sinal(linha(espelha(self.c), trend=-1, atr=300.0)), -1)

    def test_quieta_fora_do_setup(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, trend=-1, atr=300.0)), 0)       # contra a tendencia
        self.assertEqual(self.m.gerar_sinal(linha(self.c, trend=1, atr=900.0)), 0)        # perna < 2 ATR
        ontem = [dict(x) for x in self.c]
        ontem[0]["dt"] = ontem[0]["dt"] - timedelta(days=1)
        self.assertEqual(self.m.gerar_sinal(linha(ontem, trend=1, atr=300.0)), 0)         # mistura de dias


class EntradaRange(unittest.TestCase):
    m = carregar("entrada", "entrada_reversao_range_claude_v1")

    def setUp(self):
        base = datetime(2026, 3, 4, 12, 0)
        ohlcs = []
        for i in range(11):
            if i % 2 == 0:
                ohlcs.append((100300, 100320, 100100, 100130))
            else:
                ohlcs.append((100130, 100700, 100120, 100680))
        ohlcs.append((100110, 100150, 100090, 100140))      # fecha perto do fundo, candle de alta
        self.c = sequencia(base, ohlcs)

    def test_compra_e_venda(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=200.0, stoch=20.0, stoch_subindo=True)), 1)
        self.assertEqual(self.m.gerar_sinal(linha(espelha(self.c), atr=200.0, stoch=80.0, stoch_descendo=True)), -1)

    def test_quieta_fora_do_setup(self):
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=200.0, stoch=60.0, stoch_subindo=True)), 0)
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=200.0, stoch=20.0, stoch_subindo=True,
                                                  atr_relativo=1.4)), 0)
        self.assertEqual(self.m.gerar_sinal(linha(self.c, atr=20.0, stoch=20.0, stoch_subindo=True)), 0)  # range largo demais


if __name__ == "__main__":
    unittest.main()
