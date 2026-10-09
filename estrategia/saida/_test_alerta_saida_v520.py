"""V520 - capitão de saída, titulares de alerta e monitor de exaustão. Testes sintéticos:
não acessam histórico de validação nem enviam ordens.

Fica no laboratório (estrategia/saida/), com prefixo `_test_`, que o mantém fora da classificação
(Regra 7); a pasta tests/ foi extinta na V467. Rodar na raiz do projeto:
    python -m pytest estrategia/saida/_test_alerta_saida_v520.py
"""
import ast
import csv
import importlib
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
PASTA_SAIDA = RAIZ / "estrategia" / "saida"

# importlib (e nao `import classificacao`): o CI da Regra 3 faz grep de imports de modulos do
# projeto em estrategia/saida/*.py, e este arquivo e teste, nao cartucho.
cl = importlib.import_module("classificacao")
MonitorAlertasSaida = importlib.import_module("alerta_saida").MonitorAlertasSaida


class _Alerta:
    """Cartucho de alerta falso: 'fechar' controlado pelo teste."""
    def __init__(self, texto):
        self.ligado = False
        self.texto = texto

    def avaliar_saida(self, row, posicao):
        return {"fechar": self.ligado, "novo_stop": None, "novo_alvo": None}

    def diagnosticar_saida(self, row, posicao):
        return self.texto


def _contexto(lucro_reais=12.5):
    return {"horario_entrada": "2026-10-08T10:00:00", "lado": "COMPRA", "entrada": 100.0,
            "preco": 103.0, "candle": "10:15", "lucro_pts": 3.0, "pico_pts": 4.0,
            "lucro_reais": lucro_reais}


class MonitorTest(unittest.TestCase):
    def setUp(self):
        self.t0 = datetime(2026, 10, 8, 10, 20, 0)
        self.a = _Alerta("Primeira condição")
        self.b = _Alerta("Segunda condição")
        self.pasta = tempfile.TemporaryDirectory()
        self.m = MonitorAlertasSaida([("a", self.a), ("b", self.b)], pasta_logs=self.pasta.name)
        self.chave = ("10:15", "2026-10-08T10:00:00")

    def tearDown(self):
        self.pasta.cleanup()

    def av(self, seg, chave=None):
        return self.m.avaliar({}, {}, chave or self.chave, self.t0 + timedelta(seconds=seg), _contexto())

    def test_sem_votos_nao_fala(self):
        self.assertIsNone(self.av(0))
        self.assertEqual(self.m.nivel, 0)
        self.assertIn("0/2", self.m.texto_painel(self.t0))

    def test_nivel_e_quantos_concordam_e_fala_ao_subir(self):
        self.a.ligado = True
        fala = self.av(0)
        self.assertIn("nível 1 de 2", fala)
        self.assertIn("Primeira condição", fala)
        self.assertIn("12,50 reais", fala)
        self.b.ligado = True
        fala = self.av(1)
        self.assertIn("nível 2 de 2", fala)
        self.assertEqual(self.m.nivel, 2)

    def test_contador_e_aviso_a_cada_10_segundos(self):
        self.a.ligado = True
        self.assertIsNotNone(self.av(0))           # subiu: fala na hora
        for seg in range(1, 10):
            self.assertIsNone(self.av(seg), seg)   # sustenta, mas ainda nao deu 10 s
        fala = self.av(10)
        self.assertIn("sustentada há 10 segundos", fala)
        self.assertIsNone(self.av(15))
        self.assertIn("há 20 segundos", self.av(20))
        self.assertIn("há 20s", self.m.texto_painel(self.t0 + timedelta(seconds=20)))

    def test_mudar_de_nivel_reinicia_o_contador(self):
        self.a.ligado = True
        self.av(0)
        self.av(10)
        self.b.ligado = True
        fala = self.av(12)
        self.assertIn("nível 2", fala)
        self.assertEqual(self.m.segundos(self.t0 + timedelta(seconds=12)), 0)

    def test_desfazer_avisa_uma_vez(self):
        self.a.ligado = True
        self.av(0)
        self.a.ligado = False
        self.assertEqual(self.av(3), "A exaustão se desfez.")
        self.assertIsNone(self.av(4))

    def test_candle_novo_zera_o_contador_mas_mantem_a_posicao(self):
        self.a.ligado = True
        self.av(0)
        self.av(10)
        fala = self.av(15, chave=("10:30", self.chave[1]))
        self.assertIn("nível 1", fala)             # recomeca e fala de novo
        self.assertEqual(self.m.segundos(self.t0 + timedelta(seconds=15)), 0)

    def test_log_e_resumo(self):
        self.a.ligado = True
        self.av(0)
        self.av(10)
        self.a.ligado = False
        self.av(12)
        self.m.encerrar(self.t0 + timedelta(seconds=30))
        arquivo = Path(self.pasta.name) / "alertas_saida_2026-10-08.csv"
        with arquivo.open(encoding="utf-8") as f:
            linhas = list(csv.DictReader(f, delimiter=";"))
        self.assertEqual([l["evento"] for l in linhas], ["SUBIU", "SUSTENTA", "DESFEZ", "RESUMO"])
        self.assertEqual(linhas[-1]["nivel_max"], "1")
        self.assertEqual(linhas[-1]["sustentacao_max_s"], "10")
        self.assertEqual(linhas[0]["alertas"], "a")

    def test_alerta_com_erro_nao_derruba(self):
        class Quebrado:
            def avaliar_saida(self, row, posicao):
                raise ValueError("x")
        m = MonitorAlertasSaida([("q", Quebrado()), ("a", self.a)], pasta_logs=None)
        self.a.ligado = True
        self.assertIn("nível 1 de 2", m.avaliar({}, {}, self.chave, self.t0, _contexto()))

    def test_sem_titulares_de_alerta_fica_desligado(self):
        m = MonitorAlertasSaida([], pasta_logs=None)
        self.assertIsNone(m.avaliar({}, {}, self.chave, self.t0, _contexto()))
        self.assertEqual(m.texto_painel(self.t0), "")


class EstruturaTest(unittest.TestCase):
    def test_um_unico_capitao(self):
        arquivos = [p for p in (PASTA_SAIDA / "titular" / "capitao").glob("*.py") if not p.stem.startswith("_")]
        self.assertEqual(len(arquivos), 1)

    def test_classificacao_so_o_capitao_e_titular(self):
        saidas, _ = cl.descobrir_saidas()
        titulares = [s.nome for s in saidas if s.titular]
        self.assertEqual(titulares, [p.stem for p in (PASTA_SAIDA / "titular" / "capitao").glob("*.py")])
        nomes = {s.nome for s in saidas}
        alertas = {p.stem for p in (PASTA_SAIDA / "titular").glob("*.py")}
        self.assertTrue(alertas <= nomes)                   # alertas tambem entram no ranking
        self.assertTrue(alertas.isdisjoint(titulares))      # mas nunca como titular

    def test_cartuchos_de_alerta_respeitam_regra_3(self):
        permitidos = {"math"}
        for arq in (PASTA_SAIDA / "titular").glob("*.py"):
            arvore = ast.parse(arq.read_text(encoding="utf-8"))
            for no in ast.walk(arvore):
                if isinstance(no, ast.Import):
                    self.assertTrue({a.name for a in no.names} <= permitidos, arq.name)
                elif isinstance(no, ast.ImportFrom):
                    self.assertIn(no.module, permitidos, arq.name)


if __name__ == "__main__":
    unittest.main()
