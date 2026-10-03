"""Saída Stop Limitado por ATR — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Limita o stop estrutural a no máximo 1,80 ATR de distância. O alvo continua
sendo 1,55R calculado sobre o risco estrutural original. Depois da abertura não
faz nada além do stop e do alvo.

Abertura: stop = menor entre o estrutural de 5 candles e 1,80 ATR; alvo de 1,55R sobre o risco estrutural.

Origem: abertura de saida_manus_v1 (autoria Manus). Extração LITERAL da regra; nenhum limiar foi alterado.
Isola uma única regra que hoje só existe combinada com outras (Regra 6: não
duplica arquivo existente, pois nenhum outro cartucho traz esta regra sozinha
sobre o esqueleto de abertura).
Variações testadas antes desta versão (Regra 11.2): nenhuma.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato S001: avaliar_saida(row, posicao) -> dict. Único responsável pelo stop
e pelo alvo desde a abertura (Regra 1). Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3): as constantes abaixo são cópias.
"""

from datetime import datetime
from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_stop_atr_claude_v1"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
RISCO_MAXIMO_ATR = 1.80


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
        risco_estrutural = entrada - stop_estrutural
    elif lado == "VENDA":
        stop_estrutural = max(float(c["Maximo"]) for c in janela)
        risco_estrutural = stop_estrutural - entrada
    else:
        raise ValueError(f"Lado inválido: {lado}")
    if risco_estrutural <= 0 or not isfinite(stop_estrutural):
        raise ValueError(f"Proteção inicial inválida para {lado}.")

    # Sem ATR válido, preserva o stop estrutural (nunca falha por indicador).
    atr = _numero(row.get("atr"))
    risco_stop = risco_estrutural
    if atr is not None and atr > 0:
        risco_stop = min(risco_estrutural, RISCO_MAXIMO_ATR * atr)

    # O alvo usa o risco estrutural ORIGINAL: o limitador reduz só a cauda de perda.
    if lado == "COMPRA":
        stop = entrada - risco_stop
        alvo = entrada + RELACAO_RISCO_RETORNO * risco_estrutural
    else:
        stop = entrada + risco_stop
        alvo = entrada - RELACAO_RISCO_RETORNO * risco_estrutural
    if not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Níveis iniciais inválidos para {lado}.")
    return stop, alvo


def _deve_fechar(row, posicao):
    return False


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    candles = _numero(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {"fechar": bool(_deve_fechar(row, posicao)),
            "novo_stop": None, "novo_alvo": None}


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida"]
