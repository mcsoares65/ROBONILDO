# ARQUIVO: vision/captura_janela.py
# ROBONILDO_100 — Captura de região relativa à janela (recorte seguro)

import mss
import numpy as np


class CapturaJanela:
    def __init__(self):
        self.sct = mss.mss()

    def capturar_regiao(self, left, top, width, height):
        regiao = {"left": int(left), "top": int(top), "width": int(width), "height": int(height)}
        img = self.sct.grab(regiao)
        return np.array(img)
