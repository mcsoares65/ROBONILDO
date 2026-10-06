"""Saída Perda Leve às 16h30 — v01.

Das 16:30 até antes das 17:15, encerra a posição negativa cuja perda alcance o maior valor entre
80 pontos e 0,20 ATR. Depois das 17:15 esta regra não age (na origem, a partir daí valia outro
corte, que é a regra de `saida_protecao_encerramento_v01`). Abertura: stop estrutural dos
últimos 4 candles e alvo de 1,55R, como as demais saídas.
Origem: primeira camada de `saida_perda_fim_tarde_v01` (que reunia duas regras soltas).

Autoria: extração literal por Claude (Anthropic), a pedido do dono do laboratório (Regra 16,
saídas). Revisão humana antes do teste oficial: pendente. O `v0N` é a versão da estratégia, não a
VERSAO do projeto. Nenhum limiar foi alterado; o que sai do arquivo de origem é só a(s) outra(s)
regra(s) de encerramento solta(s). Variações testadas antes desta versão (Regra 11.2): nenhuma.
Sem dependência de data, evento ou preço absoluto (Regra 11.3). Resultado financeiro: ainda não
medido por esta versão; rodar `classificacao.py` (Regra 12).
"""

from math import isfinite
from datetime import datetime

CONTRATO_SAIDA = "S001"
NOME = "saida_perda_leve_1630_v01"

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55

HORARIO_CORTE_LEVE = "16:30"
PERDA_LEVE_PONTOS = 80.0
MULTIPLICADOR_ATR_LEVE = 0.20

HORARIO_FIM_JANELA = "17:15"  # a partir daqui valia o corte forte da origem, que e outra regra


def _numero_finito(valor):
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


def _protecao_inicial(row: dict, posicao: dict):
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Historico insuficiente para definir a protecao inicial.")

    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
        risco = stop - entrada
        alvo = entrada - RELACAO_RISCO_RETORNO * risco
    else:
        raise ValueError(f"Lado invalido: {lado}")

    if risco <= 0 or not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Protecao inicial invalida para {lado}.")
    return stop, alvo


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionarios.")

    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos invalido.")

    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    atr = _numero_finito(row.get("atr"))
    horario = _horario(row)
    fechar = False

    if (
        horario is not None
        and resultado is not None
        and atr is not None
        and atr >= 0
        and resultado < 0
    ):
        if HORARIO_CORTE_LEVE <= horario < HORARIO_FIM_JANELA:
            limite = max(PERDA_LEVE_PONTOS, MULTIPLICADOR_ATR_LEVE * atr)
            if resultado <= -limite:
                fechar = True

    return {"fechar": bool(fechar), "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    decisao = avaliar_saida(row, posicao)
    if not decisao["fechar"]:
        return None
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    horario = _horario(row) or "?"
    return (
        f"Corte de perda ({horario}): posição negativa em {resultado:.0f} pts."
    )


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
