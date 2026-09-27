"""
saida_gemini_v06.py — RSI/stoch + trailing MFE (migrado V445).

Autoria original: Gemini.
Migração Regra 1 v10: stop estrutural + RR 1,55 na abertura.
Corrigido: lado "COMPRA"/"VENDA"; trailing usa MFE em pontos (não preço).

Lógica original (após abertura):
  1. Lucro >= 200 + fadiga RSI/stoch
  2. Giveback de MFE alta
  3. Exaustão RSI em trades longos

Contrato: avaliar_saida(row, posicao) -> dict
Sem I/O, sem estado, sem imports do projeto.
"""

from __future__ import annotations

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55


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


def _eh_compra(lado) -> bool:
    s = str(lado or "").strip().upper()
    return s in ("COMPRA", "COMPRADO", "LONG", "C", "BUY", "B", "1")


def _mfe_pts(posicao) -> float:
    entrada = float(posicao.get("entrada") or 0.0)
    if _eh_compra(posicao.get("lado")):
        return max(0.0, float(posicao.get("maxima_desde_entrada") or entrada) - entrada)
    return max(0.0, entrada - float(posicao.get("minima_desde_entrada") or entrada))


def _deve_fechar(row, posicao) -> bool:
    resultado_pts = float(posicao.get("resultado_flutuante_pts") or 0.0)
    candles = int(posicao.get("candles_decorridos") or 0)
    compra = _eh_compra(posicao.get("lado"))

    rsi = row.get("rsi", 50.0)
    stoch = row.get("stoch", 50.0)
    try:
        rsi = float(rsi)
        stoch = float(stoch)
    except (TypeError, ValueError):
        rsi, stoch = 50.0, 50.0

    if resultado_pts >= 200.0 and candles > 0:
        if compra and (rsi > 74 or stoch < 55):
            return True
        if (not compra) and (rsi < 26 or stoch > 45):
            return True

    mfe = _mfe_pts(posicao)
    if mfe >= 300.0 and resultado_pts < mfe * 0.55:
        return True

    if candles > 6 and resultado_pts > 100.0:
        if compra and rsi > 82:
            return True
        if (not compra) and rsi < 18:
            return True

    return False


def avaliar_saida(row, posicao) -> dict:
    if posicao.get("candles_decorridos", 0) == 0:
        stop, alvo = _stop_alvo_inicial(row, posicao["entrada"], posicao["lado"])
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {
        "fechar": _deve_fechar(row, posicao),
        "novo_stop": None,
        "novo_alvo": None,
    }


def diagnosticar_saida(row, posicao):
    if not _deve_fechar(row, posicao):
        return None
    pts = posicao.get("resultado_flutuante_pts", 0.0)
    mfe = _mfe_pts(posicao)
    return f"Gemini v06: saída (pts={pts:.0f}, MFE={mfe:.0f})"


__all__ = ["avaliar_saida", "diagnosticar_saida"]
