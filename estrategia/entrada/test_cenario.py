"""cenario.py: reconhecimento exclusivo e 'tecnico' com confirmacao.
Rodar: python -m unittest discover -s estrategia/entrada -p 'test_*.py'  (da raiz do projeto)"""
import sys, unittest
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import cenario


def row(hora=(11, 0), fech=100000.0, ma21=100000.0, atr=200.0, atr_rel=1.0, fechamentos=None):
    """fechamentos: 12 fechamentos recentes. Padrao = vai e volta (eficiencia ~0,09)."""
    if fechamentos is None:
        fechamentos = [100000.0 + (50.0 if i % 2 else -50.0) for i in range(12)]
        fechamentos[-1] = 100000.0 + 50.0
    janela = tuple({"dt": None, "Abertura": f, "Maximo": f, "Minimo": f, "Fechamento": f} for f in fechamentos)
    return {"dt": datetime(2026, 3, 2, hora[0], hora[1]), "Fechamento": fech, "MA21": ma21,
            "atr": atr, "atr_relativo": atr_rel, "ohlc_recentes": janela}


LINHA_RETA = [100000.0 + 40.0 * i for i in range(12)]          # eficiencia 1,0
MEIO_TERMO = [100000.0, 100100.0, 100000.0, 100100.0, 100000.0, 100100.0,
              100000.0, 100100.0, 100200.0, 100100.0, 100200.0, 100300.0]


class Reconhecimento(unittest.TestCase):
    def test_cada_cenario(self):
        casos = {
            "abertura": row(hora=(9, 15)),
            "fim_de_tarde": row(hora=(16, 30)),
            "volatil": row(atr_rel=1.25),
            "esticado": row(fech=100400.0),
            "tendencia": row(fechamentos=LINHA_RETA),
            "lateral": row(),
        }
        for esperado, r in casos.items():
            self.assertEqual(cenario.classificar(r), esperado, esperado)

    def test_zona_cinzenta_e_indefinida(self):
        c = cenario.caracteristicas(row(fechamentos=MEIO_TERMO))
        self.assertTrue(cenario.EFICIENCIA_LATERAL < c["eficiencia"] < cenario.EFICIENCIA_TENDENCIA)
        self.assertEqual(cenario.classificar(row(fechamentos=MEIO_TERMO)), cenario.INDEFINIDO)

    def test_prioridade(self):
        # abertura vence volatil; volatil vence esticado; esticado vence tendencia
        self.assertEqual(cenario.classificar(row(hora=(9, 0), atr_rel=2.0)), "abertura")
        self.assertEqual(cenario.classificar(row(atr_rel=2.0, fech=100900.0)), "volatil")
        self.assertEqual(cenario.classificar(row(fech=100400.0, fechamentos=LINHA_RETA)), "esticado")

    def test_limites_exatos(self):
        self.assertEqual(cenario.classificar(row(hora=(9, 30))), "abertura")
        self.assertNotEqual(cenario.classificar(row(hora=(9, 45))), "abertura")
        self.assertEqual(cenario.classificar(row(hora=(16, 15))), "lateral")
        self.assertEqual(cenario.classificar(row(hora=(16, 30))), "fim_de_tarde")

    def test_sem_dados(self):
        self.assertEqual(cenario.classificar(None), cenario.INDEFINIDO)
        r = row(); r["atr"] = None
        self.assertEqual(cenario.classificar(r), cenario.INDEFINIDO)
        r = row(); r["atr"] = 0
        self.assertEqual(cenario.classificar(r), cenario.INDEFINIDO)
        r = row(); r["ohlc_recentes"] = r["ohlc_recentes"][:5]
        self.assertEqual(cenario.classificar(r), cenario.INDEFINIDO)

    def test_simetria_alta_baixa(self):
        self.assertEqual(cenario.classificar(row(fechamentos=LINHA_RETA[::-1])), "tendencia")
        self.assertEqual(cenario.classificar(row(fech=99600.0)), "esticado")
        self.assertEqual(cenario.caracteristicas(row(fechamentos=LINHA_RETA))["direcao"], 1)
        self.assertEqual(cenario.caracteristicas(row(fechamentos=LINHA_RETA[::-1]))["direcao"], -1)

    def test_nomes_unicos(self):
        self.assertEqual(len(set(cenario.NOMES)), len(cenario.NOMES))


class Tecnico(unittest.TestCase):
    def test_so_troca_apos_confirmacao(self):
        t = cenario.Acompanhante(confirmacoes=2)
        lat, vol = row(), row(atr_rel=1.5)
        self.assertEqual(t.atualizar(lat), ("indefinido", False))
        self.assertEqual(t.atualizar(lat), ("lateral", True))
        self.assertEqual(t.atualizar(vol), ("lateral", False))      # 1 candle nao basta
        self.assertEqual(t.atualizar(lat), ("lateral", False))      # voltou: zera
        self.assertEqual(t.atualizar(vol), ("lateral", False))
        self.assertEqual(t.atualizar(vol), ("volatil", True))

    def test_novo_pregao_zera(self):
        t = cenario.Acompanhante(confirmacoes=1)
        t.atualizar(row())
        self.assertEqual(t.atual, "lateral")
        t.novo_pregao()
        self.assertEqual(t.atual, cenario.INDEFINIDO)

    def test_confirmacoes_invalidas(self):
        with self.assertRaises(ValueError):
            cenario.Acompanhante(0)


if __name__ == "__main__":
    unittest.main()


class Consistencia(unittest.TestCase):
    def test_so_conta_mesmo_sentido_e_ops_minimas(self):
        import diagnostico_cenarios as dg
        def l(tipo, nome, cen, ops, res):
            return {"tipo": tipo, "estrategia": nome, "cenario": cen, "ops": ops, "resultado": res, "vitorias": 0}
        a = [l("saida", "T", "x", 20, 100), l("saida", "A", "x", 20, 300), l("saida", "B", "x", 20, 50),
             l("saida", "C", "x", 5, 900), l("saida", "T", "y", 20, 100), l("saida", "A", "y", 20, 400)]
        b = [l("saida", "T", "x", 20, 100), l("saida", "A", "x", 20, 250), l("saida", "B", "x", 20, 200),
             l("saida", "C", "x", 20, 900), l("saida", "T", "y", 20, 100), l("saida", "A", "y", 20, 0)]
        r = dg.consistencia(a, b, "E", "T")
        nomes = {(x["estrategia"], x["cenario"]): x["efeito_minimo"] for x in r}
        self.assertEqual(nomes, {("A", "x"): 150.0})   # B muda de sinal; C tem poucas ops; A em y muda de sinal


class NomesCurtos(unittest.TestCase):
    def test_remove_prefixo_e_ia_so_quando_sobra_descricao(self):
        import diagnostico_cenarios as dg
        r = dg.nomes_curtos(["entrada_macd_estocastico_claude_v1", "saida_alvo_tendencia_forte_claude_v1",
                             "entrada_grok_3_v1", "entrada_claude_v1", "saida_baseline",
                             "saida_grok_reverso_v3", "entrada_deepseek_V06"])
        self.assertEqual(r["entrada_macd_estocastico_claude_v1"], "macd_estocastico_v1")
        self.assertEqual(r["saida_alvo_tendencia_forte_claude_v1"], "alvo_tendencia_forte_v1")
        self.assertEqual(r["entrada_grok_3_v1"], "grok_3_v1")      # sem descricao: a IA e o nome
        self.assertEqual(r["entrada_claude_v1"], "claude_v1")
        self.assertEqual(r["saida_baseline"], "baseline")
        self.assertEqual(r["saida_grok_reverso_v3"], "reverso_v3")
        self.assertEqual(r["entrada_deepseek_V06"], "deepseek_V06")

    def test_colisao_volta_ao_nome_sem_prefixo(self):
        import diagnostico_cenarios as dg
        r = dg.nomes_curtos(["saida_giveback_claude_v1", "saida_giveback_manus_v1"])
        self.assertEqual(r["saida_giveback_claude_v1"], "giveback_claude_v1")
        self.assertEqual(r["saida_giveback_manus_v1"], "giveback_manus_v1")
