from __future__ import annotations

from ia.decisor_openai import DecisaoIA
from .estado_operacao import EstadoOperacao


class GestorOperacao:
    def avaliar(self, decisao_ia: DecisaoIA, estado: EstadoOperacao) -> tuple[str, str]:
        acao = decisao_ia.action.upper()
        posicao = (estado.posicao or "NENHUMA").upper()

        if posicao == "NENHUMA":
            if acao == "COMPRAR":
                return "COMPRAR", "Sem posição, seguindo compra sugerida."
            if acao == "VENDER":
                return "VENDER", "Sem posição, seguindo venda sugerida."
            return "AGUARDAR", "Sem posição, aguardando conforme IA."

        if posicao == "COMPRADO":
            if acao == "VENDER":
                return "SAIR", "IA pediu venda; vamos zerar a compra."
            if acao == "COMPRAR":
                return "AGUARDAR", "Já estamos comprados; bloqueando nova compra."
            return "AGUARDAR", "Mantendo compra aberta; IA sugere aguardar."

        if posicao == "VENDIDO":
            if acao == "COMPRAR":
                return "SAIR", "IA pediu compra; vamos encerrar a venda."
            if acao == "VENDER":
                return "AGUARDAR", "Já estamos vendidos; bloqueando nova venda."
            return "AGUARDAR", "Mantendo venda aberta; IA sugere aguardar."

        return "AGUARDAR", "Estado desconhecido; mantendo aguardando."
