"""Saída Alvo Estendido em Risco Baixo — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Stop estrutural de 5 candles. O alvo sobe de 1,55R para 1,80R quando o risco
estrutural é curto (menor que 1,50 ATR). Depois da abertura não faz nada além do
stop e do alvo.

Abertura: stop estrutural de 5 candles; alvo 1,80R se risco < 1,50 ATR, senão 1,55R.

Origem: alvo de saida_alvo_risco_curto_v01 (autoria Manus). Extração LITERAL da regra; nenhum limiar foi alterado.
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
NOME = "saida_alvo_risco_baixo_v01"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
RELACAO_RISCO_RETORNO_RISCO_CURTO = 1.80
LIMITE_RISCO_CURTO_ATR = 1.50


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


def _relacao_alvo(row, risco):
    """Sem ATR válido, preserva exatamente a relação base de 1,55R."""
    atr = _numero(row.get("atr"))
    if atr is None or atr <= 0:
        return RELACAO_RISCO_RETORNO
    if risco < LIMITE_RISCO_CURTO_ATR * atr:
        return RELACAO_RISCO_RETORNO_RISCO_CURTO
    return RELACAO_RISCO_RETORNO

def _protecao_inicial(row, posicao):
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")

    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop
        alvo = entrada + _relacao_alvo(row, risco) * risco
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
        risco = stop - entrada
        alvo = entrada - _relacao_alvo(row, risco) * risco
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if risco <= 0 or not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Proteção inicial inválida para {lado}.")
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
