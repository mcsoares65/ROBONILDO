"""Testes sintéticos; não acessam histórico de validação nem enviam ordens."""
import ast
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from motor import Candle, construir_row, wad_preco
from estrategia.entrada.entrada_divergencia_wad_v01 import gerar_sinal


class DivergenciaWadTest(unittest.TestCase):
    def candle(self, i, abertura, maxima, minima, fechamento, quantidade=None):
        return Candle(datetime(2026, 1, 1, 9) + timedelta(minutes=15 * i),
                      abertura, maxima, minima, fechamento, quantidade)

    def test_formula_sem_volume_gap_alta_baixa_e_igual(self):
        cs = [self.candle(0, 100, 102, 99, 100, 1),
              self.candle(1, 105, 108, 104, 106, 200),
              self.candle(2, 104, 105, 101, 102, 3),
              self.candle(3, 102, 103, 101, 102, 9)]
        self.assertEqual(wad_preco(cs), (0.0, 6.0, 2.0, 2.0))
        self.assertEqual(wad_preco([self.candle(i, c.abertura, c.maxima,
                                                c.minima, c.fechamento, None)
                                    for i, c in enumerate(cs)]), wad_preco(cs))
        self.assertEqual(wad_preco(cs, 3), (0.0, -4.0, -4.0))
        self.assertEqual(wad_preco([]), ())
        with self.assertRaises(ValueError):
            wad_preco(cs, 0)

    def barras(self, i, minimo=95., maximo=105., fechamento=100.):
        return {"dt": datetime(2026, 1, 1, 9) + timedelta(minutes=15 * i),
                "Abertura": 100., "Maximo": maximo, "Minimo": minimo,
                "Fechamento": fechamento}

    def test_divergencia_compra_confirmada_apenas_depois_do_setup(self):
        b = [self.barras(i) for i in range(22)]
        b[5] = self.barras(5, minimo=90.)
        b[20] = self.barras(20, minimo=89., maximo=104.)
        b[21] = self.barras(21, fechamento=106., maximo=107.)
        wad = [float(i) for i in range(22)]
        row = {"ohlc_recentes": tuple(b), "wad_preco_recentes": tuple(wad)}
        self.assertEqual(gerar_sinal(row), 1)
        self.assertEqual(gerar_sinal(row), 1)  # sem estado
        self.assertEqual(gerar_sinal({**row, "ohlc_recentes": tuple(b[:-1]),
                                      "wad_preco_recentes": tuple(wad[:-1])}), 0)
        self.assertEqual(gerar_sinal({**row, "wad_preco_recentes": tuple([0.] * 22)}), 0)
        self.assertEqual(gerar_sinal({**row, "ohlc_recentes": tuple(b[:-1])}), 0)
        self.assertEqual(gerar_sinal(row), 1)  # não altera o input

    def test_divergencia_venda_e_sem_sinal(self):
        b = [self.barras(i) for i in range(22)]
        b[5] = self.barras(5, maximo=110.)
        b[20] = self.barras(20, minimo=96., maximo=111.)
        b[21] = self.barras(21, fechamento=94., minimo=93.)
        wad = [float(-i) for i in range(22)]
        row = {"ohlc_recentes": tuple(b), "wad_preco_recentes": tuple(wad)}
        self.assertEqual(gerar_sinal(row), -1)
        self.assertEqual(gerar_sinal({**row, "wad_preco_recentes": ()}), 0)
        self.assertEqual(gerar_sinal({**row, "ohlc_recentes": ()}), 0)

    def test_row_reais_campos_alinhados_causalidade_e_compatibilidade(self):
        cs = [self.candle(i, 100. + i, 101. + i, 99. + i, 100. + i)
              for i in range(100)]
        anterior = construir_row(cs[:-1])
        atual = construir_row(cs)
        self.assertIsNotNone(anterior)
        self.assertEqual(len(atual["ohlc_recentes"]), 96)
        self.assertEqual(len(atual["wad_preco_recentes"]), 96)
        self.assertEqual(len(anterior["ohlc_recentes"]), 96)
        self.assertEqual(anterior["wad_preco_recentes"], wad_preco(cs[:-1]))
        self.assertEqual(atual["wad_preco_recentes"], wad_preco(cs))
        self.assertIsInstance(gerar_sinal(atual), int)
        self.assertIn(gerar_sinal(atual), (-1, 0, 1))
        self.assertEqual(anterior["wad_preco_recentes"], wad_preco(cs[:-1]))

    def test_cartucho_sem_import_projeto_io_ou_estado_acumulado(self):
        path = Path(__file__).parents[1] / "estrategia/entrada/entrada_divergencia_wad_v01.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)))
        calls = [n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name)]
        self.assertFalse(set(calls) & {"open", "exec", "eval", "__import__"})


if __name__ == "__main__":
    unittest.main()
