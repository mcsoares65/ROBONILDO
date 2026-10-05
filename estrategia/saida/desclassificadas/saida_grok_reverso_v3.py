"""Saída Grok reverso v3 — só escuta reversão depois de 0,618R.

S001. Candidata. Não é titular.

A v2 escutava estocástico extremo com QUALQUER lucro > 0 e ficou 13ª
(−R$ 2.135 vs v4): cortou alvo pequeno.

Aqui o regime da abertura é o risco estrutural (entrada − stop).
Só depois que o flutuante passa 0,618 desse risco o cartucho passa a
aceitar reversão. Confirmação: estocástico saindo do extremo contra.

    30/09: risco 1.165 pts → arma em ~720 pts. Pico foi +1.025. Armaria.
    Porta 1 típica (risco 200–400): não escuta ruído de +R$ 10.

Sem MFE no posicao não dá para fib de retração do swing. 0,618R é o
Fibonacci aplicável com o contrato atual. Perda: stop + cortes v4.
"""

from datetime import datetime
from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_grok_reverso_v3"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
FIB_ARMAR = 0.618
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


def _risco_abertura(posicao):
    entrada = _numero(posicao.get("entrada"))
    stop = _numero(posicao.get("stop"))
    if entrada is None or stop is None:
        return None
    risco = abs(entrada - stop)
    return risco if risco > 0 else None


def _motivo(row, posicao):
    lado = str(posicao.get("lado", "")).upper()
    lucro = _numero(posicao.get("resultado_flutuante_pts"))
    risco = _risco_abertura(posicao)
    if lucro is not None and risco is not None and lucro >= FIB_ARMAR * risco:
        if lado == "COMPRA" and bool(row.get("stoch_cross_down_80")):
            return "REVERSO_FIB_EXTREMO"
        if lado == "VENDA" and bool(row.get("stoch_cross_up_20")):
            return "REVERSO_FIB_EXTREMO"

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
    if motivo == "REVERSO_FIB_EXTREMO":
        return ("Lucro passou 0,618 do risco da abertura e o estocástico "
                f"saiu do extremo contra. Realizados {pts:.0f} pts.")
    if motivo == "PROTECAO_FINAL_PROPORCIONAL":
        return f"Perda de {abs(pts):.0f} pts no período final. Encerrado."
    if motivo == "PROTECAO_V3":
        return f"Proteção 17:15: perda de {abs(pts):.0f} pts."
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
