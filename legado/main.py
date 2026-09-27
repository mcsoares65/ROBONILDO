from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Tuple

from execucao.estado_operacao import carregar_estado, salvar_estado
from execucao.gestor_operacao import GestorOperacao
from ia.decisor_openai import DecisorOpenAI


def configurar_logger() -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger("execucao")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        caminho_log = os.path.join("logs", "execucao.log")
        handler = logging.FileHandler(caminho_log, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def capturar_contexto() -> Tuple[float, datetime]:
    """
    Captura simplificada do contexto de preço/hora.
    Em uma integração real, este método deve ler o último preço do feed
    de mercado ou da planilha em uso.
    """
    return 0.0, datetime.now()


def narrar(acao_exec: str, motivo: str, logger: logging.Logger) -> None:
    texto = f"Ação executável: {acao_exec} — {motivo}"
    print(texto)
    logger.info(texto)


def main() -> None:
    logger = configurar_logger()

    estado = carregar_estado()
    preco_atual, horario = capturar_contexto()

    ia = DecisorOpenAI()
    decisao_ia = ia.decidir()

    gestor = GestorOperacao()
    acao_exec, motivo = gestor.avaliar(decisao_ia, estado)

    estado.registrar_decisao(acao_exec, preco_atual, horario)
    salvar_estado(estado)

    narrar(acao_exec, motivo, logger)

    logger.info(
        "Resumo IA: %s | Confiança: %s | Motivo: %s",
        decisao_ia.action,
        decisao_ia.confidence,
        decisao_ia.reason_short,
    )


if __name__ == "__main__":
    main()
