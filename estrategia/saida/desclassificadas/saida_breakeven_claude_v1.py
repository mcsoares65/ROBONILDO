"""Saída Breakeven — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: FIM DE TARDE (a partir das 16:30).
Ideia única: proteger o ganho quando o tempo é curto. Abertura igual ao esqueleto
das demais saídas (stop no extremo dos últimos 5 candles, alvo 1,55R). Depois da
abertura, assim que o preço anda 1,0 ATR a favor (máxima desde a entrada na
compra, mínima na venda), leva o stop para o preço de entrada. O stop só passa a
ser tocado se o preço devolver todo o ganho; nunca afrouxa (o breakeven é mais
apertado que o stop inicial).

Origem: ideia nova do autor; nenhuma outra saída move o stop para o preço de entrada; saida_giveback_claude_v1 fecha a posição, não move o stop (Regra 6).
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
NOME = "saida_breakeven_claude_v1"
CANDLES_STOP = 5
RELACAO_RISCO_RETORNO = 1.55
GATILHO_ATR = 1.0


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
    stop, risco = _estrutural(row, lado, entrada, CANDLES_STOP)
    alvo = entrada + RELACAO_RISCO_RETORNO * risco if lado == "COMPRA" else entrada - RELACAO_RISCO_RETORNO * risco
    if not isfinite(alvo):
        raise ValueError(f"Níveis iniciais inválidos para {lado}.")
    return stop, alvo


def _depois_da_abertura(row, posicao):
    atr = _numero(row.get("atr"))
    entrada = _numero(posicao.get("entrada"))
    if atr is None or atr <= 0 or entrada is None:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}
    if str(posicao["lado"]).upper() == "COMPRA":
        melhor = _numero(posicao.get("maxima_desde_entrada"))
        protegido = melhor is not None and melhor - entrada >= GATILHO_ATR * atr
    else:
        melhor = _numero(posicao.get("minima_desde_entrada"))
        protegido = melhor is not None and entrada - melhor >= GATILHO_ATR * atr
    return {"fechar": False, "novo_stop": entrada if protegido else None, "novo_alvo": None}


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
