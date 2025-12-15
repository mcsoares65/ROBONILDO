# ARQUIVO: vision/visao_pipeline.py
# ROBONILDO_101 — Pipeline de visão (foco ProfitPro + captura por offset relativo à janela)

from config import NOME_TELA_PROFIT
from visao.foco_profit import FocoProfit
from visao.captura_janela import CapturaJanela


class PipelineVisao:
    def __init__(self, offset_grafico, nome_tela_profit: str = NOME_TELA_PROFIT):
        """
        offset_grafico = dict(x=..., y=..., width=..., height=...)
        (relativo à janela do ProfitPro)
        """
        self.foco = FocoProfit(nome_tela_profit)
        self.cap = CapturaJanela()
        self.off = offset_grafico

    def capturar_grafico(self):
        hwnd = self.foco.focar()
        if not hwnd:
            return None, "ProfitPro não encontrado"

        # valida foco pelo próprio HWND do ProfitPro
        if not self.foco.esta_em_foco(hwnd_esperado=hwnd):
            return None, "ProfitPro não ficou em foco (Windows bloqueou o foco)"

        left, top, right, bottom = self.foco.obter_rect(hwnd)
        win_w = right - left
        win_h = bottom - top

        x = self.off["x"]
        y = self.off["y"]
        w = self.off["width"]
        h = self.off["height"]

        if x < 0 or y < 0 or (x + w) > win_w or (y + h) > win_h:
            return None, f"Offset do gráfico fora da janela (janela={win_w}x{win_h}, off={x},{y},{w},{h})"

        abs_left = left + x
        abs_top = top + y

        img = self.cap.capturar_regiao(abs_left, abs_top, w, h)
        return img, None
