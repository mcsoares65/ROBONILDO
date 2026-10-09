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
_mod_alerta = importlib.import_module("alerta_saida")
MonitorAlertasSaida = _mod_alerta.MonitorAlertasSaida
linha_posicao = _mod_alerta.linha_posicao


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
        self.m = MonitorAlertasSaida([("a", self.a), ("b", self.b)], pasta_logs=self.pasta.name, estabilidade_s=0)
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
        self.assertIsNone(fala)                    # V534: candle novo nao repete o anuncio do mesmo nivel
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
        m = MonitorAlertasSaida([("q", Quebrado()), ("a", self.a)], pasta_logs=None, estabilidade_s=0)
        self.a.ligado = True
        self.assertIn("nível 1 de 2", m.avaliar({}, {}, self.chave, self.t0, _contexto()))

    def test_sem_titulares_de_alerta_fica_desligado(self):
        m = MonitorAlertasSaida([], pasta_logs=None, estabilidade_s=0)
        self.assertIsNone(m.avaliar({}, {}, self.chave, self.t0, _contexto()))
        self.assertEqual(m.texto_painel(self.t0), "")


class _AlertaComRadar(_Alerta):
    """Alerta com radar proprio, como os cartuchos reais (diagnosticar_exaustao)."""
    def __init__(self, nome, progresso, confirmadas=1, total=2, faltante="corpo"):
        super().__init__(nome)
        self.nome, self.progresso = nome, progresso
        self.confirmadas, self.total, self.faltante = confirmadas, total, faltante

    def diagnosticar_exaustao(self, row, posicao):
        return [{"estrategia": self.nome, "curto": self.nome[:11], "prioridade": 50,
                 "sinal": 1 if self.ligado else 0, "confirmadas": self.confirmadas, "total": self.total,
                 "progresso": 1.0 if self.ligado else self.progresso,
                 "faltantes": [] if self.ligado else [self.faltante], "detalhe": self.faltante}]


class RadarTest(unittest.TestCase):
    def setUp(self):
        self.t0 = datetime(2026, 10, 8, 10, 20, 0)
        self.a = _AlertaComRadar("Alfa", 0.50)
        self.b = _AlertaComRadar("Beta", 0.40)
        self.m = MonitorAlertasSaida([("a", self.a), ("b", self.b)], pasta_logs=None, estabilidade_s=0)
        self.chave = ("10:15", "2026-10-08T10:00:00")

    def av(self, seg, chave=None):
        return self.m.avaliar({}, {}, chave or self.chave, self.t0 + timedelta(seconds=seg), _contexto())

    def test_lider_e_o_de_maior_progresso(self):
        self.av(0)
        campos = self.m.campos_painel(self.t0)
        self.assertEqual(campos["nome"], "Alfa")
        self.assertEqual(campos["pct"], 50.0)
        self.assertFalse(campos["ok"])

    def test_histerese_de_5_pontos(self):
        self.av(0)                       # Alfa na frente
        self.b.progresso = 0.54          # Beta passa por 4 pontos: Alfa segura o lugar
        self.av(1)
        self.assertEqual(self.m.campos_painel(self.t0)["nome"], "Alfa")
        self.b.progresso = 0.60          # passa por mais de 5 pontos: troca
        self.av(2)
        self.assertEqual(self.m.campos_painel(self.t0)["nome"], "Beta")

    def test_100_por_cento_so_com_alerta_confirmado(self):
        self.a.progresso = 0.995
        self.av(0)
        self.assertEqual(self.m.campos_painel(self.t0)["pct"], 99.0)
        self.a.ligado = True
        self.av(1)
        campos = self.m.campos_painel(self.t0 + timedelta(seconds=1))
        self.assertEqual((campos["pct"], campos["ok"], campos["nivel"]), (100.0, True, 1))

    def test_assume_a_prioridade_uma_vez_por_candle_a_partir_de_70(self):
        self.a.progresso = 0.60
        self.assertIsNone(self.av(0))                      # abaixo de 70%: calado
        self.a.progresso = 0.75
        fala = self.av(1)
        self.assertIn("alerta de exaustão Alfa assumiu a prioridade", fala)
        self.assertIn("1 de 2 condições", fala)
        self.assertIn("Ainda aguardamos corpo", fala)
        self.assertIsNone(self.av(2))                      # nao repete no mesmo candle
        self.assertIn("assumiu a prioridade", self.av(3, chave=("10:30", self.chave[1])))  # candle novo

    def test_linha_do_painel_cabe_em_123_colunas(self):
        campos = {"nome": "Estocástico", "confirmadas": 1, "total": 2, "detalhe": "estoc. saindo zona",
                  "pct": 60.0, "ok": False, "nivel": 0, "total_alertas": 4, "segundos": 0}
        linha = linha_posicao("12:15:06", "VENDA ", 206225, f"{6.5:+7.2f}", "Stop 208130", campos, "■", 62.0, "■")
        self.assertLessEqual(len(linha), 123)
        self.assertIn("Falta estoc. saindo zona", linha)
        self.assertTrue(linha.endswith(" 62% ■"))          # fim da linha = saude do trade
        self.assertIn("1/2 ■ | Falta", linha)               # exaustao: quadrado logo apos o n/N
        campos.update(ok=True, pct=100.0, nivel=4, segundos=120, confirmadas=2)
        linha = linha_posicao("12:15:06", "COMPRA", 206225, f"{-234.5:+7.2f}", "Stop 208130", campos, "■", 100.0, "■")
        self.assertLessEqual(len(linha), 123)
        self.assertIn("Nível 4/4 há 120s", linha)

    def test_alerta_sem_radar_proprio_vira_condicao_unica(self):
        m = MonitorAlertasSaida([("x", _Alerta("texto"))], pasta_logs=None, estabilidade_s=0)
        m.avaliar({}, {}, self.chave, self.t0, _contexto())
        campos = m.campos_painel(self.t0)
        self.assertEqual((campos["confirmadas"], campos["total"], campos["pct"]), (0, 1, 0.0))


class SaudeTradeTest(unittest.TestCase):
    """V525/V530: saude do trade abre em 0% (branco) e anda ate 100% (verde no ganho, roxo na perda)."""
    @classmethod
    def setUpClass(cls):
        cls.pr = importlib.import_module("principal")
        cls.cfg = importlib.import_module("configuracao")

    def _pos(self, lado="COMPRA", entrada=100000.0, stop=99800.0, alvo=None, hora="2026-10-09T10:00:00"):
        return importlib.import_module("types").SimpleNamespace(
            lado=lado, entrada=entrada, stop=stop, alvo=alvo, horario_entrada=hora)

    def _preco_liquido(self, pos, reais):
        """Preco em que o resultado liquido (ja com custo) vale `reais`."""
        pts = (reais + self.cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS) / self.cfg.VALOR_PONTO_REAIS
        return pos.entrada + (pts if pos.lado == "COMPRA" else -pts)

    def test_sem_alvo_abre_em_zero_1r_de_lucro_e_100_e_stop_e_100(self):
        pos = self._pos(hora="t1")
        self.pr._risco_inicial_pts(pos)                        # memoriza 1R = 200 pts
        um_r = 200 * self.cfg.VALOR_PONTO_REAIS - self.cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
        saude = lambda preco: self.pr._saude_posicao(pos, preco)[0]
        self.assertAlmostEqual(saude(self._preco_liquido(pos, 0)), 0.0, places=3)           # abre em 0%
        self.assertAlmostEqual(saude(self._preco_liquido(pos, um_r / 2)), 50.0, places=3)
        self.assertAlmostEqual(saude(self._preco_liquido(pos, um_r)), 100.0, places=3)      # ganho: 1 R
        self.assertAlmostEqual(saude(self._preco_liquido(pos, um_r * 5)), 100.0, places=3)  # trava em 100
        self.assertAlmostEqual(saude(pos.stop), 100.0, places=0)                            # perda: stop
        self.assertLess(saude(pos.entrada - 20), 20.0)                                       # perda pequena

    def test_venda_e_simetrica(self):
        pos = self._pos(lado="VENDA", stop=100200.0, hora="t2")
        self.pr._risco_inicial_pts(pos)
        um_r = 200 * self.cfg.VALOR_PONTO_REAIS - self.cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
        self.assertAlmostEqual(self.pr._saude_posicao(pos, self._preco_liquido(pos, um_r))[0], 100.0, places=3)
        self.assertAlmostEqual(self.pr._saude_posicao(pos, 100200.0)[0], 100.0, places=0)
        self.assertAlmostEqual(self.pr._saude_posicao(pos, self._preco_liquido(pos, 0))[0], 0.0, places=3)

    def test_1r_vem_do_stop_inicial_e_nao_do_stop_que_sobe(self):
        pos = self._pos(hora="t3")
        self.assertEqual(self.pr._risco_inicial_pts(pos), 200.0)
        pos.stop = 100300.0                                    # trailing ja acima da entrada
        self.assertEqual(self.pr._risco_inicial_pts(pos), 200.0)

    def test_sem_1r_medido_mantem_comportamento_antigo(self):
        pos = self._pos(stop=100300.0, hora="t4")              # stop ja do lado do lucro, nunca medido
        self.assertIsNone(self.pr._risco_inicial_pts(pos))
        self.assertEqual(self.pr._progresso_posicao(pos, 100500.0), 0.0)

    def test_com_alvo_nada_muda(self):
        pos = self._pos(alvo=100400.0, hora="t5")
        self.assertEqual(self.pr._progresso_posicao(pos, 100200.0),
                         self.pr._progresso_posicao(pos, 100200.0, 200.0))

    def test_cor_branco_no_zero_roxo_e_verde_nas_pontas(self):
        pos = self._pos(hora="t6")
        self.pr._risco_inicial_pts(pos)
        if not self.pr.COR_RESET:
            self.skipTest("sem cor")
        um_r = 200 * self.cfg.VALOR_PONTO_REAIS - self.cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
        self.assertIn("255;255;255", self.pr._saude_posicao(pos, self._preco_liquido(pos, 0))[1])
        self.assertIn("163;255;30", self.pr._saude_posicao(pos, self._preco_liquido(pos, um_r))[1])
        self.assertIn("147;51;234", self.pr._saude_posicao(pos, 99800.0)[1])


class TrailingVisivelTest(unittest.TestCase):
    """V531: o trailing avisa quando ARMA (ganho maximo chegou a 1 R, stop ainda e o inicial) e quando ASSUME."""
    @classmethod
    def setUpClass(cls):
        cls.pr = importlib.import_module("principal")

    def _pos(self, hora, lado="COMPRA", entrada=207050.0, stop=205780.0, maxima=0.0, minima=0.0):
        return importlib.import_module("types").SimpleNamespace(
            lado=lado, entrada=entrada, stop=stop, alvo=None, horario_entrada=hora,
            maxima_desde_entrada=maxima, minima_desde_entrada=minima)

    def test_sem_aviso_antes_de_1r(self):
        pos = self._pos("v1", maxima=208165.0)
        self.pr._risco_inicial_pts(pos)                       # 1 R = 1270 pts
        self.assertIsNone(self.pr._frase_trailing(pos, 208165.0))
        self.assertFalse(self.pr._estado_trailing(pos, 208165.0)["armado"])

    def test_arma_uma_vez_e_depois_assume_uma_vez(self):
        pos = self._pos("v2", maxima=208330.0)
        self.pr._risco_inicial_pts(pos)
        hora = datetime(2026, 10, 8, 14, 15)
        fala = self.pr._frase_trailing(pos, 208330.0, hora)
        self.assertIn("100%", fala)
        self.assertIn("14:15", fala)
        self.assertIsNone(self.pr._frase_trailing(pos, 208340.0, hora))      # nao repete
        pos.stop = 208330.0 - 0.4 * 1270                                      # candle fechou: stop subiu
        fala = self.pr._frase_trailing(pos, 208340.0, hora)
        self.assertIn("O trailing assumiu", fala)
        self.assertIn("protegendo", fala)
        self.assertIsNone(self.pr._frase_trailing(pos, 208500.0, hora))      # nao repete
        self.assertTrue(self.pr._estado_trailing(pos, 208500.0)["assumiu"])

    def test_assumiu_sem_ter_avisado_o_armado_nao_fala_dos_dois(self):
        pos = self._pos("v3", maxima=208400.0)
        self.pr._risco_inicial_pts(pos)
        pos.stop = 207900.0
        self.assertIn("O trailing assumiu", self.pr._frase_trailing(pos, 208400.0))
        self.assertIsNone(self.pr._frase_trailing(pos, 208400.0))

    def test_venda_simetrica(self):
        pos = self._pos("v4", lado="VENDA", entrada=207050.0, stop=208320.0, minima=205700.0)
        self.pr._risco_inicial_pts(pos)
        self.assertIn("100%", self.pr._frase_trailing(pos, 205700.0))
        pos.stop = 205700.0 + 0.4 * 1270
        self.assertIn("O trailing assumiu", self.pr._frase_trailing(pos, 205700.0))

    def test_com_alvo_ou_sem_1r_medido_fica_calado(self):
        pos = self._pos("v5", maxima=209000.0)
        pos.alvo = 210000.0
        self.pr._risco_inicial_pts(pos)
        self.assertIsNone(self.pr._frase_trailing(pos, 209000.0))
        recuperada = self._pos("v6", stop=207900.0, maxima=209000.0)          # stop ja acima da entrada, nunca medido
        self.assertIsNone(self.pr._frase_trailing(recuperada, 209000.0))


class FraseEscalaTest(unittest.TestCase):
    """V535: a frase da Escala so cita 'Próxima condição' quando falta mesmo alguma."""
    def test_sem_condicao_faltando_nao_fala_proxima(self):
        esc = importlib.import_module("escalacao")
        time = esc.Escalacao([esc.Membro("x", gerar_sinal=lambda row: 1)])
        texto = time.diagnosticar_sinal({})["explicacao"]
        self.assertIn("1 de 1 confirmações.", texto)
        self.assertNotIn("Próxima condição", texto)
        self.assertNotIn("nenhuma", texto)

    def test_com_condicao_faltando_continua_citando(self):
        esc = importlib.import_module("escalacao")
        time = esc.Escalacao([esc.Membro("x", gerar_sinal=lambda row: 0)])
        self.assertIn("Próxima condição: condições da estratégia.", time.diagnosticar_sinal({})["explicacao"])


class DebounceVozTest(unittest.TestCase):
    """V534: a voz so anuncia mudanca de nivel que ficou estavel; o log continua registrando tudo."""
    def setUp(self):
        self.t0 = datetime(2026, 10, 8, 10, 20, 0)
        self.a = _Alerta("Primeira condição")
        self.pasta = tempfile.TemporaryDirectory()
        self.m = MonitorAlertasSaida([("a", self.a)], pasta_logs=self.pasta.name, intervalo_s=60, estabilidade_s=15)
        self.chave = ("10:15", "2026-10-08T10:00:00")

    def tearDown(self):
        self.pasta.cleanup()

    def av(self, seg, chave=None):
        return self.m.avaliar({}, {}, chave or self.chave, self.t0 + timedelta(seconds=seg), _contexto())

    def test_oscilacao_curta_fica_muda(self):
        self.a.ligado = True
        self.assertIsNone(self.av(0))
        self.a.ligado = False
        self.assertIsNone(self.av(4))              # sumiu em 4 s: nada foi dito, nada a desfazer
        self.a.ligado = True
        self.assertIsNone(self.av(8))
        self.a.ligado = False
        self.assertIsNone(self.av(12))
        for seg in range(13, 40):
            self.assertIsNone(self.av(seg), seg)

    def test_nivel_estavel_e_anunciado_uma_vez_e_depois_desfaz(self):
        self.a.ligado = True
        self.assertIsNone(self.av(0))
        self.assertIsNone(self.av(14))
        self.assertIn("nível 1", self.av(15))      # estavel por 15 s: fala
        self.assertIsNone(self.av(20))
        self.a.ligado = False
        self.assertIsNone(self.av(25))             # sumiu ha 0 s
        self.assertEqual(self.av(40), "A exaustão se desfez.")
        self.assertIsNone(self.av(41))

    def test_sustentada_so_a_cada_60_segundos(self):
        self.a.ligado = True
        self.av(0)
        self.assertIsNotNone(self.av(15))
        for seg in range(16, 75):
            self.assertIsNone(self.av(seg), seg)
        self.assertIn("sustentada", self.av(75))

    def test_log_registra_cada_mudanca_mesmo_sem_voz(self):
        self.a.ligado = True
        self.av(0)
        self.a.ligado = False
        self.av(4)
        arquivo = Path(self.pasta.name) / "alertas_saida_2026-10-08.csv"
        with arquivo.open(encoding="utf-8") as f:
            eventos = [l["evento"] for l in csv.DictReader(f, delimiter=";")]
        self.assertEqual(eventos, ["SUBIU", "DESFEZ"])


class CalmaTest(unittest.TestCase):
    """V532: frase de serenidade so quando os fatos sustentam o plano; limitada no tempo; calada na exaustao."""
    @classmethod
    def setUpClass(cls):
        cls.pr = importlib.import_module("principal")

    def _pos(self, hora, stop=205780.0):
        return importlib.import_module("types").SimpleNamespace(
            lado="COMPRA", entrada=207050.0, stop=stop, alvo=None, horario_entrada=hora,
            maxima_desde_entrada=0.0, minima_desde_entrada=0.0)

    def setUp(self):
        self.t0 = datetime(2026, 10, 8, 14, 20, 0)

    def test_recuo_no_lucro_com_stop_longe_fala_calma_sem_prometer(self):
        pos = self._pos("c1")
        self.pr._risco_inicial_pts(pos)
        self.assertIsNone(self.pr._frase_calma(pos, 208250.0, self.t0))          # no pico: nada a dizer
        fala = self.pr._frase_calma(pos, 207950.0, self.t0 + timedelta(seconds=5))   # recuou 300 pts, segue no lucro
        self.assertIsNotNone(fala)
        self.assertLessEqual(len(fala), 60)                                       # V533: frase curta e basica
        self.assertFalse(any(ch.isdigit() for ch in fala))
        for proibida in ("garant", "certeza", "vai subir", "jogo", "jogador", "porta", "em campo"):
            self.assertNotIn(proibida, fala.lower())

    def test_limita_a_uma_frase_por_intervalo_e_varia_o_texto(self):
        pos = self._pos("c2")
        self.pr._risco_inicial_pts(pos)
        self.pr._frase_calma(pos, 208250.0, self.t0)
        f1 = self.pr._frase_calma(pos, 207950.0, self.t0 + timedelta(seconds=5))
        self.assertIsNone(self.pr._frase_calma(pos, 207940.0, self.t0 + timedelta(seconds=30)))   # < 120 s
        f2 = self.pr._frase_calma(pos, 207940.0, self.t0 + timedelta(seconds=130))
        self.assertIsNotNone(f2)
        self.assertNotEqual(f1, f2)

    def test_calada_com_exaustao_confirmada_por_dois_alertas(self):
        pos = self._pos("c3")
        self.pr._risco_inicial_pts(pos)
        self.pr._frase_calma(pos, 208250.0, self.t0)
        self.assertIsNone(self.pr._frase_calma(pos, 207950.0, self.t0 + timedelta(seconds=5), nivel_exaustao=2))
        self.assertIsNotNone(self.pr._frase_calma(pos, 207950.0, self.t0 + timedelta(seconds=6), nivel_exaustao=1))

    def test_calada_quando_ha_pouco_pico_ou_stop_colado(self):
        pos = self._pos("c4")
        self.pr._risco_inicial_pts(pos)
        self.pr._frase_calma(pos, 207150.0, self.t0)                              # pico de so ~8%
        self.assertIsNone(self.pr._frase_calma(pos, 207070.0, self.t0 + timedelta(seconds=5)))
        colado = self._pos("c5", stop=207800.0)                                    # stop a 100 pts do preco (< 0,25 R)
        colado.entrada = 207050.0
        self.pr._RISCO_INICIAL_PTS["c5"] = 1270.0
        self.pr._frase_calma(colado, 208300.0, self.t0)
        self.assertIsNone(self.pr._frase_calma(colado, 207900.0, self.t0 + timedelta(seconds=5)))

    def test_perda_pequena_dentro_do_stop_diz_o_risco_ja_definido(self):
        pos = self._pos("c6")
        self.pr._risco_inicial_pts(pos)
        self.pr._frase_calma(pos, 207050.0, self.t0)
        fala = self.pr._frase_calma(pos, 206800.0, self.t0 + timedelta(seconds=5))        # -250 pts, longe do stop
        self.assertIsNotNone(fala)
        self.assertTrue("risco" in fala.lower())
        self.assertIsNone(self.pr._frase_calma(pos, 205900.0, self.t0 + timedelta(seconds=300)))  # perto do stop: cala

    def test_com_stop_acima_da_entrada_cita_o_lucro_garantido(self):
        pos = self._pos("c7")
        self.pr._risco_inicial_pts(pos)
        self.pr._frase_calma(pos, 209000.0, self.t0)
        pos.stop = 208100.0                                                       # trailing ja assumiu
        achadas = []
        for i in range(4):
            achadas.append(self.pr._frase_calma(pos, 208600.0, self.t0 + timedelta(seconds=130 * (i + 1))))
        self.assertTrue(any(a and "protegido" in a for a in achadas))

    def test_com_alvo_ou_sem_1r_medido_fica_calada(self):
        pos = self._pos("c8")
        pos.alvo = 210000.0
        self.pr._risco_inicial_pts(pos)
        self.assertIsNone(self.pr._frase_calma(pos, 208250.0, self.t0))
        sem = self._pos("c9", stop=207900.0)
        self.assertIsNone(self.pr._frase_calma(sem, 208250.0, self.t0))


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

    def test_radar_dos_cartuchos_reais_concorda_com_o_sinal(self):
        import importlib.util
        ohlc = tuple({"dt": i, "Abertura": 100, "Maximo": 101, "Minimo": 99, "Fechamento": 100}
                     for i in range(96))
        pos = {"lado": "VENDA", "entrada": 100.0, "candles_decorridos": 2,
               "maxima_desde_entrada": 101.0, "minima_desde_entrada": 92.0}
        casos = [
            {"Fechamento": 96, "Abertura": 95.8, "Maximo": 96.2, "Minimo": 95, "atr": 2, "MA21": 100,
             "stoch": 30, "stoch_prev": 18, "macd": -3, "macd_signal": -1, "macd_prev": -4,
             "macd_signal_prev": -1},                                   # varios sinais
            {"Fechamento": 99.5, "Abertura": 99.4, "Maximo": 99.8, "Minimo": 99.0, "atr": 2, "MA21": 100,
             "stoch": 50, "stoch_prev": 50, "macd": -1, "macd_signal": -3, "macd_prev": -1,
             "macd_signal_prev": -1},                                   # lucro pequeno: nenhum sinal
        ]
        for arq in sorted((PASTA_SAIDA / "titular").glob("saida_exaustao_*.py")):
            spec = importlib.util.spec_from_file_location(arq.stem, arq)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for caso in casos:
                row = {**caso, "ohlc_recentes": ohlc}
                item = mod.diagnosticar_exaustao(row, pos)[0]
                self.assertEqual(bool(item["sinal"]), bool(mod.avaliar_saida(row, pos)["fechar"]), arq.stem)
                self.assertTrue(0.0 <= item["progresso"] <= 1.0)
                self.assertEqual(item["progresso"] >= 1.0, bool(item["sinal"]), arq.stem)
                self.assertLessEqual(len(item["detalhe"]), 20, arq.stem)   # cabe na coluna do painel
                self.assertTrue(item["curto"])

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
