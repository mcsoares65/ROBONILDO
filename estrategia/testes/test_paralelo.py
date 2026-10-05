"""Execucao em paralelo (V477): mesmas operacoes que a execucao em serie, par a par.
Usa cartuchos reais (estrategia/entrada e estrategia/saida) sobre uma serie sintetica.
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/testes -p 'test_*.py'"""
import contextlib
import io
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import classificacao as cl
from test_janela_indicadores import serie


class Paralelo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()):
            ents, _ = cl.descobrir_entradas()
            sais, _ = cl.descobrir_saidas()
            cls.candles = serie(n_dias=45, semente=11)
            cls.dias = {c.horario.date() for c in cls.candles}
            cls.rows = cl.preparar_rows(cls.candles, cls.dias)
        # titulares + mais algumas, para cobrir saidas com e sem alvo
        cls.pares = [(e, s) for e in ents[:3] for s in sais[:3]]

    def serie(self):
        saida = []
        for e, s in self.pares:
            try:
                saida.append(("ok", cl.executar_jogo(self.candles, self.rows, e, self.dias,
                                                     avaliar_saida=s.avaliar_saida)))
            except (KeyError, TypeError, ValueError, AttributeError) as erro:
                saida.append(("erro", f"{type(erro).__name__}: {erro}"))
        return saida

    def test_paralelo_igual_a_serie(self):
        esperado = self.serie()
        self.assertTrue(any(op for tipo, op in esperado if tipo == "ok" and op),
                        "a serie sintetica precisa gerar operacoes para o teste valer")
        obtido = cl.executar_pares_em_paralelo(self.candles, self.dias, self.pares, None, 2, progresso=False)
        self.assertEqual(obtido, esperado)

    def test_blocos_cobrem_todos_os_pregoes_sem_repetir(self):
        blocos = cl._dividir_em_blocos(self.candles, self.dias, 7)
        juntos = [d for _, dias_bloco in blocos for d in sorted(dias_bloco)]
        self.assertEqual(juntos, sorted(self.dias))
        for fatia, dias_bloco in blocos:
            self.assertTrue({c.horario.date() for c in fatia} >= dias_bloco)

    def test_processos_padrao_fica_entre_1_e_8(self):
        self.assertTrue(1 <= cl.processos_padrao() <= 8)

    def test_row_de_validacao_e_a_ultima_do_historico_completo(self):
        ultima = [r for r in self.rows if r is not None][-1]
        self.assertEqual(cl._row_de_validacao(self.candles, self.dias), [ultima])


if __name__ == "__main__":
    unittest.main()
