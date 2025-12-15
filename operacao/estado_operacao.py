# ARQUIVO: operacao/estado_operacao.py
# PROJETO: ROBONILDO_102
# FUNÇÃO: memória operacional (posição aberta) + regras de transição

from dataclasses import dataclass
from datetime import datetime


@dataclass
class EstadoOperacao:
    posicao: str = "SEM_POSICAO"   # SEM_POSICAO | COMPRADO | VENDIDO
    abriu_em: datetime | None = None
    ultima_acao: str | None = None  # AGUARDAR|COMPRAR|VENDER|ENCERRAR|MANTER etc.

    def esta_aberto(self) -> bool:
        return self.posicao in ("COMPRADO", "VENDIDO")

    def abrir_compra(self, agora: datetime):
        self.posicao = "COMPRADO"
        self.abriu_em = agora
        self.ultima_acao = "COMPRAR"

    def abrir_venda(self, agora: datetime):
        self.posicao = "VENDIDO"
        self.abriu_em = agora
        self.ultima_acao = "VENDER"

    def encerrar(self, agora: datetime):
        self.posicao = "SEM_POSICAO"
        self.abriu_em = None
        self.ultima_acao = "ENCERRAR"

    def manter(self):
        self.ultima_acao = "MANTER"
