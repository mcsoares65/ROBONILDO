"""Saída Alvo na Média — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: ESTICADO (preço a 2 ATR ou mais da MA21).
Ideia única: quando o preço está longe da MA21 e a posição aponta para ela, o alvo
natural é a própria média. Stop no extremo dos últimos 3 candles mais 0,25 ATR;
alvo = MA21 se ela estiver a pelo menos 1R de distância no lado favorável; caso
contrário, 1,55R (mesma relação do esqueleto das demais saídas). Depois da
abertura não faz nada além do stop e do alvo.

Origem: ideia nova do autor; nenhuma outra saída ancora o alvo na MA21 (saida_alvo_tendencia_forte e saida_alvo_risco_baixo apenas variam a relação risco/retorno) (Regra 6).
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
NOME = "saida_alvo_media_v01"
CANDLES_STOP = 3
FOLGA_STOP_ATR = 0.25
DISTANCIA_MIN_R = 1.0
RELACAO_RISCO_RETORNO = 1.55


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
    stop_base, _ = _estrutural(row, lado, entrada, CANDLES_STOP)
    folga = FOLGA_STOP_ATR * atr
    stop = stop_base - folga if lado == "COMPRA" else stop_base + folga
    risco = abs(entrada - stop)
    ma21 = _numero(row.get("MA21"))
    direcao = 1 if lado == "COMPRA" else -1
    if ma21 is not None and (ma21 - entrada) * direcao >= DISTANCIA_MIN_R * risco:
        alvo = ma21
    else:
        alvo = entrada + direcao * RELACAO_RISCO_RETORNO * risco
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
