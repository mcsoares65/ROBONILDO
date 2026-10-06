"""Saída Stop Limitado por ATR com Alvo na MA21 — v01.

Abertura: stop estrutural dos últimos 5 candles, limitado a 1,80 ATR; alvo na própria MA21 quando ela
está a pelo menos 1R (do risco estrutural original) do preço de entrada no lado favorável, senão
1,55R sobre o risco estrutural. O alvo depende do risco do stop (regras encadeadas, um funil só).
Depois da abertura não faz nada além do stop e do alvo.
Origem: `saida_composta_stop_atr_alvo_ma21_v01` sem o corte das 18h (que é a regra de `saida_corte_18h_v01`).

Autoria: extração literal por Claude (Anthropic), a pedido do dono do laboratório (Regra 16,
saídas). Revisão humana antes do teste oficial: pendente. O `v0N` é a versão da estratégia, não a
VERSAO do projeto. Nenhum limiar foi alterado; o que sai do arquivo de origem é só a(s) outra(s)
regra(s) de encerramento solta(s). Variações testadas antes desta versão (Regra 11.2): nenhuma.
Sem dependência de data, evento ou preço absoluto (Regra 11.3). Resultado financeiro: ainda não
medido por esta versão; rodar `classificacao.py` (Regra 12).
"""

from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_stop_atr_alvo_ma21_v01"
CANDLES_ESTRUTURA = 5            # saida_stop_atr: 4 de recuo + candle atual
RISCO_MAXIMO_ATR = 1.80          # saida_stop_atr
RELACAO_RISCO_RETORNO = 1.55     # saida_stop_atr / saida_alvo_media
DISTANCIA_MIN_MA21_R = 1.0       # saida_alvo_media


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _protecao_inicial(row, posicao):
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    if lado not in ("COMPRA", "VENDA"):
        raise ValueError(f"Lado inválido: {lado}")
    direcao = 1 if lado == "COMPRA" else -1

    janela = (row.get("ohlc_recentes") or ())[-CANDLES_ESTRUTURA:]
    if len(janela) < CANDLES_ESTRUTURA:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")
    if direcao == 1:
        stop_estrutural = min(float(c["Minimo"]) for c in janela)
    else:
        stop_estrutural = max(float(c["Maximo"]) for c in janela)
    risco_estrutural = (entrada - stop_estrutural) * direcao
    if risco_estrutural <= 0 or not isfinite(stop_estrutural):
        raise ValueError(f"Proteção inicial inválida para {lado}.")

    # Sem ATR válido preserva o stop estrutural (nunca falha por indicador).
    atr = _numero(row.get("atr"))
    risco = risco_estrutural
    if atr is not None and atr > 0:
        risco = min(risco_estrutural, RISCO_MAXIMO_ATR * atr)
    stop = entrada - direcao * risco

    alvo = entrada + direcao * RELACAO_RISCO_RETORNO * risco_estrutural
    ma21 = _numero(row.get("MA21"))
    if ma21 is not None and (ma21 - entrada) * direcao >= DISTANCIA_MIN_MA21_R * risco:
        alvo = ma21

    if not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Níveis iniciais inválidos para {lado}.")
    return stop, alvo


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    candles = _numero(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida"]
