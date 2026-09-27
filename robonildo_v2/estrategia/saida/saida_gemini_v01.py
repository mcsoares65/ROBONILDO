"""
saida_gemini_v01.py — RSI / realização (migrado V445).

Autoria original: Gemini.
Migração Regra 1 v10: stop estrutural + RR 1,55 na abertura.
Corrigido: lado usa "COMPRA"/"VENDA" (motor nunca passa 1/-1 em posicao).

Lógica original (após abertura):
  Lucro >= 250 + RSI extremo, ou RSI de exaustão pura.

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


def _deve_fechar(row, posicao) -> bool:
    resultado_pts = float(posicao.get("resultado_flutuante_pts") or 0.0)
    rsi = row.get("rsi")
    if rsi is None:
        rsi = row.get("RSI", 50.0)
    try:
        rsi = float(rsi)
    except (TypeError, ValueError):
        rsi = 50.0

    compra = _eh_compra(posicao.get("lado"))

    if resultado_pts >= 250.0:
        if compra and rsi > 75:
            return True
        if (not compra) and rsi < 25:
            return True

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
    rsi = row.get("rsi", row.get("RSI", 50.0))
    pts = posicao.get("resultado_flutuante_pts", 0.0)
    return f"Gemini v01: saída por RSI/lucro (pts={pts:.0f}, RSI={rsi:.1f})"


__all__ = ["avaliar_saida", "diagnosticar_saida"]
