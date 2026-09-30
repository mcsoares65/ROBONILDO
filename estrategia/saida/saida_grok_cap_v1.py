"""Saída Grok cap v1 — teto de risco na proteção inicial.

Contrato S001. Parte da v4 (1,55R + cortes de perda 17:15/18:00).
NÃO faz breakeven, trailing nem realiza em sinal de reversão — essa
família já foi medida e destruiu 12–78% do resultado.

O vazamento de 30/09 não foi "falta de reversão": Porta 2 abriu com
stop estrutural de 1165 pts e alvo de 1806 pts. O preço andou +960 pts
(53% do alvo) e recuou. Com teto de 500 pts o alvo teria sido 775 pts
(188495) — nível que o pregão CRUZOU às 15:00.

Regra: se o swing de 5 candles exigir mais que MAX_RISCO_PONTOS, o stop
é preso a esse teto e o alvo continua 1,55R sobre o risco limitado.
Trades com stop estrutural ≤ 500 pts ficam idênticos à v4.

Candidata. Não promover sem C001 com vantagem > ruído do período.
"""

from datetime import datetime
from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_grok_cap_v1"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
MAX_RISCO_PONTOS = 500.0
HORARIO_PROTECAO_V3 = "17:15"
HORARIO_PROTECAO_PROPORCIONAL = "18:00"
PERDA_MINIMA_V3_PONTOS = 275.0
MULTIPLICADOR_V3_ATR = 0.25
PERDA_FINAL_ATR = 0.50


def _numero(valor):
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


def _protecao_inicial(row, posicao):
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")

    if lado == "COMPRA":
        stop_estrutural = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop_estrutural
        if risco > MAX_RISCO_PONTOS:
            stop = entrada - MAX_RISCO_PONTOS
            risco = MAX_RISCO_PONTOS
        else:
            stop = stop_estrutural
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    elif lado == "VENDA":
        stop_estrutural = max(float(c["Maximo"]) for c in janela)
        risco = stop_estrutural - entrada
        if risco > MAX_RISCO_PONTOS:
            stop = entrada + MAX_RISCO_PONTOS
            risco = MAX_RISCO_PONTOS
        else:
            stop = stop_estrutural
        alvo = entrada - RELACAO_RISCO_RETORNO * risco
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if risco <= 0 or not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Proteção inicial inválida para {lado}.")
    return stop, alvo


def _motivo(row, posicao):
    horario = _horario(row)
    resultado = _numero(posicao.get("resultado_flutuante_pts"))
    atr = _numero(row.get("atr"))
    if horario is None or resultado is None or atr is None or atr <= 0:
        return None

    if horario >= HORARIO_PROTECAO_PROPORCIONAL:
        if resultado <= -(PERDA_FINAL_ATR * atr):
            return "PROTECAO_FINAL_PROPORCIONAL"
        return None

    if horario >= HORARIO_PROTECAO_V3:
        limite_v3 = max(PERDA_MINIMA_V3_PONTOS, MULTIPLICADOR_V3_ATR * atr)
        if resultado <= -limite_v3:
            return "PROTECAO_V3"
    return None


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    candles = _numero(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {"fechar": _motivo(row, posicao) is not None,
            "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    motivo = _motivo(row, posicao)
    resultado = _numero(posicao.get("resultado_flutuante_pts")) or 0.0
    if motivo == "PROTECAO_FINAL_PROPORCIONAL":
        return ("A operação não apresentou continuidade até o período final "
                f"do pregão e atingiu {abs(resultado):.0f} pontos de perda. "
                "A posição foi encerrada para limitar a exposição.")
    if motivo == "PROTECAO_V3":
        return ("Proteção de fim de pregão acionada: a posição permaneceu "
                f"negativa e atingiu {abs(resultado):.0f} pontos de perda.")
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
