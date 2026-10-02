"""V462 - historico: escolha do CSV (historico_csv) e deteccao de candles faltando.
Cobre os achados B e C do Manus (ata 2026-10-02-Y) e o incidente de 01/10/2026."""
import sys, tempfile, unittest
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from construtor_candle import candles_faltando
from historico_csv import resolver_csv_historico, ler_csv_candles


def escreve(pasta, nome, inicio, n, passo_min, ativo="WINFUT"):
    linhas = []
    t = inicio
    for _ in range(n):
        linhas.append(f"{ativo};{t:%d/%m/%Y};{t:%H:%M:%S};100,00;110,00;90,00;105,00;1000,00;10")
        t += timedelta(minutes=passo_min)
    p = Path(pasta) / nome
    p.write_text("\n".join(reversed(linhas)), encoding="latin1")      # Profit exporta do mais novo ao mais antigo
    return p


class EscolhaDoCsv(unittest.TestCase):
    def test_pega_o_export_novo_com_outro_nome(self):          # incidente de 01/10
        d = tempfile.mkdtemp()
        escreve(d, "WINFUT_F_0_15min.csv", datetime(2026, 9, 28, 9, 0), 36, 15)
        escreve(d, "WINFUT_F_0_15min_01-01-2026_01-10-2026.csv", datetime(2026, 10, 1, 9, 0), 5, 15)
        self.assertEqual(resolver_csv_historico(str(Path(d) / "WINFUT_F_0_15min.csv"), 15).name,
                         "WINFUT_F_0_15min_01-01-2026_01-10-2026.csv")

    def test_nunca_escolhe_outro_timeframe(self):              # achado B
        d = tempfile.mkdtemp()
        escreve(d, "WINFUT_F_0_15min.csv", datetime(2026, 10, 1, 9, 0), 1, 15)
        escreve(d, "WINFUT_F_0_1min.csv", datetime(2026, 10, 1, 9, 0), 2, 1)       # 09:01, mais novo
        escreve(d, "WINFUT_F_0_5min.csv", datetime(2026, 10, 1, 9, 0), 3, 5)
        self.assertEqual(resolver_csv_historico(str(Path(d) / "WINFUT_F_0_15min.csv"), 15).name,
                         "WINFUT_F_0_15min.csv")

    def test_ignora_outro_ativo_mesmo_com_prefixo_igual(self):
        d = tempfile.mkdtemp()
        escreve(d, "WINFUT_F_0_15min.csv", datetime(2026, 10, 1, 9, 0), 1, 15)
        escreve(d, "WINFUT_x_15min.csv", datetime(2026, 10, 1, 10, 0), 4, 15, ativo="WINV26")
        self.assertEqual(resolver_csv_historico(str(Path(d) / "WINFUT_F_0_15min.csv"), 15).name,
                         "WINFUT_F_0_15min.csv")

    def test_mantem_o_configurado_se_nao_ha_mais_novo(self):
        d = tempfile.mkdtemp()
        escreve(d, "WINFUT_F_0_15min.csv", datetime(2026, 10, 1, 9, 0), 4, 15)
        escreve(d, "WINFUT_F_0_15min_antigo.csv", datetime(2026, 9, 1, 9, 0), 4, 15)
        self.assertEqual(resolver_csv_historico(str(Path(d) / "WINFUT_F_0_15min.csv"), 15).name,
                         "WINFUT_F_0_15min.csv")

    def test_leitura_ordena_e_remove_duplicata(self):
        d = tempfile.mkdtemp()
        p = escreve(d, "WINFUT_F_0_15min.csv", datetime(2026, 10, 1, 9, 0), 3, 15)
        c = ler_csv_candles(p)
        self.assertEqual([x.horario.strftime("%H:%M") for x in c], ["09:00", "09:15", "09:30"])


class CandlesFaltando(unittest.TestCase):
    F = ("2026-11-20", "2026-12-25")

    def f(self, a, b):
        return candles_faltando(a, b, 15, feriados=self.F)

    def test_incidente_28_09_ate_01_10(self):
        self.assertEqual(self.f(datetime(2026, 9, 28, 18, 15), datetime(2026, 10, 1, 10, 0)), 80)

    def test_fim_de_semana_nao_conta(self):
        self.assertEqual(self.f(datetime(2026, 9, 25, 18, 15), datetime(2026, 9, 28, 9, 0)), 0)

    def test_feriado_nao_conta(self):
        self.assertEqual(self.f(datetime(2026, 11, 19, 18, 15), datetime(2026, 11, 23, 9, 0)), 0)

    def test_mesmo_dia(self):
        self.assertEqual(self.f(datetime(2026, 10, 1, 10, 0), datetime(2026, 10, 1, 10, 15)), 0)
        self.assertEqual(self.f(datetime(2026, 10, 1, 10, 0), datetime(2026, 10, 1, 10, 45)), 2)

    def test_preenchimento_parcial_ainda_tem_buraco(self):     # achado C
        # 09:00 -> 10:00 com so o 09:15 preenchido: ainda faltam 09:30 e 09:45
        self.assertEqual(self.f(datetime(2026, 10, 1, 9, 15), datetime(2026, 10, 1, 10, 0)), 2)


if __name__ == "__main__":
    unittest.main()
