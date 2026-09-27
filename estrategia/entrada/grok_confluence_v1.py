"""
estrategias/grok_confluence_v1.py

Autoria: Gerada por Grok (xAI) em 19/09/2026.
Estratégia original.
Dataset de validação local: 02/01/2025 a 18/09/2026 (16251 candles).
Sem revisão humana prévia.

Lógica:
- Quatro regimes de entrada com filtros de qualidade cruzados
  (estocástico + MACD + RSI + ATR relativo + estrutura de candle).
- Foco em maximizar a Pontuação Composta:
  (resultado / capital_minimo) * min_comp * sqrt(dias).
- Bloqueios de horário e dia de baixa qualidade.
- Porta 4 exige confluência mais forte (corpo, separação, ATR e RSI).
"""

def gerar_sinal(row) -> int:
    tendencia = row['trend']
    if tendencia == 0:
        return 0

    hora = row['dt'].strftime('%H:%M')
    dia = row['dt'].weekday()
    amplitude = row['Maximo'] - row['Minimo']
    if amplitude <= 0:
        return 0

    movimento = row['Fechamento'] - row['Abertura']
    corpo = abs(movimento)
    corpo_pct = corpo / amplitude
    separacao = abs(row['MA21'] - row['MA50'])
    delta_stoch = abs(row['stoch'] - row['stoch_prev'])
    candle_alinhado = movimento * tendencia > 0
    macd_alinhado = (row['macd'] - row['macd_signal']) * tendencia > 0
    atr_rel = row['atr_relativo']
    rsi = row['rsi']

    # ---------- PORTA 1 — Pullback na MA21 ----------
    bloqueado_p1 = (
        dia == 3
        or '12:00' <= hora <= '13:15'
        or '15:00' <= hora <= '16:59'
    )
    if (
        not bloqueado_p1
        and not (75.0 <= separacao <= 275.0)
        and not (0.85 <= corpo_pct <= 1.01)
        and row['distancia_ma21'] <= 90.0
        and 16.5 <= row['stoch'] <= 83.5
        and amplitude >= 80.0
        and atr_rel <= 1.40
    ):
        if tendencia == 1 and row['stoch_subindo'] and rsi >= 45:
            return 1
        if tendencia == -1 and row['stoch_descendo'] and rsi <= 55:
            return -1

    # ---------- PORTA 2 — MACD cross ----------
    if (
        not ('11:45' <= hora <= '12:30')
        and not (240.0 <= amplitude <= 340.0)
        and row['distancia_ma21'] > 200.0
        and delta_stoch >= 3.0
        and atr_rel <= 1.35
    ):
        if tendencia == 1 and row['stoch_subindo'] and row['macd_cross_up']:
            return 1
        if tendencia == -1 and row['stoch_descendo'] and row['macd_cross_down']:
            return -1

    # ---------- PORTA 3 — Saída de extremo ----------
    if (
        not ('12:30' <= hora <= '13:15')
        and not (279.0 <= amplitude <= 360.0)
        and not (0.55 <= corpo_pct <= 0.625)
        and corpo_pct <= 0.70
        and atr_rel <= 1.40
    ):
        if tendencia == 1 and row['stoch_cross_up_20']:
            return 1
        if tendencia == -1 and row['stoch_cross_down_80']:
            return -1

    # ---------- PORTA 4 — Continuação com confluência ----------
    if dia == 4:
        return 0
    if '12:15' <= hora <= '14:59':
        return 0
    if separacao <= 75.0:
        return 0
    if not (200.0 <= row['distancia_ma21'] <= 1000.0):
        return 0
    if not candle_alinhado or not macd_alinhado:
        return 0

    # 4A — corpo forte
    if corpo_pct >= 0.70:
        if tendencia == 1 and row['stoch_subindo']:
            return 1
        if tendencia == -1 and row['stoch_descendo']:
            return -1

    # 4B — expansão com RSI + ATR
    if not (0.60 <= corpo_pct < 0.70):
        return 0
    if separacao < 140.0:
        return 0
    if delta_stoch < 3.5:
        return 0
    if atr_rel > 1.20:
        return 0

    if tendencia == 1:
        if not row['stoch_subindo'] or row['stoch'] >= 87:
            return 0
        if rsi < 48 or not row['rsi_subindo']:
            return 0
        return 1

    if tendencia == -1:
        if not row['stoch_descendo'] or row['stoch'] <= 13:
            return 0
        if rsi > 52 or not row['rsi_descendo']:
            return 0
        return -1

    return 0
