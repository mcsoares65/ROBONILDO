"""Periodo livre (classificacao.interpretar_periodo) e simulador de mercado.
Rodar: python -m unittest discover -s tests -v   (da raiz do projeto)"""
import sys, unittest
from datetime import date, datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import classificacao as cl
import simulador_mercado as sim
from motor import Candle


def historico(n_dias=12, inicio=date(2026, 1, 5)):
    candles, d, preco = [], inicio, 100000.0
    while len([1 for _ in {c.horario.date() for c in candles}]) < n_dias:
        if d.weekday() < 5:
            for i in range(38):
                h = datetime(d.year, d.month, d.day, 9, 0) + timedelta(minutes=15 * i)
                o = preco
                f = o + (40 if i % 3 else -35)
                candles.append(Candle(h, o, max(o, f) + 25, min(o, f) - 25, f))
                preco = f
        d += timedelta(days=1)
    return candles


DIAS = [date(2026, 2, 27), date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 31),
        date(2026, 4, 1), date(2026, 4, 2)]


class Periodo(unittest.TestCase):
    def test_tudo_e_vazio(self):
        for txt in (None, "", "tudo"):
            sel, rot = cl.interpretar_periodo(txt, DIAS)
            self.assertEqual(sel, DIAS)
            self.assertEqual(rot, "tudo")

    def test_ultimos(self):
        sel, _ = cl.interpretar_periodo("ultimos 2", DIAS)
        self.assertEqual(sel, DIAS[-2:])
        sel, _ = cl.interpretar_periodo("últimos 99", DIAS)
        self.assertEqual(sel, DIAS)

    def test_mes(self):
        for txt in ("mes 2026-03", "2026-03", "mes 03/2026"):
            sel, rot = cl.interpretar_periodo(txt, DIAS)
            self.assertEqual(sel, DIAS[1:4])
            self.assertEqual(rot, "2026-03")

    def test_intervalo_e_data_unica(self):
        sel, _ = cl.interpretar_periodo("02/03/2026 01/04/2026", DIAS)
        self.assertEqual(sel, DIAS[1:5])
        sel, _ = cl.interpretar_periodo("2026-03-31:2026-04-02", DIAS)
        self.assertEqual(sel, DIAS[3:])
        sel, _ = cl.interpretar_periodo("01/04/2026", DIAS)
        self.assertEqual(sel, DIAS[4:])
        sel, _ = cl.interpretar_periodo("01/04/2026 02/03/2026", DIAS)   # invertido
        self.assertEqual(sel, DIAS[1:5])

    def test_invalidos(self):
        for txt in ("xpto", "31/02/2026", "mes 2025-01", "ultimos 0", "01/01/2020 02/01/2020"):
            with self.assertRaises(ValueError, msg=txt):
                cl.interpretar_periodo(txt, DIAS)


class Simulador(unittest.TestCase):
    def setUp(self):
        self.real = historico()

    def test_deterministico_e_semente_muda_resultado(self):
        for modo in sim.MODOS:
            a, _, _ = sim.gerar_candles(self.real, 10, semente=5, modo=modo)
            b, _, _ = sim.gerar_candles(self.real, 10, semente=5, modo=modo)
            c, _, _ = sim.gerar_candles(self.real, 10, semente=6, modo=modo)
            self.assertEqual(a, b)
            self.assertNotEqual(a, c)

    def test_candles_validos(self):
        for modo in sim.MODOS:
            cs, rot, _ = sim.gerar_candles(self.real, 15, semente=1, modo=modo)
            self.assertEqual(len(cs), 15 * 38)
            self.assertEqual(len(rot), len(cs))
            for c in cs:
                self.assertGreaterEqual(c.maxima, max(c.abertura, c.fechamento))
                self.assertLessEqual(c.minima, min(c.abertura, c.fechamento))
                self.assertTrue(all(v % 5 == 0 for v in (c.abertura, c.maxima, c.minima, c.fechamento)))
            self.assertGreaterEqual(cs[0].horario.date(), sim.DATA_INICIAL_PADRAO)

    def test_csv_ida_e_volta(self):
        import tempfile
        cs, _, _ = sim.gerar_candles(self.real, 6, semente=3)
        with tempfile.TemporaryDirectory() as pasta:
            p = sim.salvar_csv(cs, Path(pasta) / "s.csv")
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                lido = cl.carregar_csv(p)
        self.assertEqual(lido, cs)

    def test_entradas_invalidas(self):
        with self.assertRaises(ValueError):
            sim.gerar_candles(self.real, 10, modo="xpto")
        with self.assertRaises(ValueError):
            sim.gerar_candles(self.real, 1)
        with self.assertRaises(ValueError):
            sim.gerar_candles(historico(3), 10)


if __name__ == "__main__":
    unittest.main()


class FiltroPorCenario(unittest.TestCase):
    """classificacao.executar_jogo(cenario=...) so deixa a entrada disparar naquele cenario."""

    def test_entrada_so_dispara_no_cenario(self):
        import cenario
        import contextlib, io
        candles, _, _ = sim.gerar_candles(historico(8), 12, semente=4, modo="regimes")
        with contextlib.redirect_stdout(io.StringIO()):
            rows = cl.preparar_rows(candles)
            saidas, _ = cl.descobrir_saidas()
        saida = next(s for s in saidas if s.titular)
        dias = {c.horario.date() for c in candles}
        por_hora = {c.horario: r for c, r in zip(candles, rows)}
        sempre_compra = cl.CartuchoEntrada("fake", Path("fake.py"), lambda row: 1)
        for alvo in ("abertura", "fim_de_tarde", "lateral"):
            trades = cl.executar_jogo(candles, rows, sempre_compra, dias,
                                      avaliar_saida=saida.avaliar_saida, cenario=alvo)
            for t in trades:
                self.assertEqual(cenario.classificar(por_hora[t["horario_rotulo"]]), alvo)
        livre = cl.executar_jogo(candles, rows, sempre_compra, dias, avaliar_saida=saida.avaliar_saida)
        self.assertGreater(len(livre), 0)
