"""Contrato Gabriel (laboratorio, saidas): saidas Gabriel passam no contrato S-001 nos dois lados.
Arquivo com prefixo `_`: o classificador nao o trata como candidata (Regra 7).
Rodar (da raiz do projeto): python -m unittest discover -s estrategia/saida -p '_test_*.py'"""
import sys
import unittest
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from classificacao import CartuchoSaida, validar_contrato_saida
from motor import Candle, construir_row


class SaidasGabriel(unittest.TestCase):
    def test_saidas_gabriel_passam_s001_ambos_lados(self):
        raiz = Path(__file__).resolve().parents[2]
        pasta = raiz / "estrategia" / "saida"
        inicio = datetime(2026, 10, 1, 9)
        candles = [Candle(inicio + timedelta(minutes=15 * i), 1000 + i * 0.1,
                          1010 + i * 0.1, 990 + i * 0.1, 1001 + i * 0.1, 200)
                   for i in range(100)]
        row = construir_row(candles)
        arquivos = list(pasta.glob("saida_gabriel_*.py"))
        self.assertEqual(len(arquivos), 3)
        for p in arquivos:
            with self.subTest(p=p.name):
                spec = importlib.util.spec_from_file_location(p.stem, p)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                valido, motivo = validar_contrato_saida(
                    CartuchoSaida(p.stem, p, mod.avaliar_saida, False), [row]
                )
                self.assertTrue(valido, motivo)


if __name__ == "__main__":
    unittest.main()
