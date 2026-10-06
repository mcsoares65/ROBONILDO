# TITULAR EM TRANSICAO (V496, Regra 16): une duas regras soltas (corte 17h15 e corte 18h). Segue em operacao
# ate o dono trocar o titular por merge de PR. Ver conselho/2026-10-05-AG.txt.
"""Saída ChatGPT V4 — proteção proporcional no encerramento.

Candidata S001. Preserva o stop estrutural e o alvo de 1,55R da V3. A partir
das 18h, encerra posições cuja perda alcance 0,50 ATR, evitando que uma
operação sem continuidade consuma o restante do risco até o corte obrigatório.
"""

from datetime import datetime
from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_protecao_encerramento_v02"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
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
