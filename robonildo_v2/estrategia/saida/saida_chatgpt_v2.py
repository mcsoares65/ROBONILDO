"""Cartucho candidato de saída — ChatGPT V2.

Hipótese validada no motor oficial do Robonildo:
    preservar integralmente stop/alvo e não antecipar operações vencedoras;
    depois das 16:30, encerrar somente uma posição que ainda carregue perda
    igual ou superior a 250 pontos no fechamento do candle.

Motivação:
    no fim do pregão resta pouco tempo para uma posição atrasada alcançar o
    alvo de 1,55R. A saída limita a permanência de perdas tardias sem podar a
    cauda positiva que torna a baseline forte.

Instalação:
    estrategia/saida/saida_chatgpt_v2.py

Este arquivo é CANDIDATO. Não substituir o titular antes de executar
classificacao.py no histórico oficial atualizado.
"""

from datetime import datetime
from math import isfinite


NOME = "saida_chatgpt_v2"
HORARIO_INICIO_PROTECAO = "16:30"
PERDA_MAXIMA_TARDIA_PONTOS = 250.0


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
    """Solicita encerramento de perda tardia; caso contrário, mantém baseline.

    O motor continua verificando stop e alvo antes deste cartucho. A decisão
    ocorre apenas no fechamento do candle de 15 minutos.
    """
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        return False

    if str(posicao.get("lado", "")).upper() not in {"COMPRA", "VENDA"}:
        return False

    horario = _horario(row)
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    candles = _numero_finito(posicao.get("candles_decorridos"))
    if horario is None or resultado is None or candles is None:
        return False

    if candles < 1 or horario < HORARIO_INICIO_PROTECAO:
        return False

    return resultado <= -PERDA_MAXIMA_TARDIA_PONTOS


def diagnosticar_saida(row, posicao):
    """Explicação opcional para a interface, somente quando houver saída."""
    if not avaliar_saida(row, posicao):
        return None
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    return (
        "Proteção de fim de pregão acionada: a posição permaneceu negativa "
        f"após as 16h30 e atingiu {abs(resultado):.0f} pontos de perda."
    )


__all__ = ["avaliar_saida", "diagnosticar_saida"]
