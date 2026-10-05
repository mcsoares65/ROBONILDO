"""Stop/alvo titular com saida por falta de progresso — ChatGPT v1.

Autoria: ChatGPT (OpenAI), a pedido de Marcio Soares. Revisao humana e do
conselho: pendentes. ``v1`` e a versao propria deste cartucho.

Mantem stop estrutural de cinco candles e alvo 1,55R. A unica hipotese nova e:
apos quatro candles completos, se a excursao favoravel nunca alcancou 0,45 ATR
e a operacao esta negativa em pelo menos 0,15 ATR, encerra no fechamento. A
regra tenta liberar capital de sinais que nao desenvolveram, sem mexer em
operacoes que ja demonstraram continuidade.

Variacoes relevantes testadas antes da submissao (Regra 11.2): nenhuma.
Sem dependencia de data, evento ou preco absoluto (Regra 11.3).
Resultado financeiro: ainda nao medido; aguarda revisao do PR (Regra 12).
"""

from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_chatgpt_tempo_sem_progresso_v1"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
CANDLES_MINIMOS = 4
PROGRESSO_MIN_ATR = 0.45
PERDA_MIN_ATR = 0.15


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _protecao_inicial(row, posicao):
    entrada = _numero(posicao.get("entrada"))
    lado = str(posicao.get("lado", "")).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if entrada is None or len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("historico insuficiente para a protecao inicial")
    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
        risco = stop - entrada
        alvo = entrada - RELACAO_RISCO_RETORNO * risco
    else:
        raise ValueError(f"lado invalido: {lado}")
    if risco <= 0 or not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"protecao inicial invalida para {lado}")
    return stop, alvo


def _sem_progresso(row, posicao):
    candles = _numero(posicao.get("candles_decorridos"))
    entrada = _numero(posicao.get("entrada"))
    maxima = _numero(posicao.get("maxima_desde_entrada"))
    minima = _numero(posicao.get("minima_desde_entrada"))
    resultado = _numero(posicao.get("resultado_flutuante_pts"))
    atr = _numero(row.get("atr"))
    lado = str(posicao.get("lado", "")).upper()
    if any(v is None for v in (candles, entrada, maxima, minima, resultado, atr)) or atr <= 0:
        return False
    if candles < CANDLES_MINIMOS or resultado > -(PERDA_MIN_ATR * atr):
        return False
    if lado == "COMPRA":
        progresso = maxima - entrada
    elif lado == "VENDA":
        progresso = entrada - minima
    else:
        return False
    return progresso < PROGRESSO_MIN_ATR * atr


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionarios")
    candles = _numero(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos invalido")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {"fechar": bool(_sem_progresso(row, posicao)), "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    if _sem_progresso(row, posicao):
        return ("A operacao completou quatro candles sem avancar 0,45 ATR e "
                "permanece negativa. A posicao foi encerrada por falta de progresso.")
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
