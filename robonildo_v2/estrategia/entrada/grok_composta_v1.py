"""
estrategias/grok_composta_v1.py

Autoria: Gerada por Grok (xAI) em 19/09/2026.
Dataset de validação local: 02/01/2025 a 18/09/2026 (16251 candles).
MIN_RR do motor: 1.55.
Sem revisão humana prévia.

Base: estrutura da chatgpt_4_portas_composta_v16 com ajuste fino
na proporção mínima de corpo da Porta 4 (0.72 em vez de 0.70).
Objetivo: maximizar Pontuação Composta.
"""

def gerar_sinal(row) -> int:
    tendencia = row['trend']
    if tendencia == 0:
        return 0

    hora = row['dt'].strftime('%H:%M')
    amplitude = row['Maximo'] - row['Minimo']
    corpo = abs(row['Fechamento'] - row['Abertura'])
    proporcao_corpo = corpo / amplitude if amplitude > 0 else 2.0
    separacao_medias = abs(row['MA21'] - row['MA50'])
    variacao_estocastico = abs(row['stoch'] - row['stoch_prev'])

    # Porta 1
    bloqueado_ma21 = (
        row['dt'].weekday() == 3
        or '12:00' <= hora <= '13:15'
        or '15:00' <= hora <= '16:59'
    )
    separacao_fraca_ma21 = 75.0 <= separacao_medias <= 200.0
    candle_excessivo_ma21 = 0.85 <= proporcao_corpo <= 1.01
    if not bloqueado_ma21 and not separacao_fraca_ma21 and not candle_excessivo_ma21:
        if row['distancia_ma21'] <= 90.0 and 16.5 <= row['stoch'] <= 83.5:
            if tendencia == 1 and row['stoch_subindo']:
                return 1
            if tendencia == -1 and row['stoch_descendo']:
                return -1

    # Porta 2
    bloqueado_macd = '11:45' <= hora <= '12:30'
    amplitude_fraca_macd = 240.0 <= amplitude <= 340.0
    if (
        not bloqueado_macd
        and not amplitude_fraca_macd
        and row['distancia_ma21'] > 200.0
        and variacao_estocastico >= 3.0
    ):
        if tendencia == 1 and row['stoch_subindo'] and row['macd_cross_up']:
            return 1
        if tendencia == -1 and row['stoch_descendo'] and row['macd_cross_down']:
            return -1

    # Porta 3
    bloqueado_estocastico = (
        '11:00' <= hora <= '11:59'
        or '12:30' <= hora <= '13:15'
    )
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    corpo_fraco_estocastico = 0.55 <= proporcao_corpo <= 0.625
    if (
        not bloqueado_estocastico
        and not amplitude_fraca_estocastico
        and not corpo_fraco_estocastico
        and amplitude > 0
        and proporcao_corpo <= 0.70
    ):
        if tendencia == 1 and row['stoch_cross_up_20']:
            return 1
        if tendencia == -1 and row['stoch_cross_down_80']:
            return -1

    # Porta 4
    if row['dt'].weekday() not in (0, 2, 3):
        return 0
    if '12:00' <= hora <= '14:59':
        return 0
    if amplitude <= 0 or separacao_medias <= 75.0:
        return 0
    if not (200.0 <= row['distancia_ma21'] <= 1000.0):
        return 0
    if proporcao_corpo < 0.72:          # ajuste vs v16 (era 0.70)
        return 0

    candle_alinhado = (row['Fechamento'] - row['Abertura']) * tendencia > 0
    macd_alinhado = (row['macd'] - row['macd_signal']) * tendencia > 0
    if not candle_alinhado or not macd_alinhado:
        return 0

    if tendencia == 1 and row['stoch_subindo']:
        return 1
    if tendencia == -1 and row['stoch_descendo']:
        return -1
    return 0
