"""Saída Stop Limitado por ATR com Alvo Forte — v02.

Abertura: stop estrutural dos últimos 4 candles, limitado a 1,80 ATR; alvo de 1,55R sobre o risco
estrutural original, ou 1,70R em tendência forte (separação MA21/MA50 de pelo menos 250 pontos e
ATR relativo até 1,40). Depois da abertura não faz nada além do stop e do alvo.
Origem: `saida_stop_limitado_alvo_forte_v01` (Manus V1) sem o corte de perda tardia das 17:15, que é a
regra de `saida_protecao_encerramento_v01`. O v02 é a mesma ideia de abertura, sem a regra solta.

Autoria: extração literal por Claude (Anthropic), a pedido do dono do laboratório (Regra 16,
saídas). Revisão humana antes do teste oficial: pendente. O `v0N` é a versão da estratégia, não a
VERSAO do projeto. Nenhum limiar foi alterado; o que sai do arquivo de origem é só a(s) outra(s)
regra(s) de encerramento solta(s). Variações testadas antes desta versão (Regra 11.2): nenhuma.
Sem dependência de data, evento ou preço absoluto (Regra 11.3). Resultado financeiro: ainda não
medido por esta versão; rodar `classificacao.py` (Regra 12).
"""

from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_stop_limitado_alvo_forte_v02"

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO_BASE = 1.55
RELACAO_RISCO_RETORNO_FORTE = 1.70
SEPARACAO_TENDENCIA_FORTE = 250.0
ATR_RELATIVO_MAX_TENDENCIA_FORTE = 1.40
RISCO_MAXIMO_ATR = 1.80



def _numero_finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _protecao_inicial(row: dict, posicao: dict) -> tuple[float, float]:
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")

    atr = _numero_finito(row.get("atr"))
    if atr is None or atr <= 0.0:
        raise ValueError("ATR inválido para normalizar o risco inicial.")

    if lado == "COMPRA":
        stop_estrutural = min(float(c["Minimo"]) for c in janela)
        risco_estrutural = entrada - stop_estrutural
    elif lado == "VENDA":
        stop_estrutural = max(float(c["Maximo"]) for c in janela)
        risco_estrutural = stop_estrutural - entrada
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if risco_estrutural <= 0.0 or not isfinite(stop_estrutural):
        raise ValueError(f"Proteção inicial inválida para {lado}.")

    risco_stop = min(risco_estrutural, RISCO_MAXIMO_ATR * atr)
    if lado == "COMPRA":
        stop = entrada - risco_stop
    else:
        stop = entrada + risco_stop

    separacao = abs(float(row["MA21"]) - float(row["MA50"]))
    atr_relativo = _numero_finito(row.get("atr_relativo"))
    tendencia_forte = (
        separacao >= SEPARACAO_TENDENCIA_FORTE
        and atr_relativo is not None
        and atr_relativo <= ATR_RELATIVO_MAX_TENDENCIA_FORTE
    )
    relacao = (
        RELACAO_RISCO_RETORNO_FORTE
        if tendencia_forte
        else RELACAO_RISCO_RETORNO_BASE
    )

    # O alvo usa o risco estrutural original. Assim, o limitador de stop reduz
    # apenas a cauda de perda; não aproxima o alvo-base dos trades existentes.
    if lado == "COMPRA":
        alvo = entrada + relacao * risco_estrutural
    else:
        alvo = entrada - relacao * risco_estrutural

    if not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Níveis iniciais inválidos para {lado}.")
    return stop, alvo


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")

    if int(posicao.get("candles_decorridos", 0)) == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    if int(posicao.get("candles_decorridos", 0)) == 0:
        return "Abertura: stop estrutural limitado a 1,80 ATR e alvo 1,55R/1,70R."
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
