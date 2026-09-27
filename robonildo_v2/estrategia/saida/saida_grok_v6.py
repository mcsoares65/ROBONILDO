"""
saida_grok_v6.py — trava de lucro no fim do pregão (migrado V445).

Autoria original: Grok (xAI).
Migração Regra 1 v10: stop estrutural + RR 1,55 na abertura (obrigatório).

Ideia original (inalterada após a abertura):
  Depois das 17:30, se lucro flutuante >= 1,0 × ATR, realiza.

Contrato: avaliar_saida(row, posicao) -> dict
Sem I/O, sem estado, sem imports do projeto.

AVISO (Regra 4): benchmarks medidos contra motor pré-V445 (stop no motor)
não valem no motor atual — revalidar em classificacao.py.
"""

from __future__ import annotations

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55

HORA_MINIMA = "17:30"
MIN_FLUT_ATR = 1.0
MIN_CANDLES = 2


def _stop_alvo_inicial(row, entrada, lado):
    ohlc = row.get("ohlc_recentes") or ()
    janela = ohlc[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        return None, None
    if lado == "COMPRA":
        stop = min(c["Minimo"] for c in janela)
        risco = entrada - stop
        if risco <= 0:
            return None, None
        return stop, entrada + RELACAO_RISCO_RETORNO * risco
    stop = max(c["Maximo"] for c in janela)
    risco = stop - entrada
    if risco <= 0:
        return None, None
    return stop, entrada - RELACAO_RISCO_RETORNO * risco


def _deve_travar(row, posicao) -> bool:
    if posicao.get("candles_decorridos", 0) < MIN_CANDLES:
        return False
    atr = row.get("atr")
    if atr is None or atr != atr or atr <= 0:
        return False
    hm = row["dt"].strftime("%H:%M")
    if hm < HORA_MINIMA:
        return False
    return posicao.get("resultado_flutuante_pts", 0.0) >= atr * MIN_FLUT_ATR


def avaliar_saida(row, posicao) -> dict:
    if posicao.get("candles_decorridos", 0) == 0:
        stop, alvo = _stop_alvo_inicial(row, posicao["entrada"], posicao["lado"])
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    return {
        "fechar": _deve_travar(row, posicao),
        "novo_stop": None,
        "novo_alvo": None,
    }


def diagnosticar_saida(row, posicao):
    if posicao.get("candles_decorridos", 0) == 0:
        return "Abertura: stop estrutural + alvo RR 1,55"
    atr = row.get("atr")
    if atr is None or atr != atr or atr <= 0:
        return "ATR inválido"
    if posicao.get("candles_decorridos", 0) < MIN_CANDLES:
        return f"Aguarda {MIN_CANDLES} candles"
    hm = row["dt"].strftime("%H:%M")
    flut = posicao.get("resultado_flutuante_pts", 0.0)
    if hm < HORA_MINIMA:
        return f"Antes de {HORA_MINIMA} — não trava"
    if flut >= atr * MIN_FLUT_ATR:
        return f"TRAVA fim de pregão ({hm}, flut={flut:.0f} >= {MIN_FLUT_ATR} ATR)"
    return f"Após {HORA_MINIMA} mas flut={flut:.0f} < {MIN_FLUT_ATR} ATR"


__all__ = ["avaliar_saida", "diagnosticar_saida"]
