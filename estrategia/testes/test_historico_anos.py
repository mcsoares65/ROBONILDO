"""Historico por ano (V476): listar/interpretar anos, buraco entre anos nao consecutivos e a
fusao dos CSVs das pastas de ano no classificacao.
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/testes -p 'test_*.py'"""
import contextlib
import io
import sys
import tempfile
import unittest
import unittest.mock
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import classificacao as cl
import configuracao as cfg
import historico_csv as hc


def escrever_csv(caminho: Path, dias, ativo="WINFUT", passo_min=15, preco=100000.0):
    """CSV no formato do Profit: 3 candles por dia (09:00, +passo, +2*passo)."""
    linhas = []
    for d in dias:
        for k in range(3):
            h = datetime(d.year, d.month, d.day, 9, 0) + timedelta(minutes=passo_min * k)
            o = preco + k
            linhas.append(f"{ativo};{h:%d/%m/%Y};{h:%H:%M:%S};{o:.2f};{o+5:.2f};{o-5:.2f};{o+1:.2f};1000,00;10")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(linhas) + "\n", encoding="latin1")


class ListarEInterpretar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        for ano in (2023, 2024, 2026):
            escrever_csv(self.base / str(ano) / "WINFUT_F_0_15min.csv", [date(ano, 3, 1)])
        (self.base / "backtest_antigo").mkdir()          # nome que nao e ano
        (self.base / "2025").mkdir()                     # ano sem csv
        (self.base / "WINFUT_F_0_15min.csv").write_text("x")   # arquivo solto na base

    def tearDown(self):
        self.tmp.cleanup()

    def test_listar_anos_so_pastas_de_ano_com_csv(self):
        self.assertEqual(sorted(hc.listar_anos(self.base)), [2023, 2024, 2026])

    def test_listar_anos_pasta_inexistente(self):
        self.assertEqual(hc.listar_anos(self.base / "nao_existe"), {})

    def test_interpretar_anos(self):
        d = [2023, 2024, 2026]
        self.assertEqual(hc.interpretar_anos("", d), d)
        self.assertEqual(hc.interpretar_anos("todos", d), d)
        self.assertEqual(hc.interpretar_anos("2024", d), [2024])
        self.assertEqual(hc.interpretar_anos("2023-2026", d), d)           # buraco (2025) nao e erro
        self.assertEqual(hc.interpretar_anos("2024 a 2026", d), [2024, 2026])
        self.assertEqual(hc.interpretar_anos("2026,2023", d), [2023, 2026])
        self.assertEqual(hc.interpretar_anos("ultimos 2", d), [2024, 2026])
        self.assertEqual(hc.interpretar_anos("últimos 1", d), [2026])

    def test_interpretar_anos_erros_claros(self):
        d = [2023, 2024]
        for ruim in ("2025", "2019-2020", "banana", "ultimos 0"):
            with self.subTest(ruim=ruim):
                with self.assertRaises(ValueError):
                    hc.interpretar_anos(ruim, d)


class BuracoEntreAnos(unittest.TestCase):
    def test_dias_pos_buraco(self):
        dias = [date(2023, 12, 27), date(2023, 12, 28), date(2025, 1, 2), date(2025, 1, 3),
                date(2025, 1, 6), date(2025, 1, 7)]
        self.assertEqual(hc.dias_pos_buraco(dias), {date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6)})

    def test_sem_buraco_nao_tira_nada(self):
        dias = [date(2023, 12, 28), date(2024, 1, 2), date(2024, 1, 3)]     # virada normal do ano
        self.assertEqual(hc.dias_pos_buraco(dias), set())


class FusaoDosArquivos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def carregar(self, anos):
        pastas = hc.listar_anos(self.base)
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            res = cl.carregar_historico_anos(pastas, anos)
        return res, buf.getvalue()

    def test_une_anos_em_ordem_e_conta_arquivos(self):
        escrever_csv(self.base / "2024" / "a.csv", [date(2024, 5, 2), date(2024, 5, 3)])
        escrever_csv(self.base / "2023" / "a.csv", [date(2023, 5, 2)])
        (candles, rotulo, n), _ = self.carregar([2023, 2024])
        self.assertEqual(len(candles), 9)
        self.assertEqual([c.horario for c in candles], sorted(c.horario for c in candles))
        self.assertEqual((rotulo, n), ("2023–2024", 2))

    def test_rotulo_de_anos_nao_consecutivos_lista_os_anos(self):
        escrever_csv(self.base / "2023" / "a.csv", [date(2023, 5, 2)])
        escrever_csv(self.base / "2025" / "a.csv", [date(2025, 5, 2)])
        (_, rotulo, _), _ = self.carregar([2023, 2025])
        self.assertEqual(rotulo, "2023,2025")

    def test_so_o_ano_escolhido(self):
        escrever_csv(self.base / "2023" / "a.csv", [date(2023, 5, 2)])
        escrever_csv(self.base / "2024" / "a.csv", [date(2024, 5, 2)])
        (candles, rotulo, _), _ = self.carregar([2024])
        self.assertEqual({c.horario.year for c in candles}, {2024})
        self.assertEqual(rotulo, "2024")

    def test_arquivos_parciais_na_mesma_pasta_sao_fundidos_sem_duplicar(self):
        escrever_csv(self.base / "2024" / "a_1sem.csv", [date(2024, 3, 4), date(2024, 3, 5)])
        escrever_csv(self.base / "2024" / "b_2sem.csv", [date(2024, 3, 5), date(2024, 9, 2)], preco=200000.0)
        (candles, _, n), _ = self.carregar([2024])
        self.assertEqual(len(candles), 9)                   # 3 dias distintos x 3 candles
        self.assertEqual(n, 2)
        dia5 = [c for c in candles if c.horario.date() == date(2024, 3, 5)]
        self.assertGreater(dia5[0].abertura, 150000)        # vale o ultimo arquivo (ordem de nome)

    def test_ignora_candle_de_outro_ano_e_timeframe_errado(self):
        escrever_csv(self.base / "2024" / "a.csv", [date(2024, 5, 2), date(2023, 12, 29)])
        escrever_csv(self.base / "2024" / "b_1min.csv", [date(2024, 6, 3)], passo_min=1)
        (candles, _, n), saida = self.carregar([2024])
        self.assertEqual({c.horario.date() for c in candles}, {date(2024, 5, 2)})
        self.assertEqual(n, 1)
        self.assertIn("outro ano", saida)
        self.assertIn("1 min", saida)

    def test_sem_nenhum_candle_do_ano_da_erro(self):
        escrever_csv(self.base / "2024" / "a.csv", [date(2023, 12, 29)])
        with self.assertRaises(ValueError):
            self.carregar([2024])


class ExecutarLendoPorAno(unittest.TestCase):
    """executar() com a pasta-base de anos: escolhe os anos, nao pergunta quando anos=''
    e nao grava arquivo."""

    def test_executar_usa_so_os_anos_pedidos(self):
        dias_2023 = [date(2023, 3, 1) + timedelta(days=i) for i in range(0, 40) if (date(2023, 3, 1) + timedelta(days=i)).weekday() < 5]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            escrever_csv(base / "2023" / "x.csv", dias_2023)
            escrever_csv(base / "2024" / "x.csv", [date(2024, 3, 1)])
            visto = {}
            original = cl.carregar_historico_anos

            def espiao(pastas, anos):
                visto["anos"] = list(anos)
                return original(pastas, anos)

            class Parou(Exception):
                pass

            def parar(*a, **k):
                raise Parou()

            with unittest.mock.patch.object(cfg, "PASTA_HISTORICO_BACKTEST", str(base)), \
                    unittest.mock.patch.object(cl, "carregar_historico_anos", espiao), \
                    unittest.mock.patch.object(cl, "preparar_rows", parar), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(Parou):
                    cl.executar(modo="E", anos="2023", simulacao=False, cenario="")
            self.assertEqual(visto["anos"], [2023])


if __name__ == "__main__":
    unittest.main()
