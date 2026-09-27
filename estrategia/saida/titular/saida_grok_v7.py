"""
saida_grok_v7.py — proteção progressiva + trava de fim de pregão

Autoria: Grok (xAI).

Contrato (Regra 1 v10 / compliance v8):
    avaliar_saida(row, posicao) -> dict
    Sem I/O, sem estado, sem imports do projeto.

Contexto (motor V445):
    O motor não calcula stop/alvo. Quem define proteção desde a abertura
    é exclusivamente este cartucho. Sem níveis na abertura, a posição
    fica sem stop até o corte 18:20:58 (drawdown tipo -498 observado
    quando cartuchos antigos não migraram).

Camadas (nesta ordem de intenção):
    1) Abertura (candles_decorridos == 0)
       Stop estrutural (janela OHLC) + alvo RR 1,55 — mesma base do
       baseline, obrigatória no motor atual.

    2) Breakeven por ATR
       Se lucro flutuante >= 1,0 × ATR, propõe stop na entrada.
       Não usa o stop atual (posicao pública não expõe stop/alvo).

    3) Giveback de MFE
       Se a máxima excursão favorável (MFE) >= 1,5 × ATR e o lucro
       atual caiu para <= 40% da MFE (ainda > 0), realiza no fechamento.
       Evita devolver a maior parte de um movimento já capturado.

    4) Trava de fim de pregão
       Após 17:30, se lucro flutuante >= 0,8 × ATR, realiza.
       Mesma família da v6, limiar um pouco mais cedo (0,8 vs 1,0)
       para compensar o fato de já existir BE/giveback antes.

Constantes SWING_LOOKBACK_CANDLES e RELACAO_RISCO_RETORNO copiadas de
configuracao.py (Regra 3 — não importar módulos do projeto).

Resultado histórico não garante desempenho futuro. Validar em
classificacao.py (modo S e C) no motor oficial antes de qualquer promoção.
"""

from __future__ import annotations

# --- cópias de configuracao.py (não importar — Regra 3) ---
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55

# --- parâmetros desta versão ---
MIN_CANDLES_DISCRICIONARIO = 2
ATR_BE = 1.0          # flutuante >= 1,0×ATR → stop na entrada
ATR_MFE_MIN = 1.5     # MFE mínima para armar giveback
GIVEBACK_FRAC = 0.40  # realiza se lucro atual <= 40% da MFE
HORA_TRAVA = "17:30"
ATR_TRAVA = 0.8       # após HORA_TRAVA, flutuante >= 0,8×ATR → fecha


def _stop_alvo_inicial(row: dict, entrada: float, lado: str):
    """Stop estrutural + alvo RR — mesma lógica do baseline / motor antigo."""
    ohlc = row.get("ohlc_recentes") or ()
    janela = ohlc[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        return None, None

    if lado == "COMPRA":
        stop = min(c["Minimo"] for c in janela)
        risco = entrada - stop
        if risco <= 0:
            return None, None
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    else:
        stop = max(c["Maximo"] for c in janela)
        risco = stop - entrada
        if risco <= 0:
            return None, None
        alvo = entrada - RELACAO_RISCO_RETORNO * risco

    return stop, alvo


def _mfe_pts(posicao: dict) -> float:
    """Máxima excursão favorável em pontos desde a entrada."""
    entrada = posicao["entrada"]
    if posicao["lado"] == "COMPRA":
        return max(0.0, posicao["maxima_desde_entrada"] - entrada)
    return max(0.0, entrada - posicao["minima_desde_entrada"])


def _atr_ok(row: dict):
    atr = row.get("atr")
    if atr is None or atr != atr or atr <= 0:
        return None
    return atr


def avaliar_saida(row: dict, posicao: dict) -> dict:
    candles = posicao.get("candles_decorridos", 0)
    lado = posicao["lado"]
    entrada = posicao["entrada"]
    flutuante = posicao.get("resultado_flutuante_pts", 0.0)

    # 1) Abertura — proteção obrigatória no motor V445
    if candles == 0:
        stop, alvo = _stop_alvo_inicial(row, entrada, lado)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    # Antes de MIN_CANDLES só mantém o que foi fixado na abertura
    if candles < MIN_CANDLES_DISCRICIONARIO:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    atr = _atr_ok(row)
    if atr is None:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    # 3) Giveback de MFE (antes da trava de horário — captura devolução intraday)
    mfe = _mfe_pts(posicao)
    if (
        mfe >= atr * ATR_MFE_MIN
        and flutuante > 0
        and flutuante <= mfe * GIVEBACK_FRAC
    ):
        return {"fechar": True, "novo_stop": None, "novo_alvo": None}

    # 4) Trava fim de pregão
    hm = row["dt"].strftime("%H:%M")
    if hm >= HORA_TRAVA and flutuante >= atr * ATR_TRAVA:
        return {"fechar": True, "novo_stop": None, "novo_alvo": None}

    # 2) Breakeven: sobe stop para a entrada quando já há lucro relevante
    #    (não fecha; só aperta o risco residual)
    if flutuante >= atr * ATR_BE:
        return {"fechar": False, "novo_stop": entrada, "novo_alvo": None}

    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    """Texto curto para narração / debug — não afeta a decisão."""
    candles = posicao.get("candles_decorridos", 0)
    if candles == 0:
        return "Abertura: definindo stop estrutural + alvo RR 1,55"

    atr = _atr_ok(row)
    if atr is None:
        return "ATR inválido — sem ajuste discricionário"

    if candles < MIN_CANDLES_DISCRICIONARIO:
        return f"Aguarda {MIN_CANDLES_DISCRICIONARIO} candles"

    flutuante = posicao.get("resultado_flutuante_pts", 0.0)
    mfe = _mfe_pts(posicao)
    hm = row["dt"].strftime("%H:%M")

    if (
        mfe >= atr * ATR_MFE_MIN
        and flutuante > 0
        and flutuante <= mfe * GIVEBACK_FRAC
    ):
        return (
            f"Giveback MFE: flut={flutuante:.0f} pts <= {GIVEBACK_FRAC:.0%} "
            f"de MFE={mfe:.0f} (mín {ATR_MFE_MIN}×ATR)"
        )

    if hm >= HORA_TRAVA and flutuante >= atr * ATR_TRAVA:
        return (
            f"Trava fim de pregão ({hm}): flut={flutuante:.0f} >= "
            f"{ATR_TRAVA}×ATR ({atr * ATR_TRAVA:.0f})"
        )

    if flutuante >= atr * ATR_BE:
        return (
            f"Breakeven armado: flut={flutuante:.0f} >= {ATR_BE}×ATR — "
            f"stop proposto na entrada"
        )

    return (
        f"Mantém níveis | flut={flutuante:.0f} MFE={mfe:.0f} "
        f"ATR={atr:.0f} {hm}"
    )


__all__ = ["avaliar_saida", "diagnosticar_saida"]
