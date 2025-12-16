# comentarios/comentarista_fluxo.py

import time
import csv
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")

class ComentaristaFluxo:
    def __init__(self, narrador, intervalo_min=120):
        self.narrador = narrador
        self.intervalo_min = intervalo_min
        self.ultimo_comentario = 0
        self.ultimo_estado = None

        self.log_path = Path("logs/comentarios_fluxo.csv")
        self.log_path.parent.mkdir(exist_ok=True)

        if not self.log_path.exists():
            with open(self.log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["timestamp", "estado_fluxo"])

    def analisar(self, decisao):
        agora = time.time()

        if agora - self.ultimo_comentario < self.intervalo_min:
            return

        estado = self._inferir_fluxo(decisao)

        if estado == self.ultimo_estado:
            return

        self.ultimo_estado = estado
        self.ultimo_comentario = agora

        self._logar(estado)
        self.narrador.falar(estado, force=True)

    def _inferir_fluxo(self, decisao):
        conf = decisao.confidence

        if conf < 0.35:
            return "Fluxo fraco. Mercado sem agressividade."
        if conf < 0.55:
            return "Fluxo inconsistente. Aguardando continuidade."
        if conf < 0.75:
            return "Fluxo começando a ganhar força."
        return "Fluxo forte detectado. Atenção ao próximo movimento."

    def _logar(self, estado):
        with open(self.log_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
                estado
            ])
