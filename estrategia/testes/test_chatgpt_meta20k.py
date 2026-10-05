"""Testes causais e de contrato das candidatas ChatGPT V479.

Usam somente linhas sinteticas; nao consomem o bloco de validacao nem holdout.
"""

import copy
import importlib.util
import unittest
from datetime import datetime, timedelta
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]


def carregar(subpasta, nome):
    caminho = RAIZ / "estrategia" / subpasta / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def candle(dt, abertura, maxima, minima, fechamento):
    return {"dt": dt, "Abertura": abertura, "Maximo": maxima,
            "Minimo": minima, "Fechamento": fechamento}


def base(dt, ohlc, **alteracoes):
    row = {
        "dt": dt, "Abertura": 100.0, "Maximo": 103.0,
        "Minimo": 99.0, "Fechamento": 102.5,
        "MA21": 101.0, "MA50": 99.0, "trend": 1,
        "atr": 5.0, "atr_relativo": 1.0, "rsi": 60.0,
        "macd": 3.0, "macd_signal": 2.0,
        "ohlc_recentes": tuple(ohlc),
    }
    row.update(alteracoes)
    return row


class Entradas(unittest.TestCase):
    abertura = carregar("entrada", "entrada_chatgpt_abertura_expansao_v1")
    compressao = carregar("entrada", "entrada_chatgpt_compressao_rompimento_v1")
    gap = carregar("entrada", "entrada_chatgpt_gap_continuacao_v1")

    def test_abertura_compra_e_primeiro_rompimento(self):
        dia = datetime(2026, 1, 5, 9, 0)
        faixa = [candle(dia + timedelta(minutes=15 * i), 100, 102, 99, 101) for i in range(4)]
        atual = candle(dia.replace(hour=10), 101, 104, 100.5, 103)
        row = base(atual["dt"], faixa + [atual], Abertura=101, Maximo=104,
                   Minimo=100.5, Fechamento=103, MA21=101, MA50=99,
                   atr=4, rsi=60, macd=2, macd_signal=1)
        self.assertEqual(self.abertura.gerar_sinal(row), 1)
        anterior_fora = candle(dia.replace(hour=10), 101, 104, 100, 103)
        atual2 = candle(dia.replace(hour=10, minute=15), 103, 105, 102, 104)
        row2 = base(atual2["dt"], faixa + [anterior_fora, atual2], Abertura=103,
                    Maximo=105, Minimo=102, Fechamento=104, atr=4)
        self.assertEqual(self.abertura.gerar_sinal(row2), 0)

    def test_compressao_compra(self):
        dt = datetime(2026, 1, 5, 12, 0)
        anteriores = [candle(dt - timedelta(minutes=15 * (8 - i)), 100, 102, 99, 101)
                      for i in range(8)]
        atual = candle(dt, 101, 105, 100.5, 104.5)
        row = base(dt, anteriores + [atual], Abertura=101, Maximo=105,
                   Minimo=100.5, Fechamento=104.5, atr=5)
        self.assertEqual(self.compressao.gerar_sinal(row), 1)

    def test_gap_compra_sem_preenchimento(self):
        ontem = datetime(2026, 1, 4, 18, 15)
        hoje = datetime(2026, 1, 5, 9, 0)
        anterior = candle(ontem, 98, 101, 97, 100)
        atual = [
            candle(hoje, 103, 104, 102, 103.5),
            candle(hoje + timedelta(minutes=15), 103.5, 105, 102.5, 104),
            candle(hoje + timedelta(minutes=30), 104, 108, 103, 107),
        ]
        row = base(atual[-1]["dt"], [anterior] + atual, Abertura=104,
                   Maximo=108, Minimo=103, Fechamento=107, atr=5)
        self.assertEqual(self.gap.gerar_sinal(row), 1)

    def test_entradas_nao_mutam_row_e_dominio(self):
        dt = datetime(2026, 1, 5, 14, 0)
        ohlc = [candle(dt - timedelta(minutes=15 * i), 100, 102, 99, 101)
                for i in reversed(range(12))]
        row = base(dt, ohlc)
        for modulo in (self.abertura, self.compressao, self.gap):
            antes = copy.deepcopy(row)
            self.assertIn(modulo.gerar_sinal(row), (-1, 0, 1))
            self.assertEqual(row, antes)


class Saida(unittest.TestCase):
    modulo = carregar("saida", "saida_chatgpt_tempo_sem_progresso_v1")

    def setUp(self):
        dt = datetime(2026, 1, 5, 12, 0)
        self.row = base(dt, [candle(dt - timedelta(minutes=15 * i), 100, 102, 98, 100)
                             for i in reversed(range(6))], atr=10)

    def posicao(self, lado, candles=0, resultado=0, maxima=100, minima=100):
        return {"lado": lado, "entrada": 100.0, "candles_decorridos": candles,
                "maxima_desde_entrada": maxima, "minima_desde_entrada": minima,
                "resultado_flutuante_pts": resultado}

    def test_abertura_define_stop_e_alvo_para_os_dois_lados(self):
        compra = self.modulo.avaliar_saida(self.row, self.posicao("COMPRA"))
        venda = self.modulo.avaliar_saida(self.row, self.posicao("VENDA"))
        self.assertLess(compra["novo_stop"], 100)
        self.assertGreater(compra["novo_alvo"], 100)
        self.assertGreater(venda["novo_stop"], 100)
        self.assertLess(venda["novo_alvo"], 100)

    def test_fecha_so_sem_progresso(self):
        fraca = self.posicao("COMPRA", candles=4, resultado=-2, maxima=103, minima=97)
        forte = self.posicao("COMPRA", candles=4, resultado=-2, maxima=106, minima=97)
        self.assertTrue(self.modulo.avaliar_saida(self.row, fraca)["fechar"])
        self.assertFalse(self.modulo.avaliar_saida(self.row, forte)["fechar"])


if __name__ == "__main__":
    unittest.main()
