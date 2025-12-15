# ARQUIVO: regras/pregao.py
# PROJETO: ROBONILDO_102
# FUNÇÃO: regras de horário (09:01–18:20) + margem de zeragem

from dataclasses import dataclass
from datetime import time


@dataclass
class RegrasPregao:
    hora_inicio: time = time(9, 1)
    hora_fim: time = time(18, 21)

    # Margem (minutos) para zerar antes do fim (evita taxa de zeragem/correria)
    margem_zeragem_min: int = 2

    def dentro_horario(self, agora_local) -> bool:
        t = agora_local.time()
        return self.hora_inicio <= t <= self.hora_fim

    def perto_de_encerrar(self, agora_local) -> bool:
        # exemplo: fim 18:20, margem 2min => 18:18 em diante
        fim = self.hora_fim
        limite_h = fim.hour
        limite_m = fim.minute - self.margem_zeragem_min
        # corrige underflow simples
        if limite_m < 0:
            limite_h -= 1
            limite_m += 60
        limite = time(limite_h, limite_m)
        return agora_local.time() >= limite
