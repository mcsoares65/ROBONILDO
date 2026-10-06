# DESCLASSIFICADA pela Regra 16 (V493): agregador de ideias por OU (portas 1 e 2 repetem o grok_3).
# A parte nova (vetos da porta 3) foi isolada em entrada_saida_extremo_v02. Ver conselho/2026-10-05-AE.txt.
"""Entrada Regime 04 V6 — V5 + veto temporalmente validado na Saída de Extremo.

BASE
----
Parte da entrada_regime_04_v5 e preserva integralmente as portas
Retomada MA21 e MACD + Estocástico.

NOVO VETO
----------
Na porta Saída de Extremo, além do veto V5, bloqueia sinais quando:

1) o estocástico quase não havia penetrado na região extrema antes de cruzar;
2) o mercado já percorreu um range amplo nos 5 candles anteriores.

Interpretação:
- cruzamento "raso" do extremo;
- contexto prévio já bastante expandido;
- maior risco de ser um falso reset / entrada tardia.

A regra foi escolhida usando a PRIMEIRA metade temporal das 82 operações
da porta e checada separadamente na SEGUNDA metade.

NÃO usa futuro.
NÃO usa resultado futuro.
NÃO usa a data 04/12/2025 como filtro.
"""

from __future__ import annotations

NOME = "entrada_regime_04_v6"
TEST_ONLY = False
LIVE_ALLOWED = False
USES_FUTURE_DATA = False

# V5 congelado
MAX_STOCH_EXIT_FRACO = 6.31
MAX_MA_SEP_ATR_FRACA = 0.40

# Novo veto V6 — congelado após split temporal
MAX_STOCH_EXTREME_DEPTH_RASO = 4.322
MIN_PREV_RANGE5_ATR_EXPANDIDO = 2.66


def _num(v, padrao=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return padrao


def _bars_anteriores(row, n=5):
    ohlc = list(row.get("ohlc_recentes") or ())
    if not ohlc:
        return []

    dt_atual = row.get("dt")
    try:
        if dt_atual is not None and ohlc[-1].get("dt") == dt_atual:
            ohlc = ohlc[:-1]
    except Exception:
        pass

    return ohlc[-n:]


def _prev_range5_atr(row):
    atr = _num(row.get("atr"))
    if atr <= 0:
        return 0.0

    bars = _bars_anteriores(row, 5)
    if len(bars) < 3:
        return 0.0

    hi = max(_num(b.get("Maximo")) for b in bars)
    lo = min(_num(b.get("Minimo")) for b in bars)
    return (hi - lo) / atr


def _stoch_extreme_depth(row, sinal):
    atual = _num(row.get("stoch"))
    anterior = _num(row.get("stoch_prev"))

    if sinal == 1:
        # Compra: cruzou para cima de 20.
        return max(0.0, 20.0 - anterior)

    # Venda: cruzou para baixo de 80.
    return max(0.0, anterior - 80.0)


def _porta_base(row):
    tendencia = row["trend"]
    if tendencia == 0:
        return 0, None

    hora = row["dt"].strftime("%H:%M")
    amplitude = row["Maximo"] - row["Minimo"]
    corpo = abs(row["Fechamento"] - row["Abertura"])
    separacao = abs(row["MA21"] - row["MA50"])
    variacao_stoch = abs(row["stoch"] - row["stoch_prev"])

    direcao_stoch = (
        row["stoch_subindo"] if tendencia == 1
        else row["stoch_descendo"]
    )

    cruzamento_macd = (
        row["macd_cross_up"] if tendencia == 1
        else row["macd_cross_down"]
    )

    cruzamento_extremo = (
        row["stoch_cross_up_20"] if tendencia == 1
        else row["stoch_cross_down_80"]
    )

    direcao = 1 if tendencia == 1 else -1

    # Porta 1 — Retomada MA21
    e1 = (
        not (
            row["dt"].weekday() == 3
            or "12:00" <= hora <= "13:15"
            or "15:00" <= hora <= "16:59"
        )
        and not (75.0 <= separacao <= 175.0)
        and row["atr_relativo"] <= 1.40
    )

    c1 = (
        row["distancia_ma21"] <= 90.0
        and 16.5 <= row["stoch"] <= 83.5
        and direcao_stoch
    )

    if e1 and c1:
        return direcao, "Retomada MA21"

    # Porta 2 — MACD + Estocástico
    e2 = (
        not ("11:45" <= hora <= "12:30")
        and not (240.0 <= amplitude <= 340.0)
    )

    c2 = (
        row["distancia_ma21"] > 200.0
        and variacao_stoch >= 4.5
        and direcao_stoch
        and cruzamento_macd
    )

    if e2 and c2:
        return direcao, "MACD + Estocástico"

    # Porta 3 — Saída de Extremo
    e3 = (
        not ("12:30" <= hora <= "13:15")
        and not (279.0 <= amplitude <= 360.0)
    )

    c3 = (
        amplitude > 0
        and corpo <= 0.70 * amplitude
        and cruzamento_extremo
    )

    if e3 and c3:
        return direcao, "Saída de Extremo"

    return 0, None


def _veto_v5(row):
    atr = _num(row.get("atr"))
    if atr <= 0:
        return False, {}

    stoch_exit_size = abs(
        _num(row.get("stoch")) - _num(row.get("stoch_prev"))
    )

    ma_sep_atr = abs(
        _num(row.get("MA21")) - _num(row.get("MA50"))
    ) / atr

    veto = (
        stoch_exit_size <= MAX_STOCH_EXIT_FRACO
        and ma_sep_atr <= MAX_MA_SEP_ATR_FRACA
    )

    return veto, {
        "stoch_exit_size": stoch_exit_size,
        "ma_sep_atr": ma_sep_atr,
    }


def _veto_v6(row, sinal):
    depth = _stoch_extreme_depth(row, sinal)
    prev_range5_atr = _prev_range5_atr(row)

    veto = (
        depth <= MAX_STOCH_EXTREME_DEPTH_RASO
        and prev_range5_atr >= MIN_PREV_RANGE5_ATR_EXPANDIDO
    )

    return veto, {
        "stoch_extreme_depth": depth,
        "prev_range5_atr": prev_range5_atr,
    }


def gerar_sinal(row) -> int:
    sinal, porta = _porta_base(row)

    if sinal == 0:
        return 0

    # Portas 1 e 2 ficam exatamente como Grok 3.
    if porta != "Saída de Extremo":
        return sinal

    veto5, _ = _veto_v5(row)
    if veto5:
        return 0

    veto6, _ = _veto_v6(row, sinal)
    if veto6:
        return 0

    return sinal


def diagnosticar_sinal(row):
    sinal, porta = _porta_base(row)

    if sinal == 0:
        return {
            "porta": 0,
            "total_portas": 3,
            "estrategia": "Regime 04 V6",
            "lado": "NEUTRA",
            "progresso": 0.0,
            "confirmadas": 0,
            "total": 2,
            "faltantes": ["nenhuma porta Grok-base ativa"],
            "explicacao": "Nenhuma porta-base da Grok está ativa.",
        }

    porta_num = (
        1 if porta == "Retomada MA21"
        else 2 if porta == "MACD + Estocástico"
        else 3
    )

    if porta != "Saída de Extremo":
        return {
            "porta": porta_num,
            "total_portas": 3,
            "estrategia": f"Regime 04 V6 / {porta}",
            "lado": "COMPRA" if sinal == 1 else "VENDA",
            "progresso": 1.0,
            "confirmadas": 2,
            "total": 2,
            "faltantes": [],
            "explicacao": "Porta preservada sem filtro adicional.",
        }

    veto5, d5 = _veto_v5(row)
    veto6, d6 = _veto_v6(row, sinal)

    motivos = []
    if veto5:
        motivos.append(
            "V5: cruzamento fraco + tendência MA fraca"
        )
    if veto6:
        motivos.append(
            "V6: extremo raso + range prévio já expandido"
        )

    veto = veto5 or veto6

    return {
        "porta": 3,
        "total_portas": 3,
        "estrategia": "Regime 04 V6 / Saída de Extremo",
        "lado": "COMPRA" if sinal == 1 else "VENDA",
        "progresso": 0.0 if veto else 1.0,
        "confirmadas": 0 if veto else 2,
        "total": 2,
        "faltantes": motivos,
        "explicacao": (
            f"stoch_exit={d5.get('stoch_exit_size', 0):.2f}; "
            f"MAsep/ATR={d5.get('ma_sep_atr', 0):.2f}; "
            f"depth_extremo={d6.get('stoch_extreme_depth', 0):.2f}; "
            f"range5/ATR={d6.get('prev_range5_atr', 0):.2f}. "
            + (
                "VETADO: " + " | ".join(motivos)
                if veto
                else "Sinal preservado."
            )
        ),
    }


__all__ = ["NOME", "gerar_sinal", "diagnosticar_sinal"]
