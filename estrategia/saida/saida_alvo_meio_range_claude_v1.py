"""Saída Alvo no Meio do Range — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: LATERAL (preço vai e volta sem sair do lugar).
Ideia única: em mercado lateral o alvo natural é o meio do intervalo. O range é
o dos últimos 12 candles. Stop além da extremidade oposta do range, com folga de
0,25 ATR; alvo = meio do range se ele estiver a pelo menos 1R no lado favorável;
caso contrário 1,55R. Se o range não der um stop coerente para o lado da
posição, usa o stop dos últimos 5 candles. Depois da abertura não faz nada além
do stop e do alvo.

Origem: ideia nova do autor; nenhuma outra saída usa o intervalo de 12 candles; difere de saida_alvo_media_claude_v1 (âncora na MA21, para posição contra esticamento) (Regra 6).
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
NOME = "saida_alvo_meio_range_claude_v1"
CANDLES_RANGE = 12
CANDLES_STOP_ALTERNATIVO = 5
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
    janela = (row.get("ohlc_recentes") or ())[-CANDLES_RANGE:]
    if len(janela) < CANDLES_RANGE:
        raise ValueError("Histórico insuficiente para definir o range.")
    topo = max(float(c["Maximo"]) for c in janela)
    fundo = min(float(c["Minimo"]) for c in janela)
    meio = (topo + fundo) / 2.0
    folga = FOLGA_STOP_ATR * atr
    direcao = 1 if lado == "COMPRA" else -1
    stop = (fundo - folga) if lado == "COMPRA" else (topo + folga)
    risco = (entrada - stop) * direcao
    if risco <= 0:
        stop, risco = _estrutural(row, lado, entrada, CANDLES_STOP_ALTERNATIVO)
        meio = None
    if meio is not None and (meio - entrada) * direcao >= DISTANCIA_MIN_R * risco:
        alvo = meio
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
