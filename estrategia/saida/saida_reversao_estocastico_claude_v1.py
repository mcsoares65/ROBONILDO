"""Saída Reversão do Estocástico — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Com a posição no lucro, encerra quando o estocástico sai da zona extrema contra
a posição (cruza 80 para baixo na compra, 20 para cima na venda). Em prejuízo
não age: quem protege é o stop.

Abertura (esqueleto): stop estrutural dos últimos 5 candles e alvo de 1,55R, idênticos aos da saida_chatgpt_v4. Depois da abertura, SÓ a regra desta candidata age.

Origem: gatilho de reversão de saida_claude_v6. Extração LITERAL da regra; nenhum limiar foi alterado.
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
NOME = "saida_reversao_estocastico_claude_v1"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55


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


def _deve_fechar(row, posicao):
    resultado = _numero(posicao.get("resultado_flutuante_pts"))
    if resultado is None or resultado <= 0:
        return False
    lado = str(posicao["lado"]).upper()
    if lado == "COMPRA":
        return bool(row.get("stoch_cross_down_80"))
    return bool(row.get("stoch_cross_up_20"))


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
