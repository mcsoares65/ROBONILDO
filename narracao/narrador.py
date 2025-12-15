# ARQUIVO: narracao/narrador_oficial.py
# ROBONILDO_100 — Orquestrador oficial de narração (não bloqueante)

import time
import threading
import queue


class NarradorOficial:
    def __init__(self, voz, cooldown=3.0):
        """
        voz: instância de VozAdam (ou outro driver de voz)
        cooldown: tempo mínimo entre falas (segundos)
        """
        self.voz = voz
        self.cooldown = cooldown
        self._ultima_fala = 0.0
        self._fila = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def falar(self, texto: str, force=False):
        agora = time.time()

        if not force and (agora - self._ultima_fala) < self.cooldown:
            return

        try:
            self._fila.put_nowait(texto)
            self._ultima_fala = agora
        except queue.Full:
            pass

    def _worker(self):
        while True:
            texto = self._fila.get()
            try:
                self.voz.falar(texto)
            except Exception:
                pass
