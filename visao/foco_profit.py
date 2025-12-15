# ARQUIVO: vision/foco_profit.py
# ROBONILDO_101 — Foco robusto no ProfitPro (filtra ruído e valida janela ativa)

import win32gui
import win32con
import time


class FocoProfit:
    def __init__(self, titulo_contendo="ProfitPro"):
        self.titulo = titulo_contendo

        self.blacklist = [
            "prompt de comando",
            "command prompt",
            "windows terminal",
            "powershell",
            "notepad++",
            "visual studio code",
        ]

    def _titulo_ok(self, titulo: str) -> bool:
        t = (titulo or "").lower()
        if not t:
            return False
        if self.titulo.lower() not in t:
            return False
        for b in self.blacklist:
            if b in t:
                return False
        return True

    def _encontrar_janelas(self):
        janelas = []

        def enum_handler(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                titulo = win32gui.GetWindowText(hwnd)
                if self._titulo_ok(titulo):
                    janelas.append((hwnd, titulo))

        win32gui.EnumWindows(enum_handler, None)
        return janelas

    def focar(self):
        janelas = self._encontrar_janelas()
        if not janelas:
            return None

        hwnd, _titulo = janelas[0]

        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

        time.sleep(0.05)
        return hwnd

    def esta_em_foco(self, hwnd_esperado=None) -> bool:
        """
        Se hwnd_esperado for passado, valida se o foreground é esse hwnd.
        Se não for passado, valida se o título do foreground contém self.titulo.
        """
        hwnd_ativo = win32gui.GetForegroundWindow()
        if hwnd_esperado is not None:
            return hwnd_ativo == hwnd_esperado

        titulo = win32gui.GetWindowText(hwnd_ativo) or ""
        return self.titulo.lower() in titulo.lower()

    def obter_rect(self, hwnd):
        return win32gui.GetWindowRect(hwnd)

    def titulo_da_janela(self, hwnd):
        return win32gui.GetWindowText(hwnd)
