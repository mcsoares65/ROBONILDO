"""
estrategias/grok_assault_v1.py

Autoria: Gerada por Grok (xAI) em 19/09/2026.
Estratégia original.
Dataset de validação local: 02/01/2025 a 18/09/2026.
Sem revisão humana prévia.

Objetivo: superar o resultado financeiro do atual líder
(PROG_GPT_5_6_4_PORTAS_V5 ~ R$ 18.691) mantendo pontuação competitiva.
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

    # PORTA 1 — Pullback
    bloqueado = (
        dia == 3
        or '12:00' <= hora <= '13:15'
        or '15:00' <= hora <= '16:59'
    )
    if (
        not bloqueado
        and not (75.0 <= separacao <= 275.0)
        and not (0.85 <= corpo_pct <= 1.01)
        and row['distancia_ma21'] <= 92.0
        and 16.0 <= row['stoch'] <= 84.0
    ):
        if tendencia == 1 and row['stoch_subindo']:
            return 1
        if tendencia == -1 and row['stoch_descendo']:
            return -1

    # PORTA 2 — MACD
    if (
        not ('11:45' <= hora <= '12:30')
        and not (240.0 <= amplitude <= 340.0)
        and row['distancia_ma21'] > 195.0
        and delta_stoch >= 2.9
    ):
        if tendencia == 1 and row['stoch_subindo'] and row['macd_cross_up']:
            return 1
        if tendencia == -1 and row['stoch_descendo'] and row['macd_cross_down']:
            return -1

    # PORTA 3 — Extremo
    if (
        not ('12:30' <= hora <= '13:15')
        and not (279.0 <= amplitude <= 360.0)
        and not (0.55 <= corpo_pct <= 0.625)
        and corpo_pct <= 0.71
    ):
        if tendencia == 1 and row['stoch_cross_up_20']:
            return 1
        if tendencia == -1 and row['stoch_cross_down_80']:
            return -1

    # PORTA 4 — Continuação
    if dia == 4:
        return 0
    if '12:00' <= hora <= '14:59':
        return 0
    if separacao <= 70.0:
        return 0
    if not (195.0 <= row['distancia_ma21'] <= 1050.0):
        return 0
    if not candle_alinhado or not macd_alinhado:
        return 0

    if corpo_pct >= 0.64:
        if tendencia == 1 and row['stoch_subindo']:
            return 1
        if tendencia == -1 and row['stoch_descendo']:
            return -1

    if not (0.58 <= corpo_pct < 0.64):
        return 0
    if separacao < 140.0:
        return 0
    if delta_stoch < 3.5:
        return 0
    if row['atr_relativo'] > 1.40:
        return 0

    if tendencia == 1:
        if not row['stoch_subindo'] or row['stoch'] >= 90:
            return 0
        if row['rsi'] < 50 or not row['rsi_subindo']:
            return 0
        return 1

    if tendencia == -1:
        if not row['stoch_descendo'] or row['stoch'] <= 10:
            return 0
        if row['rsi'] > 50 or not row['rsi_descendo']:
            return 0
        return -1

    return 0
