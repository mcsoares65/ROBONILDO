"""A janela de 1.500 candles do classificacao.preparar_rows nao muda nenhum indicador:
cada linha sai igual a calculada com o historico inteiro (motor.construir_row).
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/testes -p 'test_*.py'"""
import contextlib
import io
import random
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import classificacao as cl
import motor
from motor import Candle


def serie(n_dias=58, semente=7):
    """Passeio aleatorio com 38 candles de 15 min por dia util."""
    rnd = random.Random(semente)
    candles, preco, d = [], 150000.0, datetime(2024, 1, 2)
    while len(candles) < n_dias * 38:
        if d.weekday() < 5:
            for k in range(38):
                h = d.replace(hour=9, minute=0) + timedelta(minutes=15 * k)
                o = preco
                c = o + rnd.gauss(0, 120)
                hi = max(o, c) + abs(rnd.gauss(0, 60))
                lo = min(o, c) - abs(rnd.gauss(0, 60))
                candles.append(Candle(h, o, hi, lo, c, 1000.0))
                preco = c
        d += timedelta(days=1)
    return candles


class JanelaDeIndicadores(unittest.TestCase):
    def test_linhas_iguais_ao_historico_inteiro(self):
        candles = serie()
        self.assertGreater(len(candles), cl.JANELA_INDICADORES + 300)
        with contextlib.redirect_stdout(io.StringIO()):
            rows = cl.preparar_rows(candles)
        self.assertIsNone(rows[10])
        indices = list(range(65, 80)) + list(range(len(candles) - 700, len(candles), 37)) + [len(candles) - 1]
        for i in indices:
            esperado = motor.construir_row(candles[:i + 1])
            self.assertEqual(rows[i], esperado, f"linha {i} diverge")


if __name__ == "__main__":
    unittest.main()
