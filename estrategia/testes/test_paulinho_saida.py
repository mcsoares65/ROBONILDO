"""V466 (laboratorio, saidas): saida percentual 2R do metodo Just (Paulinho).
Arquivo `test_*`: o classificador nao o trata como candidata.
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/testes -p 'test_*.py'"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from estrategia.saida.desclassificadas.saida_paulinho_just_rr2_V01 import avaliar_saida


class SaidaPaulinho(unittest.TestCase):
    def test_saida_percentual_2r_arredondada_ao_tick_do_win(self):
        compra = avaliar_saida({}, {
            "lado": "COMPRA", "entrada": 190_035, "candles_decorridos": 0,
        })
        self.assertEqual(compra["novo_stop"], 189_650.0)
        self.assertEqual(compra["novo_alvo"], 190_800.0)


if __name__ == "__main__":
    unittest.main()
