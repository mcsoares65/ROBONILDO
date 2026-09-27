"""Cartucho candidato de saída do Robonildo — ChatGPT V1.

Objetivo
--------
Reter parte de um lucro relevante quando o mercado devolve a máxima excursão
favorável (MFE), sem competir com o stop e o alvo rígidos do motor.

Contrato público
----------------
``avaliar_saida(row, posicao) -> bool``

O motor consulta este cartucho apenas no fechamento de cada candle de 15
minutos e somente depois de verificar stop/alvo. Portanto, ``True`` solicita
uma saída a mercado no fechamento observado; não é promessa de preço nem de
liquidez.

Instalação como candidata
-------------------------
Copiar para ``estrategia/saida/saida_chatgpt_v1.py``. Não colocar diretamente
em ``estrategia/saida/titular/``: primeiro execute ``classificacao.py`` e
compare com ``baseline.py`` no ranking de saída e no ranking cruzado.
"""

from datetime import datetime
from math import isfinite


NOME = "saida_chatgpt_v1"

# A proteção só é armada depois de uma excursão realmente relevante.
MFE_MINIMA_PONTOS = 350.0
MFE_MINIMA_ATR = 0.90
MINIMO_CANDLES = 2

# Trailing sobre a melhor excursão já alcançada.
DEVOLUCAO_MINIMA_PONTOS = 150.0
DEVOLUCAO_FRACAO_MFE = 0.30
DEVOLUCAO_EMERGENCIA_FRACAO_MFE = 0.45
LUCRO_RESTANTE_MINIMO_PONTOS = 125.0
LUCRO_RESTANTE_FRACAO_MFE = 0.40

# O rótulo 17:45 corresponde ao fechamento/executável das 18:00 no motor
# histórico de 15 minutos. Isso deixa margem antes do corte rígido das 18:20.
ROTULO_REALIZACAO_FIM_DIA = "17:45"
LUCRO_MINIMO_FIM_DIA_PONTOS = 100.0


def _numero(valor, padrao=0.0):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return padrao
    return numero if isfinite(numero) else padrao


def _horario_rotulo(valor):
    if isinstance(valor, datetime):
        return valor.strftime("%H:%M")
    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except (TypeError, ValueError):
            return ""
    return ""


def _confirmacoes_reversao(row, lado):
    """Conta sinais de perda de força contrários ao lado da posição."""
    macd = _numero(row.get("macd"), None)
    sinal = _numero(row.get("macd_signal"), None)

    if lado == "COMPRA":
        confirmacoes = [
            bool(row.get("stoch_descendo")),
            bool(row.get("rsi_descendo")),
            macd is not None and sinal is not None and macd < sinal,
        ]
    else:
        confirmacoes = [
            bool(row.get("stoch_subindo")),
            bool(row.get("rsi_subindo")),
            macd is not None and sinal is not None and macd > sinal,
        ]
    return sum(confirmacoes)


def avaliar_saida(row, posicao):
    """Retorna ``True`` quando a posição deve ser encerrada antecipadamente.

    Regras, nesta ordem:
    1. No fechamento rotulado 17:45 ou depois, realiza posição que ainda
       conserve pelo menos 100 pontos de lucro.
    2. Depois de MFE >= máximo(350 pontos, 0,90 ATR), arma trailing.
    3. Sai após devolver >= máximo(150 pontos, 30% da MFE), se ainda retiver
       >= máximo(125 pontos, 40% da MFE) e houver duas confirmações de
       reversão entre Estocástico, RSI e MACD.
    4. Uma devolução >= 45% da MFE aciona proteção de emergência mesmo sem
       as duas confirmações, desde que o lucro mínimo ainda exista.

    Stop e alvo não aparecem aqui porque o próprio motor os avalia antes.
    """
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        return False

    lado = str(posicao.get("lado", "")).upper()
    if lado not in {"COMPRA", "VENDA"}:
        return False

    candles = int(_numero(posicao.get("candles_decorridos"), 0.0))
    lucro_atual = _numero(posicao.get("resultado_flutuante_pts"), 0.0)
    if lucro_atual <= 0:
        return False

    horario = _horario_rotulo(row.get("dt"))
    if horario >= ROTULO_REALIZACAO_FIM_DIA and lucro_atual >= LUCRO_MINIMO_FIM_DIA_PONTOS:
        return True

    if candles < MINIMO_CANDLES:
        return False

    entrada = _numero(posicao.get("entrada"), 0.0)
    maxima = _numero(posicao.get("maxima_desde_entrada"), entrada)
    minima = _numero(posicao.get("minima_desde_entrada"), entrada)
    mfe = (maxima - entrada) if lado == "COMPRA" else (entrada - minima)

    atr = max(0.0, _numero(row.get("atr"), 0.0))
    ativacao = max(MFE_MINIMA_PONTOS, MFE_MINIMA_ATR * atr)
    if mfe < ativacao:
        return False

    devolucao = max(0.0, mfe - lucro_atual)
    lucro_a_reter = max(LUCRO_RESTANTE_MINIMO_PONTOS, LUCRO_RESTANTE_FRACAO_MFE * mfe)
    if lucro_atual < lucro_a_reter:
        return False

    limite_normal = max(DEVOLUCAO_MINIMA_PONTOS, DEVOLUCAO_FRACAO_MFE * mfe)
    if devolucao >= limite_normal and _confirmacoes_reversao(row, lado) >= 2:
        return True

    limite_emergencia = max(DEVOLUCAO_MINIMA_PONTOS, DEVOLUCAO_EMERGENCIA_FRACAO_MFE * mfe)
    return devolucao >= limite_emergencia

