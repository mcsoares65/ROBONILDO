"""Saída Perda Final às 17h — v01.

A partir das 17:00, encerra a posição cuja perda alcance 150 pontos. Abertura: stop estrutural
dos últimos 4 candles e alvo de 1,55R, como as demais saídas.
Origem: camada "final" de `saida_protecoes_cirurgicas_v01` (que reunia quatro regras soltas).

Autoria: extração literal por Claude (Anthropic), a pedido do dono do laboratório (Regra 16,
saídas). Revisão humana antes do teste oficial: pendente. O `v0N` é a versão da estratégia, não a
VERSAO do projeto. Nenhum limiar foi alterado; o que sai do arquivo de origem é só a(s) outra(s)
regra(s) de encerramento solta(s). Variações testadas antes desta versão (Regra 11.2): nenhuma.
Sem dependência de data, evento ou preço absoluto (Regra 11.3). Resultado financeiro: ainda não
medido por esta versão; rodar `classificacao.py` (Regra 12).
"""

from datetime import datetime
from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_perda_final_1700_v01"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
HORARIO_INICIO_PROTECAO = "17:00"
PERDA_FINAL_PONTOS = 150.0


def _numero_finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _horario(row):
    valor = row.get("dt")
    if isinstance(valor, datetime) or hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except (TypeError, ValueError):
            return None
    return None


def _protecao_inicial(row: dict, posicao: dict) -> tuple[float, float]:
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")

    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
        risco = stop - entrada
        alvo = entrada - RELACAO_RISCO_RETORNO * risco
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if risco <= 0 or not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Proteção inicial inválida para {lado}.")
    return stop, alvo


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")

    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    horario = _horario(row)
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    atr = _numero_finito(row.get("atr"))
    fechar = False
    if (
        horario is not None
        and resultado is not None
        and horario >= HORARIO_INICIO_PROTECAO
    ):
        fechar = resultado <= -PERDA_FINAL_PONTOS

    return {"fechar": bool(fechar), "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    decisao = avaliar_saida(row, posicao)
    if not decisao["fechar"]:
        return None
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    return (
        "Proteção de fim de pregão acionada: a posição permaneceu negativa "
        f"e atingiu {abs(resultado):.0f} pontos de perda."
    )


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
