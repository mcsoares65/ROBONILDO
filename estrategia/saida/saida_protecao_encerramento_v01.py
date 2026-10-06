"""ChatGPT V3 migrada para o contrato S001 do motor V445.

Mantém a proteção baseline (stop estrutural + alvo 1,55R). A partir do candle
rotulado 17h15, encerra uma perda que alcance o maior valor entre 275 pontos
e 0,25 ATR. Não utiliza breakeven, trailing ou giveback.
"""

from datetime import datetime
from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_protecao_encerramento_v01"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
HORARIO_INICIO_PROTECAO = "17:15"
PERDA_MINIMA_PONTOS = 275.0
MULTIPLICADOR_ATR = 0.25


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

    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    horario = _horario(row)
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    atr = _numero_finito(row.get("atr"))
    fechar = False
    if (
        horario is not None
        and resultado is not None
        and atr is not None
        and atr >= 0
        and horario >= HORARIO_INICIO_PROTECAO
    ):
        limite = max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR * atr)
        fechar = resultado <= -limite

    return {"fechar": bool(fechar), "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    decisao = avaliar_saida(row, posicao)
    if not decisao["fechar"]:
        return None
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    return (
        "Proteção de fim de pregão acionada: a posição permaneceu negativa "
        f"e atingiu {abs(resultado):.0f} pontos de perda."
    )


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
