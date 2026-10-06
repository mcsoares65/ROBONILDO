"""
saida_macd_contrario_v01.py — MACD contrário em lucro (migrado V445).

Autoria original: Claude (Anthropic).
Migração Regra 1 v10: stop estrutural + RR 1,55 na abertura.

Lógica original (após abertura):
  Se lucro flutuante >= 250 pts e MACD cruza contra a posição → fecha.

Contrato: avaliar_saida(row, posicao) -> dict
Sem I/O, sem estado, sem imports do projeto.
"""

from __future__ import annotations

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
LIMIAR_LUCRO_MINIMO_PONTOS = 250.0


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


def _deve_fechar(row, posicao) -> bool:
    if posicao.get("resultado_flutuante_pts", 0.0) < LIMIAR_LUCRO_MINIMO_PONTOS:
        return False
    if posicao.get("lado") == "COMPRA":
        return bool(row.get("macd_cross_down"))
    return bool(row.get("macd_cross_up"))


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
    return (
        f"MACD contrário em lucro ({posicao.get('resultado_flutuante_pts', 0):.0f} pts "
        f">= {LIMIAR_LUCRO_MINIMO_PONTOS:.0f}) — trava ganho antes do alvo."
    )


__all__ = ["avaliar_saida", "diagnosticar_saida"]
