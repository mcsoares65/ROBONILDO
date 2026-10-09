"""Saída baseline compatível com o contrato S001 do motor V445.

Reproduz a antiga proteção estrutural do Robonildo: stop no extremo dos
últimos cinco candles e alvo fixo de 1,55 vez o risco. Depois da abertura não
antecipa nem reconfigura a operação.

TITULAR DE SAÍDA desde a V504 (pedido do dono, 07/10/2026): operação que corre em
prejuízo NÃO é cortada por horário (sem as regras de 17h15 e 18h da
saida_protecao_encerramento_v02). Só fecham: stop, alvo e o corte absoluto do motor
(HORARIO_LIMITE_ABSOLUTO 18:20:58, CORTE_SEGURANCA_LIMITE).
"""

from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_baseline"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55


def _protecao_inicial(row: dict, posicao: dict) -> tuple[float, float]:
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


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")

    if int(posicao.get("candles_decorridos", 0)) == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
