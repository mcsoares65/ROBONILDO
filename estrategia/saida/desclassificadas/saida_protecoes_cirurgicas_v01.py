# DESCLASSIFICADA pela Regra 16 (V496): regras de encerramento soltas no mesmo arquivo. Fora do ranking.
# Equivale a: saida_perda_tardia_v01 + saida_perda_final_1700_v01 + saida_desastre_rsi_v01 + saida_giveback_v01. Ver conselho/2026-10-05-AG.txt.
"""
saida_protecoes_cirurgicas_v01.py — proteções cirúrgicas (migrado V445).

Autoria original: DeepSeek.
Migração Regra 1 v10: stop estrutural + RR 1,55 na abertura.

Camadas originais (após abertura):
  1. Disaster: primeiros 3 candles, perda >= 1,2 ATR + RSI extremo contra
  2. Tardia: após 16:30, perda >= 250 pts
  3. Final: após 17:00, perda >= 150 pts
  4. Giveback extremo: pico >= 2,0 ATR e lucro <= 0,15 ATR

Contrato: avaliar_saida(row, posicao) -> dict
Sem I/O, sem estado, sem imports do projeto.
"""

from __future__ import annotations

from math import isfinite

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55

HORARIO_TARDIO = "16:30"
PERDA_TARDIA_PTS = 250.0
HORARIO_FINAL = "17:00"
PERDA_FINAL_PTS = 150.0
CANDLES_DISASTER = 3
MULT_ATR_DISASTER = 1.2
RSI_DISASTER_CONTRA = 30.0
MULT_ATR_GIVEBACK = 2.0
MULT_ATR_GIVEBACK_PISO = 0.15


def _num(x, default=0.0):
    try:
        n = float(x)
        return n if isfinite(n) else default
    except (TypeError, ValueError):
        return default


def _horario(row):
    v = row.get("dt") if isinstance(row, dict) else None
    if v is None:
        return None
    if hasattr(v, "strftime"):
        try:
            return v.strftime("%H:%M")
        except (TypeError, ValueError):
            return None
    return None


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
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        return False
    lado = posicao.get("lado")
    if lado is None:
        return False

    horario = _horario(row)
    flut = _num(posicao.get("resultado_flutuante_pts"), 0.0)
    candles = int(_num(posicao.get("candles_decorridos"), 0))
    entrada = _num(posicao.get("entrada"), 0.0)
    maxima = _num(posicao.get("maxima_desde_entrada"), entrada)
    minima = _num(posicao.get("minima_desde_entrada"), entrada)
    atr = _num(row.get("atr"), 0.0)
    rsi = row.get("rsi")
    comprado = str(lado).upper() in ("COMPRA", "COMPRADO", "LONG", "C", "BUY", "B", "1")

    if horario is not None and horario >= HORARIO_TARDIO and flut <= -PERDA_TARDIA_PTS:
        return True
    if horario is not None and horario >= HORARIO_FINAL and flut <= -PERDA_FINAL_PTS:
        return True
    if atr <= 0.0 or entrada <= 0.0:
        return False

    if candles <= CANDLES_DISASTER and flut <= -MULT_ATR_DISASTER * atr:
        if rsi is not None:
            r = _num(rsi, 50.0)
            if comprado and r <= RSI_DISASTER_CONTRA:
                return True
            if (not comprado) and r >= (100.0 - RSI_DISASTER_CONTRA):
                return True

    if comprado:
        pico = maxima - entrada if maxima > entrada else max(0.0, flut)
    else:
        pico = entrada - minima if minima < entrada else max(0.0, flut)

    if pico >= MULT_ATR_GIVEBACK * atr and 0.0 <= flut <= MULT_ATR_GIVEBACK_PISO * atr:
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
    if _deve_fechar(row, posicao):
        return "saida_protecoes_cirurgicas_v01: fechar_agora"
    return "saida_protecoes_cirurgicas_v01: manter"


__all__ = ["avaliar_saida", "diagnosticar_saida"]
