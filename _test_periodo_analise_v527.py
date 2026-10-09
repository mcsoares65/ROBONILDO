"""V527 - periodo da analise: pergunta no modo interativo e formato 'dia DD/MM/AAAA'.
Testes sinteticos (sem historico real). Rodar na raiz: python -m pytest _test_periodo_analise_v527.py"""
import importlib
import unittest
from datetime import date
from unittest import mock

cl = importlib.import_module("classificacao")
DIAS = [date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 4), date(2026, 4, 1), date(2026, 4, 2)]


class PeriodoTest(unittest.TestCase):
    def test_dia_unico(self):
        for texto in ("dia 03/03/2026", "Dia 2026-03-03", "dia  03/03/2026 "):
            sel, rotulo = cl.interpretar_periodo(texto, DIAS)
            self.assertEqual(sel, [date(2026, 3, 3)], texto)
            self.assertEqual(rotulo, "2026-03-03")

    def test_dia_sem_pregao_ou_invalido(self):
        for texto in ("dia 05/03/2026", "dia", "dia 03/03/2026 04/03/2026", "dia 32/13/2026", "dia abc"):
            with self.assertRaises(ValueError, msg=texto):
                cl.interpretar_periodo(texto, DIAS)

    def test_formatos_antigos_continuam(self):
        self.assertEqual(cl.interpretar_periodo("", DIAS)[1], "tudo")
        self.assertEqual(len(cl.interpretar_periodo("03/03/2026 01/04/2026", DIAS)[0]), 3)
        self.assertEqual(len(cl.interpretar_periodo("03/03/2026", DIAS)[0]), 4)      # dali ate o fim
        self.assertEqual(len(cl.interpretar_periodo("ultimos 2", DIAS)[0]), 2)
        self.assertEqual(len(cl.interpretar_periodo("mes 2026-03", DIAS)[0]), 3)

    def test_pergunta_repete_ate_entender_e_enter_vale_tudo(self):
        with mock.patch("builtins.input", side_effect=["bobagem", "dia 04/03/2026"]):
            self.assertEqual(cl._perguntar_periodo(DIAS), "dia 04/03/2026")
        with mock.patch("builtins.input", side_effect=[""]):
            self.assertEqual(cl._perguntar_periodo(DIAS), "")


if __name__ == "__main__":
    unittest.main()
