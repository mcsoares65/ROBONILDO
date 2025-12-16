# comentarios/comentarista_tecnico.py

import time
import csv
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")

class ComentaristaTecnico:
    def __init__(self, narrador, timeframe="30M", intervalo_min=300):
        self.narrador = narrador
        self.timeframe = timeframe
        self.intervalo_min = intervalo_min
        self.ultimo_comentario = 0
        self.ultimo_contexto = None

        self.log_path = Path("logs/comentarios_tecnicos.csv")
        self.log_path.parent.mkdir(exist_ok=True)

        if not self.log_path.exists():
            with open(self.log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["timestamp", "timeframe", "contexto"])

    def analisar(self, decisao):
        agora = time.time()

        if agora - self.ultimo_comentario < self.intervalo_min:
            return

        contexto = self._extrair_contexto(decisao)

        if contexto == self.ultimo_contexto:
            return

        self.ultimo_contexto = contexto
        self.ultimo_comentario = agora

        self._logar(contexto)
        self.narrador.falar(contexto, force=True)

    def _extrair_contexto(self, decisao):
        texto = decisao.reason_short.lower()

        if "resist" in texto:
            return "Preço próximo de resistência. Mercado pode travar."
        if "suporte" in texto:
            return "Preço próximo de suporte. Região importante para reação."
        if "consol" in texto:
            return "Mercado em consolidação. Sem direção clara."
        if "romp" in texto:
            return "Possível rompimento em formação, aguardando confirmação."
        if "tend" in texto:
            return "Tendência definida no gráfico atual."

        return "Mercado em observação, aguardando definição."

    def _logar(self, contexto):
        with open(self.log_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
                self.timeframe,
                contexto
            ])
