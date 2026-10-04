"""Saída Tendência com Trailing — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: TENDÊNCIA (preço andando em linha).
Ideia única: deixar a tendência correr. Abertura: stop no extremo dos últimos 5
candles e SEM alvo. Depois da abertura, a partir do 2º candle, fecha a posição
quando o fechamento devolve 2,0 ATR a partir do melhor preço desde a entrada
(máxima desde a entrada na compra, mínima na venda). Não aperta nem afrouxa o
stop: só pede fechamento no fechamento do candle. Sem alvo, o ganho é limitado
apenas pelo trailing e pelo corte final do pregão.

Origem: ideia nova do autor; nenhuma outra saída trabalha sem alvo com trailing de ATR; saida_giveback_claude_v1 devolve uma fração do ganho já feito e mantém o alvo de 1,55R (Regra 6).
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
NOME = "saida_tendencia_trailing_claude_v1"
CANDLES_STOP = 5
TRAILING_ATR = 2.0
CANDLES_MIN_PARA_TRAILING = 2


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
    stop, _ = _estrutural(row, lado, entrada, CANDLES_STOP)
    return stop, None


def _depois_da_abertura(row, posicao):
    candles = _numero(posicao.get("candles_decorridos")) or 0
    atr = _numero(row.get("atr"))
    fechamento = _numero(row.get("Fechamento"))
    if candles < CANDLES_MIN_PARA_TRAILING or atr is None or atr <= 0 or fechamento is None:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}
    lado = str(posicao["lado"]).upper()
    if lado == "COMPRA":
        melhor = _numero(posicao.get("maxima_desde_entrada"))
        fechar = melhor is not None and fechamento <= melhor - TRAILING_ATR * atr
    else:
        melhor = _numero(posicao.get("minima_desde_entrada"))
        fechar = melhor is not None and fechamento >= melhor + TRAILING_ATR * atr
    return {"fechar": bool(fechar), "novo_stop": None, "novo_alvo": None}


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
