"""Orquestrador dinâmico de estratégias de entrada.

Este cartucho não contém uma hipótese de entrada própria. Ele descobre os
cartuchos instalados em ``estrategia/entrada`` que oferecem simultaneamente:

    gerar_sinal(row)
    diagnosticar_oportunidades(row)

Cada oportunidade é normalizada para um score técnico comparável. A mais
aderente ao estado corrente vai para o radar; no fechamento, somente
oportunidades efetivamente confirmadas podem produzir sinal.

IMPORTANTE: esta é uma CANDIDATA. Ela precisa vencer o ranking oficial antes
de ser movida para ``titular/``. A seleção não consulta resultado futuro,
arquivos de operações nem o histórico de classificação.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


NOME_ESTRATEGIA = "Orquestrador Dinâmico v1"
VERSAO_CONTRATO = 1
MARGEM_CONFLITO_PONTOS = 2.0

_ARQUIVO_ATUAL = Path(__file__).resolve()
_PASTA_ENTRADA = _ARQUIVO_ATUAL.parent
_PASTA_TITULAR = _PASTA_ENTRADA / "titular"


def _importar(caminho: Path, indice: int) -> ModuleType:
    nome = f"robonildo_orq_{indice}_{abs(hash(caminho.resolve()))}"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    if spec is None or spec.loader is None:
        raise ImportError(f"Não foi possível importar {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _descobrir_cartuchos() -> tuple[list[dict], list[str]]:
    """Carrega somente cartuchos com telemetria suficiente para comparação."""
    caminhos = []
    caminhos.extend(sorted(_PASTA_TITULAR.glob("*.py")))
    caminhos.extend(sorted(_PASTA_ENTRADA.glob("*.py")))

    carregados: list[dict] = []
    rejeitados: list[str] = []
    vistos: set[str] = set()
    for indice, caminho in enumerate(caminhos):
        if caminho.resolve() == _ARQUIVO_ATUAL or caminho.stem.startswith("_"):
            continue
        # Se o titular também existir como candidata, conserva apenas o titular.
        chave = caminho.stem.casefold()
        if chave in vistos:
            continue
        vistos.add(chave)
        try:
            modulo = _importar(caminho, indice)
        except Exception as erro:
            rejeitados.append(
                f"{caminho.stem}: importação falhou ({type(erro).__name__}: {erro})"
            )
            continue
        gerar = getattr(modulo, "gerar_sinal", None)
        diagnosticar = getattr(modulo, "diagnosticar_oportunidades", None)
        if not callable(gerar) or not callable(diagnosticar):
            rejeitados.append(f"{caminho.stem}: sem diagnosticar_oportunidades(row)")
            continue
        carregados.append({
            "nome": caminho.stem,
            "modulo": modulo,
            "diagnosticar": diagnosticar,
            "confiabilidade": max(
                0.0,
                min(1.0, float(getattr(modulo, "CONFIABILIDADE_ORQUESTRADOR", 1.0))),
            ),
        })
    return carregados, rejeitados


_CARTUCHOS, CARTUCHOS_REJEITADOS = _descobrir_cartuchos()
CARTUCHOS_ELEGIVEIS = tuple(item["nome"] for item in _CARTUCHOS)


def _normalizar_oportunidade(origem: dict, item: dict) -> dict:
    if not isinstance(item, dict):
        raise TypeError("cada oportunidade precisa ser um dict")
    total = max(1, int(item.get("total", 1)))
    confirmadas = max(0, min(total, int(item.get("confirmadas", 0))))
    progresso = max(
        0.0,
        min(1.0, float(item.get("progresso", confirmadas / total))),
    )
    aderencia = max(0.0, min(1.0, float(item.get("aderencia_regime", 1.0))))
    confianca = max(0.0, min(1.0, float(item.get("confianca", 1.0))))
    confiabilidade = origem["confiabilidade"]

    # Prontidão domina o score. Aderência ao regime e confiança são extensões
    # opcionais do contrato; cartuchos atuais recebem valor neutro 1.0.
    score = 100.0 * progresso * (
        0.75 + 0.15 * aderencia + 0.10 * confianca
    ) * confiabilidade
    sinal = int(item.get("sinal", 0))
    if sinal not in (-1, 0, 1):
        raise ValueError(f"sinal inválido: {sinal!r}")

    return {
        **item,
        "estrategia": str(item.get("estrategia") or origem["nome"]),
        "cartucho": origem["nome"],
        "sinal": sinal,
        "confirmadas": confirmadas,
        "total": total,
        "progresso": progresso,
        "score": score,
        "prioridade": int(item.get("prioridade", 999)),
        "faltantes": list(item.get("faltantes") or []),
    }


def diagnosticar_oportunidades(row) -> list[dict]:
    oportunidades: list[dict] = []
    for origem in _CARTUCHOS:
        try:
            resposta = origem["diagnosticar"](row)
            if not isinstance(resposta, (list, tuple)):
                continue
            for item in resposta:
                oportunidades.append(_normalizar_oportunidade(origem, item))
        except Exception:
            # Um cartucho defeituoso é isolado; não derruba os concorrentes.
            continue
    return sorted(
        oportunidades,
        key=lambda item: (
            -item["score"],
            -int(item["sinal"] in (-1, 1)),
            item["prioridade"],
            item["cartucho"].casefold(),
            item["estrategia"].casefold(),
        ),
    )


def _confirmada_vencedora(row):
    confirmadas = [
        item for item in diagnosticar_oportunidades(row)
        if item["sinal"] in (-1, 1)
    ]
    if not confirmadas:
        return None, None
    melhor = confirmadas[0]
    opostas = [
        item for item in confirmadas[1:]
        if item["sinal"] == -melhor["sinal"]
        and melhor["score"] - item["score"] < MARGEM_CONFLITO_PONTOS
    ]
    if opostas:
        return None, (melhor, opostas[0])
    return melhor, None


def gerar_sinal(row) -> int:
    melhor, conflito = _confirmada_vencedora(row)
    if conflito is not None or melhor is None:
        return 0
    return int(melhor["sinal"])


def diagnosticar_sinal(row) -> dict:
    oportunidades = diagnosticar_oportunidades(row)
    melhor, conflito = _confirmada_vencedora(row)
    escolhida = melhor or (oportunidades[0] if oportunidades else None)
    if escolhida is None:
        return {
            "estrategia": NOME_ESTRATEGIA,
            "lado": "NEUTRA",
            "progresso": 0.0,
            "confirmadas": 0,
            "total": 1,
            "faltantes": ["nenhum cartucho elegível"],
            "explicacao": "Nenhum cartucho elegível foi encontrado pelo orquestrador.",
        }
    if conflito is not None:
        a, b = conflito
        explicacao = (
            f"Conflito entre {a['estrategia']} e {b['estrategia']}; "
            "a entrada foi bloqueada por segurança."
        )
    else:
        faltante = escolhida["faltantes"][0] if escolhida["faltantes"] else "nenhuma"
        explicacao = (
            f"O orquestrador selecionou {escolhida['estrategia']} do cartucho "
            f"{escolhida['cartucho']}, com score {escolhida['score']:.0f}, "
            f"{escolhida['confirmadas']} de {escolhida['total']} confirmações. "
            f"Próxima condição: {faltante}."
        )
    return {
        "porta": escolhida["prioridade"],
        "total_portas": len(oportunidades),
        "estrategia": escolhida["estrategia"],
        "cartucho": escolhida["cartucho"],
        "score": escolhida["score"],
        "lado": escolhida.get("direcao", "NEUTRA"),
        "progresso": escolhida["progresso"],
        "confirmadas": escolhida["confirmadas"],
        "total": escolhida["total"],
        "faltantes": escolhida["faltantes"],
        "conflito": conflito is not None,
        "explicacao": explicacao,
    }


if not _CARTUCHOS:
    raise RuntimeError(
        "Orquestrador sem cartuchos elegíveis. Cada participante precisa "
        "fornecer gerar_sinal(row) e diagnosticar_oportunidades(row)."
    )


__all__ = [
    "gerar_sinal",
    "diagnosticar_sinal",
    "diagnosticar_oportunidades",
    "CARTUCHOS_ELEGIVEIS",
    "CARTUCHOS_REJEITADOS",
]
