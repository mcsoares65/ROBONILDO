"""Contrato Gabriel (laboratorio, entradas e dados): dados ausentes nao viram volume ficticio; entradas stateless.
Arquivo `test_*`: o classificador nao o trata como candidata.
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/entrada -p 'test_*.py'"""
import sys
import tempfile
import unittest
import copy
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from classificacao import carregar_csv
from construtor_candle import ConstrutorCandle
from historico_csv import ler_csv_candles
from leitor_dde import LeitorDDE, COLUNAS_EXTRAS_DDE
from motor import Candle, construir_row


class CompatibilidadeGabriel(unittest.TestCase):
    def test_janelas_ohlc_e_gabriel_preservam_seus_contratos(self):
        inicio = datetime(2026, 10, 1, 9)
        candles = [Candle(inicio + timedelta(minutes=15*i), 100+i, 110+i,
                          90+i, 105+i, float(i)) for i in range(110)]
        row = construir_row(candles)
        self.assertEqual(len(row["ohlc_recentes"]), 96)
        self.assertNotIn("Quantidade", row["ohlc_recentes"][-1])
        self.assertEqual(len(row["gabriel_barras"]), 96)
        self.assertEqual(row["gabriel_barras"][-1]["Quantidade"], 109.0)
        self.assertEqual(row["gabriel_barras"][-1]["dt"], row["dt"])
        self.assertIsNone(construir_row([Candle(x.horario, x.abertura, x.maxima,
                            x.minima, x.fechamento) for x in candles])
                          ["gabriel_barras"][-1]["Quantidade"])

    def test_csv_ler_igual_na_classificacao_e_no_historico(self):
        texto = ("WINFUT;01/10/2026;09:00:00;100,00;110,00;90,00;105,00;12345,00;17\n"
                 "WINFUT;01/10/2026;09:15:00;100,00;110,00;90,00;105,00;0;\n"
                 "WINFUT;01/10/2026;09:30:00;100,00;110,00;90,00;105,00\n"
                 "WINFUT;01/10/2026;09:45:00;100,00;110,00;90,00;105,00;0;0\n")
        with tempfile.TemporaryDirectory() as pasta:
            p = Path(pasta) / "amostra.csv"
            p.write_text(texto, encoding="latin1")
            for candles in (ler_csv_candles(p), carregar_csv(p)):
                self.assertEqual([c.quantidade for c in candles], [17.0, None, None, None])

    def test_construtor_nao_fabrica_quantidade(self):
        t = datetime(2026, 10, 1, 9)
        c = ConstrutorCandle()
        self.assertIsNone(c.nova_leitura(100, t))
        self.assertIsNone(c.nova_leitura(105, t + timedelta(minutes=1)))
        self.assertIsNone(c.nova_leitura(110, t + timedelta(minutes=15)).quantidade)
        d = ConstrutorCandle()
        d.nova_leitura(100, t, 3)
        d.nova_leitura(105, t + timedelta(minutes=1), 5)
        self.assertEqual(d.nova_leitura(110, t + timedelta(minutes=15), 2).quantidade, 8)
        e = ConstrutorCandle()
        e.nova_leitura(100, t, 3)
        e.nova_leitura(105, t + timedelta(minutes=1))
        self.assertIsNone(e.nova_leitura(110, t + timedelta(minutes=15), 2).quantidade)

    def test_coluna_l_passiva(self):
        self.assertEqual(COLUNAS_EXTRAS_DDE, {"quantidade": "L"})
        enderecos = []

        class Planilha:
            def Sheets(self, nome):
                self.nome = nome
                return self

            def Range(self, celula):
                enderecos.append(celula)
                return type("Celula", (), {"Value": 1543327})()

        leitor = LeitorDDE()
        leitor._planilha = Planilha()
        leitor._linha_ativo = 7
        self.assertEqual(leitor.ler_extras(), {"quantidade": 1543327.0})
        self.assertEqual(enderecos, ["L7"])

    def test_entradas_gabriel_sao_stateless_e_nao_alteram_row(self):
        raiz = Path(__file__).resolve().parents[2]
        pasta = raiz / "estrategia" / "entrada"
        inicio = datetime(2026, 10, 1, 9)
        candles = [Candle(inicio + timedelta(minutes=15 * i), 1000 + i * 0.1,
                          1010 + i * 0.1, 990 + i * 0.1, 1001 + i * 0.1, 200)
                   for i in range(100)]
        row = construir_row(candles)
        arquivos = list(pasta.glob("entrada_gabriel_*.py"))
        if not arquivos:
            self.skipTest("nenhuma entrada Gabriel no laboratorio")
        for p in arquivos:
            with self.subTest(p=p.name):
                spec = importlib.util.spec_from_file_location(p.stem, p)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                original = copy.deepcopy(row)
                sinal = mod.gerar_sinal(row)
                self.assertIn(sinal, (-1, 0, 1))
                self.assertEqual(sinal, mod.gerar_sinal(row))
                self.assertEqual(row, original)
                sem_quantidade = copy.deepcopy(row)
                sem_quantidade["gabriel_barras"] = tuple(
                    {**c, "Quantidade": None} for c in row["gabriel_barras"]
                )
                self.assertIn(mod.gerar_sinal(sem_quantidade), (-1, 0, 1))


if __name__ == "__main__":
    unittest.main()
