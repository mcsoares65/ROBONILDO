"""saida_grok_v8.py — baseline + BE conservador + trava fim de pregão

Autoria: Grok (xAI).
Contrato: S001 (motor V445+) — avaliar_saida(row, posicao) -> dict
Sem I/O, sem estado, sem imports do projeto.

Diagnóstico da v7 (queda ~R$5k no ranking):
  BE em 1,0×ATR + giveback de MFE realizaram cedo demais e cortaram
  a expectativa do alvo 1,55R. Drawdown melhorou, lucro piorou.

Esta versão (v8):
  1) Abertura: stop estrutural + alvo RR 1,55 (obrigatório).
  2) Sem giveback (não antecipa vencedores).
  3) Breakeven só com lucro >= 1,5×ATR (mais tarde que a v7).
  4) Trava após 17:30 se flutuante >= 1,0×ATR (protege lucro residual
     sem o corte agressivo de perda da chatgpt_v3 — esse fica a cargo
     do stop estrutural / motor).

Constantes de swing/RR copiadas (Regra 3 — não importar configuracao).

Validar em classificacao.py (modos S e C) antes de qualquer promoção.
"""

from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_grok_v8"

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55

MIN_CANDLES_DISCRICIONARIO = 2
ATR_BE = 1.5
HORA_TRAVA = "17:30"
ATR_TRAVA = 1.0


def _numero_finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _protecao_inicial(row: dict, posicao: dict):
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


def _atr_ok(row: dict):
    atr = _numero_finito(row.get("atr"))
    if atr is None or atr <= 0:
        return None
    return atr


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")

    candles = int(posicao.get("candles_decorridos", 0))

    # 1) Abertura — proteção obrigatória
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    if candles < MIN_CANDLES_DISCRICIONARIO:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    atr = _atr_ok(row)
    if atr is None:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    flutuante = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    entrada = float(posicao["entrada"])

    # 4) Trava fim de pregão — realiza lucro residual
    hm = row["dt"].strftime("%H:%M")
    if hm >= HORA_TRAVA and flutuante >= atr * ATR_TRAVA:
        return {"fechar": True, "novo_stop": None, "novo_alvo": None}

    # 3) Breakeven tardio (não fecha; só aperta risco)
    if flutuante >= atr * ATR_BE:
        return {"fechar": False, "novo_stop": entrada, "novo_alvo": None}

    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    candles = int(posicao.get("candles_decorridos", 0))
    if candles == 0:
        return "Abertura: stop estrutural + alvo RR 1,55"
    atr = _atr_ok(row)
    if atr is None:
        return "ATR inválido — sem ajuste discricionário"
    if candles < MIN_CANDLES_DISCRICIONARIO:
        return f"Aguarda {MIN_CANDLES_DISCRICIONARIO} candles"
    flutuante = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    hm = row["dt"].strftime("%H:%M")
    if hm >= HORA_TRAVA and flutuante >= atr * ATR_TRAVA:
        return (
            f"Trava fim de pregão ({hm}): flut={flutuante:.0f} >= "
            f"{ATR_TRAVA}×ATR"
        )
    if flutuante >= atr * ATR_BE:
        return (
            f"Breakeven armado: flut={flutuante:.0f} >= {ATR_BE}×ATR — "
            f"stop na entrada"
        )
    return f"Mantém níveis | flut={flutuante:.0f} ATR={atr:.0f} {hm}"


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]
