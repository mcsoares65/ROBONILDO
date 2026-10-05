"""Modo D (Diagnostico de cenarios) de classificacao.py: so leitura, agrega por cenario.
Arquivo `test_*`: o classificador nao o trata como candidata.
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/entrada -p 'test_*.py'"""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import cenario
import classificacao as cl
import configuracao as cfg
import simulador_mercado as sim
from test_periodo_simulador import historico


class ModoDiagnostico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candles, cls.rotulos, _ = sim.gerar_candles(historico(8), 20, semente=3, modo="regimes")
        with contextlib.redirect_stdout(io.StringIO()):
            cls.rows = cl.preparar_rows(cls.candles)
            cls.entradas, _ = cl.descobrir_entradas()
            saidas, _ = cl.descobrir_saidas()
        cls.dias = {c.horario.date() for c in cls.candles}
        cls.et = next(e for e in cls.entradas if e.titular)
        cls.st = next(s for s in saidas if s.titular)
        cls.saidas = [s for s in saidas if cl.validar_contrato_saida(s, cls.rows)[0]]

    def test_modo_d_e_aceito_na_pergunta(self):
        with mock.patch("builtins.input", side_effect=["x", "d"]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cl._perguntar_modo_ranking(), "D")

    def test_soma_das_celulas_bate_com_as_operacoes_do_par(self):
        linhas = cl.diagnosticar_cenarios(self.candles, self.rows, self.dias, [self.et], [],
                                          self.et, self.st)
        trades = cl.executar_jogo(self.candles, self.rows, self.et, self.dias,
                                  avaliar_saida=self.st.avaliar_saida)
        self.assertGreater(len(trades), 0)
        self.assertEqual(sum(l["ops"] for l in linhas), len(trades))
        self.assertAlmostEqual(sum(l["resultado"] for l in linhas),
                               sum(t["resultado_reais"] for t in trades), places=0)
        self.assertTrue(all(l["cenario"] in cenario.NOMES for l in linhas))

    def test_distribuicao_e_acerto_do_reconhecedor(self):
        dist = cl.distribuicao_cenarios(self.rows)
        self.assertEqual(sum(dist.values()), len([r for r in self.rows if r is not None]))
        acerto = cl.acerto_geral_cenarios(cl.matriz_confusao_cenarios(self.candles, self.rows, self.rotulos))
        self.assertTrue(0.0 <= acerto <= 1.0)

    def test_execucao_do_modo_nao_grava_arquivo_e_nao_pergunta_cenario(self):
        with tempfile.TemporaryDirectory() as pasta, \
                mock.patch.object(cfg, "PASTA_LOGS_AUDITORIA", pasta):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                res = cl._executar_diagnostico(
                    self.candles, self.rows, sorted(self.dias), self.dias, self.entradas[:3],
                    self.saidas[:3], self.et, self.st, [], "_sim_teste", self.rotulos, False)
            self.assertEqual(res["modo"], "D")
            self.assertNotIn("csv", res)
            self.assertEqual(list(Path(pasta).iterdir()), [])     # nenhum arquivo gravado
            self.assertIn("Candles por cenario", buf.getvalue())
            self.assertIn("Acerto", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
