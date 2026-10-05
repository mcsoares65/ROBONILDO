"""Laboratorio (entrada composta): as portas 1-3 reproduzem a entrada titular grok_3
e a 4a (fim de tarde) so atua quando as anteriores nao sinalizam.
Arquivo `test_*`: o classificador nao o trata como candidata.
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/testes -p 'test_*.py'"""
import contextlib
import io
import importlib.util
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
import classificacao as cl
import simulador_mercado as sim
from test_periodo_simulador import historico


def carregar(sub, nome):
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "estrategia" / sub / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class ComposicaoDasPortas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.comp = carregar("entrada", "entrada_composta_grok_fim_tarde_claude_v1")
        cls.grok = carregar("entrada/titular", "entrada_grok_3_v1")
        cls.fim = carregar("entrada", "entrada_fim_tarde_rompimento_claude_v1")
        candles, _, _ = sim.gerar_candles(historico(10), 40, semente=7, modo="regimes")
        with contextlib.redirect_stdout(io.StringIO()):
            rows = cl.preparar_rows(candles)
        cls.rows = [r for r in rows if r is not None]

    def test_igual_a_grok_3_ou_fim_de_tarde_em_todas_as_linhas(self):
        self.assertGreater(len(self.rows), 500)
        for row in self.rows:
            g = self.grok.gerar_sinal(row)
            esperado = g if g else self.fim.gerar_sinal(row)
            self.assertEqual(self.comp.gerar_sinal(row), esperado)

    def test_sinal_dentro_do_dominio(self):
        for row in self.rows:
            self.assertIn(self.comp.gerar_sinal(row), (-1, 0, 1))

    def test_nao_altera_a_row(self):
        import copy
        for row in self.rows[:200]:
            antes = copy.deepcopy(row)
            self.comp.gerar_sinal(row)
            self.assertEqual(row, antes)


if __name__ == "__main__":
    unittest.main()
