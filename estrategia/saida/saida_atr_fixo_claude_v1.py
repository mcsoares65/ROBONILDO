"""Saída ATR Fixo — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: VOLÁTIL (ATR >= 1,25x a média de 50 candles).
Ideia única: em mercado agitado o stop estrutural de 5 candles fica largo e
imprevisível; aqui o risco é medido pela própria agitação. Stop a 1,2 ATR da
entrada e alvo a 1,8 ATR (relação 1,5). Depois da abertura não faz nada além do
stop e do alvo. Ao contrário da saída titular, não usa nenhum candle anterior.

Origem: ideia nova do autor; difere de saida_stop_atr_claude_v1 (que só LIMITA o stop estrutural a 1,8 ATR e mantém o alvo em 1,55R do risco estrutural): aqui stop e alvo são puramente em ATR (Regra 6).
Variações testadas antes desta versão (Regra 11.2): nenhuma. Limiares fixados
a priori, sem ajuste a histórico.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato S001: avaliar_saida(row, posicao) -> dict. Único responsável pelo stop
e pelo alvo desde a abertura (Regra 1). Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3): as constantes abaixo são cópias.
"""

from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_atr_fixo_claude_v1"
STOP_ATR = 1.20
ALVO_ATR = 1.80


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _atr_valido(row):
    atr = _numero(row.get("atr"))
    if atr is None or atr <= 0:
        raise ValueError("ATR inválido: não há como definir a proteção inicial.")
    return atr


def _estrutural(row, lado, entrada, candles):
    """Stop no extremo dos últimos `candles` candles fechados (lado oposto à posição)."""
    janela = (row.get("ohlc_recentes") or ())[-candles:]
    if len(janela) < candles:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")
    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
        risco = stop - entrada
    else:
        raise ValueError(f"Lado inválido: {lado}")
    if risco <= 0 or not isfinite(stop):
        raise ValueError(f"Proteção inicial inválida para {lado}.")
    return stop, risco


def _protecao_inicial(row, posicao):
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    atr = _atr_valido(row)
    if lado == "COMPRA":
        stop, alvo = entrada - STOP_ATR * atr, entrada + ALVO_ATR * atr
    elif lado == "VENDA":
        stop, alvo = entrada + STOP_ATR * atr, entrada - ALVO_ATR * atr
    else:
        raise ValueError(f"Lado inválido: {lado}")
    if not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Níveis iniciais inválidos para {lado}.")
    return stop, alvo


def _depois_da_abertura(row, posicao):
    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    candles = _numero(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return _depois_da_abertura(row, posicao)


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida"]
