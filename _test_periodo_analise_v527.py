"""V527/V529 - escopo da analise: UMA pergunta para ano(s) ou periodo (data / intervalo de datas).
Testes sinteticos (sem historico real). Rodar na raiz: python -m pytest _test_periodo_analise_v527.py"""
import importlib
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest import mock

cl = importlib.import_module("classificacao")
DIAS = [date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 4), date(2026, 4, 1), date(2026, 4, 2)]


class PeriodoTest(unittest.TestCase):
    def test_data_sozinha_e_so_aquele_dia(self):
        for texto in ("03/03/2026", "2026-03-03", "dia 03/03/2026", "Dia 2026-03-03", " 03/03/2026 "):
            sel, rotulo = cl.interpretar_periodo(texto, DIAS)
            self.assertEqual(sel, [date(2026, 3, 3)], texto)
            self.assertEqual(rotulo, "2026-03-03")

    def test_intervalo_com_traco_ou_espaco(self):
        for texto in ("03/03/2026-01/04/2026", "03/03/2026 01/04/2026", "03/03/2026 a 01/04/2026"):
            self.assertEqual(len(cl.interpretar_periodo(texto, DIAS)[0]), 3, texto)
        self.assertEqual(len(cl.interpretar_periodo("2026-03-03-2026-04-01", DIAS)[0]), 3)
        self.assertEqual(len(cl.interpretar_periodo("01/04/2026-03/03/2026", DIAS)[0]), 3)   # invertido

    def test_desde_e_formatos_antigos(self):
        self.assertEqual(len(cl.interpretar_periodo("desde 03/03/2026", DIAS)[0]), 4)
        self.assertEqual(cl.interpretar_periodo("", DIAS)[1], "tudo")
        self.assertEqual(len(cl.interpretar_periodo("ultimos 2", DIAS)[0]), 2)
        self.assertEqual(len(cl.interpretar_periodo("mes 2026-03", DIAS)[0]), 3)

    def test_sem_pregao_ou_invalido(self):
        for texto in ("05/03/2026", "dia 05/03/2026", "dia", "desde", "dia 03/03/2026 04/03/2026",
                      "32/13/2026", "desde 01/01/2030", "abc"):
            with self.assertRaises(ValueError, msg=texto):
                cl.interpretar_periodo(texto, DIAS)


class EscopoTest(unittest.TestCase):
    DISP = [2020, 2021, 2025, 2026]

    def test_reconhece_periodo_x_anos(self):
        for t in ("08/10/2026", "01/10/2026-08/10/2026", "2026-10-08", "dia 08/10/2026", "desde 01/10/2026", "mes 2026-03"):
            self.assertTrue(cl._escopo_eh_periodo(t), t)
        for t in ("", "2026", "2020-2026", "2023,2025", "todos", "ultimos 2"):
            self.assertFalse(cl._escopo_eh_periodo(t), t)

    def test_anos_para_periodo_inclui_ano_anterior_para_aquecimento(self):
        self.assertEqual(cl._anos_para_periodo("08/10/2026", self.DISP), [2025, 2026])
        self.assertEqual(cl._anos_para_periodo("01/10/2026-08/10/2026", self.DISP), [2025, 2026])
        self.assertEqual(cl._anos_para_periodo("05/01/2021", self.DISP), [2020, 2021])
        self.assertEqual(cl._anos_para_periodo("05/01/2020", self.DISP), [2020])          # sem ano anterior
        self.assertEqual(cl._anos_para_periodo("01/02/2020-03/04/2026", self.DISP), [2020, 2021, 2025, 2026])
        with self.assertRaises(ValueError):
            cl._anos_para_periodo("08/10/2030", self.DISP)

    def _candles(self, *dias):
        return [SimpleNamespace(horario=datetime(d.year, d.month, d.day, 10, 0)) for d in dias]

    def test_pergunta_unica_ano_data_e_repeticao_em_erro(self):
        pastas = {a: object() for a in self.DISP}
        carregados = []

        def falso(pastas_ano, anos):
            carregados.append(list(anos))
            return self._candles(date(2026, 10, 7), date(2026, 10, 8)), f"{anos[0]}–{anos[-1]}", 3

        with mock.patch.object(cl, "carregar_historico_anos", side_effect=falso):
            with mock.patch("builtins.input", side_effect=["2030", "09/10/2026", "08/10/2026"]):
                anos, candles, rotulo, n, periodo = cl._perguntar_escopo(pastas)
            self.assertEqual((anos, periodo), ([2025, 2026], "08/10/2026"))     # 2030 sem pasta; 09/10 sem pregao
            self.assertEqual(carregados[-1], [2025, 2026])
            with mock.patch("builtins.input", side_effect=["2020-2026"]):
                anos, _, _, _, periodo = cl._perguntar_escopo(pastas)
            self.assertEqual((anos, periodo), (self.DISP, ""))
            with mock.patch("builtins.input", side_effect=[""]):
                anos, _, _, _, periodo = cl._perguntar_escopo(pastas)
            self.assertEqual((anos, periodo), (self.DISP, ""))


if __name__ == "__main__":
    unittest.main()
