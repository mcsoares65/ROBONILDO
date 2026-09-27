"""Cartucho candidato de saída — ChatGPT V3.

Hipótese validada em três históricos do motor oficial do Robonildo:
    preservar o stop e o alvo estruturais e nunca antecipar uma operação
    vencedora; a partir do candle rotulado 17:15, encerrar apenas uma posição
    perdedora cuja perda alcance o maior valor entre 275 pontos e 0,25 ATR.

Por que a proteção combina pontos e ATR:
    o piso de 275 pontos evita reagir a ruído normal; a parcela de 0,25 ATR
    torna o limite mais conservador quando a volatilidade estiver elevada.

Importante sobre o horário:
    a avaliação ocorre no fechamento do candle de 15 minutos. Assim, o candle
    rotulado 17:15 normalmente produz uma decisão por volta das 17:30.

Instalação:
    estrategia/saida/saida_chatgpt_v3.py

Este arquivo é CANDIDATO. Não substituir o titular antes de executar
classificacao.py no histórico oficial atualizado.
"""

from datetime import datetime
from math import isfinite


NOME = "saida_chatgpt_v3"
HORARIO_INICIO_PROTECAO = "17:15"
PERDA_MINIMA_PONTOS = 275.0
MULTIPLICADOR_ATR = 0.25


def _numero_finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _horario(row):
    valor = row.get("dt")
    if isinstance(valor, datetime):
        return valor.strftime("%H:%M")
    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except (TypeError, ValueError):
            return None
    return None


def avaliar_saida(row, posicao) -> bool:
    """Solicita somente a interrupção de perda tardia.

    O motor continua verificando stop e alvo antes deste cartucho. Na falta de
    dados válidos, a função falha com segurança e preserva a regra baseline.
    """
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        return False

    if str(posicao.get("lado", "")).upper() not in {"COMPRA", "VENDA"}:
        return False

    horario = _horario(row)
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    candles = _numero_finito(posicao.get("candles_decorridos"))
    atr = _numero_finito(row.get("atr"))
    if horario is None or resultado is None or candles is None or atr is None:
        return False

    if candles < 1 or atr < 0 or horario < HORARIO_INICIO_PROTECAO:
        return False

    limite = max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR * atr)
    return resultado <= -limite


def diagnosticar_saida(row, posicao):
    """Explica a antecipação somente quando a proteção for acionada."""
    if not avaliar_saida(row, posicao):
        return None
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    return (
        "Proteção de fim de pregão acionada: a posição permaneceu negativa "
        f"e atingiu {abs(resultado):.0f} pontos de perda."
    )


__all__ = ["avaliar_saida", "diagnosticar_saida"]
