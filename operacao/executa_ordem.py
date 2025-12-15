"""
Envio de ordens via atalhos de teclado no ProfitPro.

Mapeamento de ações:
- COMPRAR  -> ALT + C
- VENDER   -> ALT + V
- ENCERRAR -> ALT + Z

O envio só é realizado quando ENVIAR_ORDENS=True para evitar execuções acidentais.
"""

from time import sleep
from typing import Tuple

from config import ENVIAR_ORDENS, NOME_TELA_PROFIT
from visao.foco_profit import FocoProfit


def _atalho_por_acao(acao_final: str) -> str | None:
    acao = (acao_final or "").upper()
    if acao == "COMPRAR":
        return "c"
    if acao == "VENDER":
        return "v"
    if acao == "ENCERRAR":
        return "z"
    return None


def executar_ordem(acao_final: str) -> Tuple[bool, str]:
    """
    Envia a ordem para o Profit via atalho se estiver habilitado.

    Retorna (sucesso, mensagem).
    """
    tecla = _atalho_por_acao(acao_final)
    if tecla is None:
        return False, f"Ação não executável: {acao_final}"

    if not ENVIAR_ORDENS:
        return False, "Envio de ordens desabilitado (ENVIAR_ORDENS=False)"

    try:
        import pyautogui
    except Exception as e:  # pragma: no cover - ambiente pode não ter pyautogui
        return False, f"pyautogui indisponível: {e}"

    foco = FocoProfit(NOME_TELA_PROFIT)
    hwnd = foco.focar()
    if not hwnd:
        return False, "Janela do Profit não encontrada"

    if not foco.esta_em_foco(hwnd_esperado=hwnd):
        return False, "Profit não ficou em foco para enviar a ordem"

    try:
        pyautogui.hotkey("alt", tecla)
        sleep(0.2)  # evita disparos duplos involuntários
        return True, f"Ordem enviada: ALT+{tecla.upper()}"
    except Exception as e:  # pragma: no cover - depende do ambiente gráfico
        return False, f"Falha ao enviar atalho: {e}"
