"""Saida estrutural assimetrica com cauda limitada por ATR.

Autoria: ChatGPT (OpenAI), a pedido de Marcio Soares.

Contrato S001. Na abertura, mede o risco pela maxima/minima dos quatro candles
mais recentes. O stop efetivo fica limitado a 2,10 ATR. O alvo conserva o risco
estrutural original e usa 1,90R em COMPRA e 1,55R em VENDA. Depois da abertura,
o cartucho nao antecipa o encerramento: stop, alvo e corte obrigatorio continuam
sob o motor.

Os parametros foram selecionados em 150 pregoes e mantidos sem alteracao em
50 pregoes de validacao, 50 de teste e 183 pregoes anteriores fora da selecao.
Nao depende de data, preco absoluto, arquivo externo ou estado global.
"""

from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_chatgpt_estrutura_assimetrica_v1"
CANDLES_ESTRUTURA = 4
RISCO_MAXIMO_ATR = 2.10
RR_COMPRA = 1.90
RR_VENDA = 1.55


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _protecao_inicial(row, posicao):
    entrada = _numero(posicao.get("entrada"))
    lado = str(posicao.get("lado", "")).upper()
    janela = (row.get("ohlc_recentes") or ())[-CANDLES_ESTRUTURA:]
    atr = _numero(row.get("atr"))
    if entrada is None or atr is None or atr <= 0:
        raise ValueError("entrada ou ATR invalido")
    if len(janela) < CANDLES_ESTRUTURA:
        raise ValueError("historico insuficiente para definir a protecao")

    if lado == "COMPRA":
        stop_estrutural = min(float(c["Minimo"]) for c in janela)
        direcao = 1.0
        rr = RR_COMPRA
        risco_estrutural = entrada - stop_estrutural
    elif lado == "VENDA":
        stop_estrutural = max(float(c["Maximo"]) for c in janela)
        direcao = -1.0
        rr = RR_VENDA
        risco_estrutural = stop_estrutural - entrada
    else:
        raise ValueError(f"lado invalido: {lado}")

    if not isfinite(risco_estrutural) or risco_estrutural <= 0:
        raise ValueError(f"risco estrutural invalido para {lado}")

    risco_stop = min(risco_estrutural, RISCO_MAXIMO_ATR * atr)
    stop = entrada - direcao * risco_stop
    alvo = entrada + direcao * rr * risco_estrutural
    if not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"stop ou alvo invalido para {lado}")
    return stop, alvo


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionarios")
    candles = _numero(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos invalido")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida"]
