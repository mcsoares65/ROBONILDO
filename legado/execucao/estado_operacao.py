from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


CAMINHO_ESTADO = os.path.join("logs", "estado_104.json")


@dataclass
class EstadoOperacao:
    posicao: str = "NENHUMA"
    preco_entrada: Optional[float] = None
    hora_entrada: Optional[str] = None
    ultimo_preco_analisado: Optional[float] = None
    hora_ultima_decisao: Optional[str] = None

    def registrar_decisao(self, acao_exec: str, preco_atual: Optional[float], horario: datetime) -> None:
        """
        Atualiza o estado interno de acordo com a ação executável decidida
        pelo gestor de operações.
        """
        self.ultimo_preco_analisado = preco_atual
        self.hora_ultima_decisao = horario.isoformat()

        if acao_exec == "COMPRAR":
            self.posicao = "COMPRADO"
            self.preco_entrada = preco_atual
            self.hora_entrada = horario.isoformat()
        elif acao_exec == "VENDER":
            self.posicao = "VENDIDO"
            self.preco_entrada = preco_atual
            self.hora_entrada = horario.isoformat()
        elif acao_exec == "SAIR":
            self.posicao = "NENHUMA"
            self.preco_entrada = None
            self.hora_entrada = None


def carregar_estado(caminho: str = CAMINHO_ESTADO) -> EstadoOperacao:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)

    if not os.path.exists(caminho):
        return EstadoOperacao()

    with open(caminho, "r", encoding="utf-8") as fp:
        dados = json.load(fp)

    return EstadoOperacao(
        posicao=dados.get("posicao", "NENHUMA"),
        preco_entrada=dados.get("preco_entrada"),
        hora_entrada=dados.get("hora_entrada"),
        ultimo_preco_analisado=dados.get("ultimo_preco_analisado"),
        hora_ultima_decisao=dados.get("hora_ultima_decisao"),
    )


def salvar_estado(estado: EstadoOperacao, caminho: str = CAMINHO_ESTADO) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as fp:
        json.dump(asdict(estado), fp, ensure_ascii=False, indent=2)
