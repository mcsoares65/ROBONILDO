"""Localiza um cartucho para os testes, mesmo depois de movido para a pasta de
desclassificados (entrada/desclassificada, saida/desclassificadas).

Os testes dessas candidatas continuam valendo como documentação do que foi
descartado e de por que; o ranking, porém, não as enxerga mais."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SUBPASTAS = ("", "desclassificada", "desclassificadas")


def caminho_cartucho(pasta, nome):
    """Primeiro arquivo existente de pasta/nome.py (ou nas pastas de desclassificados)."""
    base = RAIZ / "estrategia" / pasta
    for sub in SUBPASTAS:
        candidato = base / sub / f"{nome}.py" if sub else base / f"{nome}.py"
        if candidato.exists():
            return candidato
    return None
