"""Saída Grok reverso v2 — um gatilho, o que o grid mediu.

S001. Candidata. Não é titular.

Abertura: stop estrutural 5 candles + 1,55R.
Lucro: fecha se o estocástico SAI da zona extrema CONTRA a posição
(compra: cruza 80 para baixo; venda: cruza 20 para cima).
Perda: stop estrutural; cortes 17:15 / 18:00 iguais à v4.

Não usa MACD nem MA21 na saída — no grid oficial esses dois pioram o total.
Só o extremo melhorou ret/risco (58,3 vs 53,5) e DD nos dois períodos.
"""

from datetime import datetime
from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_grok_reverso_v2"
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
    lado = str(posicao.get("lado", "")).upper()
    lucro = _numero(posicao.get("resultado_flutuante_pts"))
    if lucro is not None and lucro > 0:
        if lado == "COMPRA" and bool(row.get("stoch_cross_down_80")):
            return "REVERSO_EXTREMO"
        if lado == "VENDA" and bool(row.get("stoch_cross_up_20")):
            return "REVERSO_EXTREMO"

    horario = _horario(row)
    atr = _numero(row.get("atr"))
    if horario is None or lucro is None or atr is None or atr <= 0:
        return None
    if horario >= HORARIO_PROTECAO_PROPORCIONAL:
        if lucro <= -(PERDA_FINAL_ATR * atr):
            return "PROTECAO_FINAL_PROPORCIONAL"
        return None
    if horario >= HORARIO_PROTECAO_V3:
        limite = max(PERDA_MINIMA_V3_PONTOS, MULTIPLICADOR_V3_ATR * atr)
        if lucro <= -limite:
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
    pts = _numero(posicao.get("resultado_flutuante_pts")) or 0.0
    if motivo == "REVERSO_EXTREMO":
        return ("Estocástico saiu da zona extrema contra a posição. "
                f"Lucro de {pts:.0f} pts realizado.")
    if motivo == "PROTECAO_FINAL_PROPORCIONAL":
        return (f"Perda de {abs(pts):.0f} pts no período final. Posição encerrada.")
    if motivo == "PROTECAO_V3":
        return (f"Proteção 17:15: perda de {abs(pts):.0f} pts.")
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
