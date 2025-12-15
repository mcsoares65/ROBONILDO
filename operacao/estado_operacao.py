# ARQUIVO: operacao/estado_operacao.py
# PROJETO: ROBONILDO_102
# FUNÇÃO: memória operacional (posição aberta) + regras de transição

from dataclasses import dataclass
from datetime import datetime


def _agora(agora: datetime | None) -> datetime:
    return agora or datetime.now()


@dataclass
class EstadoOperacao:
    posicao: str = "SEM_POSICAO"   # SEM_POSICAO | COMPRADO | VENDIDO
    entrou_em: datetime | None = None
    saiu_em: datetime | None = None
    preco_entrada: float | None = None
    preco_saida: float | None = None
    ultima_acao: str | None = None  # AGUARDAR|COMPRAR|VENDER|ENCERRAR|MANTER etc.

    def esta_aberto(self) -> bool:
        return self.posicao in ("COMPRADO", "VENDIDO")

    def abrir_compra(self, agora: datetime | None = None, preco: float | None = None):
        t = _agora(agora)
        self.posicao = "COMPRADO"
        self.entrou_em = t
        self.preco_entrada = preco
        self.saiu_em = None
        self.preco_saida = None
        self.ultima_acao = "COMPRAR"

    def abrir_venda(self, agora: datetime | None = None, preco: float | None = None):
        t = _agora(agora)
        self.posicao = "VENDIDO"
        self.entrou_em = t
        self.preco_entrada = preco
        self.saiu_em = None
        self.preco_saida = None
        self.ultima_acao = "VENDER"

    def encerrar(self, agora: datetime | None = None, preco: float | None = None):
        t = _agora(agora)
        self.saiu_em = t
        self.preco_saida = preco
        self.posicao = "SEM_POSICAO"
        self.ultima_acao = "ENCERRAR"

    def manter(self):
        self.ultima_acao = "MANTER"

    def aplicar_acao(self, acao_final: str, agora: datetime | None = None, preco: float | None = None):
        """Atualiza o estado de forma segura, impedindo reentradas equivocadas."""
        if acao_final == "COMPRAR":
            if self.posicao != "SEM_POSICAO":
                self.manter()
                return
            self.abrir_compra(agora, preco)
            return

        if acao_final == "VENDER":
            if self.posicao != "SEM_POSICAO":
                self.manter()
                return
            self.abrir_venda(agora, preco)
            return

        if acao_final == "ENCERRAR":
            if self.esta_aberto():
                self.encerrar(agora, preco)
            else:
                self.ultima_acao = "ENCERRAR"
            return

        self.manter()
