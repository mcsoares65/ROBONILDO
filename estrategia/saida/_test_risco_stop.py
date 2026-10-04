"""V462 - limite de risco por operacao (motor.validar_risco_inicial).
Rodar: python -m unittest discover -s estrategia/saida -p '_test_*.py'  (da raiz do projeto)
Cobre o achado A do Manus (ata 2026-10-02-Y): stop invalido/ausente nao pode liberar ordem real."""
import sys, unittest
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import configuracao as cfg
from motor import MotorRobonildo, Sinal


def sinal(lado="COMPRA", entrada=187390.0):
    return Sinal(horario=datetime(2026, 10, 1, 10, 15), lado=lado, entrada=entrada,
                 stop=None, alvo=None, distancia_ma21=0.0, motivo="")


def motor_com(saida):
    m = MotorRobonildo.__new__(MotorRobonildo)      # sem estado em disco
    m.avaliar_saida = saida
    return m


class RiscoInicial(unittest.TestCase):
    def setUp(self):
        self._salvo = (cfg.BANCA_REAL_REAIS, cfg.RISCO_MAXIMO_PCT_BANCA, cfg.RISCO_FALHA_FECHADA)
        cfg.BANCA_REAL_REAIS, cfg.RISCO_MAXIMO_PCT_BANCA, cfg.RISCO_FALHA_FECHADA = 1490.0, 0.25, True

    def tearDown(self):
        cfg.BANCA_REAL_REAIS, cfg.RISCO_MAXIMO_PCT_BANCA, cfg.RISCO_FALHA_FECHADA = self._salvo

    def ok(self, m, s=None):
        return m.validar_risco_inicial(s or sinal(), {"x": 1})[0]

    def test_stop_dentro_do_limite_libera(self):
        self.assertTrue(self.ok(motor_com(lambda r, p: {"novo_stop": 187390.0 - 1000})))

    def test_stop_acima_de_25pct_bloqueia_com_a_mensagem_do_dono(self):
        ok, msg = motor_com(lambda r, p: {"novo_stop": 187390.0 - 2000}).validar_risco_inicial(sinal(), {"x": 1})
        self.assertFalse(ok)
        self.assertIn("a banca não irá suportar o tamanho do stop loss", msg)

    def test_incidente_de_01_10(self):
        self.assertFalse(self.ok(motor_com(lambda r, p: {"novo_stop": 183855.0})))

    def test_venda_simetrica(self):
        m = motor_com(lambda r, p: {"novo_stop": 187390.0 + 2000})
        self.assertFalse(self.ok(m, sinal("VENDA")))

    def test_invalidos_bloqueiam_quando_fail_closed(self):
        casos = {
            "excecao": lambda r, p: (_ for _ in ()).throw(ValueError("x")),
            "sem_stop": lambda r, p: {"fechar": False},
            "resposta_nao_dict": lambda r, p: False,
            "stop_none": lambda r, p: {"novo_stop": None},
            "nan": lambda r, p: {"novo_stop": float("nan")},
            "inf": lambda r, p: {"novo_stop": float("inf")},
            "texto": lambda r, p: {"novo_stop": "abc"},
            "lado_errado": lambda r, p: {"novo_stop": 187390.0 + 100},
        }
        for nome, f in casos.items():
            with self.subTest(nome):
                self.assertFalse(self.ok(motor_com(f)))

    def test_fail_open_se_desligado(self):
        cfg.RISCO_FALHA_FECHADA = False
        for f in (lambda r, p: {"fechar": False}, lambda r, p: {"novo_stop": float("nan")}):
            self.assertTrue(self.ok(motor_com(f)))

    def test_sem_cartucho_ou_sem_row_nao_bloqueia(self):
        self.assertTrue(motor_com(None).validar_risco_inicial(sinal(), {"x": 1})[0])
        self.assertTrue(motor_com(lambda r, p: {}).validar_risco_inicial(sinal(), None)[0])

    def test_desligado_com_pct_zero(self):
        cfg.RISCO_MAXIMO_PCT_BANCA = 0
        self.assertTrue(self.ok(motor_com(lambda r, p: {"novo_stop": 100.0})))


if __name__ == "__main__":
    unittest.main()
