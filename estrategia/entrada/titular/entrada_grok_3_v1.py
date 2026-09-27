"""
estrategias/grok_3_portas_robusta_v1.py

Autoria: Gerada por Grok (xAI) em 20/09/2026.
Dataset de validação: 13/03/2026 a 18/09/2026 (4.964 candles).
MIN_RR do motor: 1.55.
Sem revisão humana prévia.

Base: estrutura da chatgpt_3_portas_robusta_v19 com ajuste
na variação mínima do estocástico da Porta 2 (4.5 em vez de 4.0).
"""

def gerar_sinal(row) -> int:
    tendencia = row['trend']
    if tendencia == 0:
        return 0

    hora = row['dt'].strftime('%H:%M')
    amplitude = row['Maximo'] - row['Minimo']
    corpo = abs(row['Fechamento'] - row['Abertura'])
    separacao_medias = abs(row['MA21'] - row['MA50'])
    variacao_estocastico = abs(row['stoch'] - row['stoch_prev'])

    # Porta 1: retomada perto da MA21
    bloqueado_ma21 = (
        row['dt'].weekday() == 3
        or '12:00' <= hora <= '13:15'
        or '15:00' <= hora <= '16:59'
    )
    separacao_fraca_ma21 = 75.0 <= separacao_medias <= 175.0
    if (
        not bloqueado_ma21
        and not separacao_fraca_ma21
        and row['atr_relativo'] <= 1.40
        and row['distancia_ma21'] <= 90.0
        and 16.5 <= row['stoch'] <= 83.5
    ):
        if tendencia == 1 and row['stoch_subindo']:
            return 1
        if tendencia == -1 and row['stoch_descendo']:
            return -1

    # Porta 2: MACD com variação de estocástico >= 4.5
    bloqueado_macd = '11:45' <= hora <= '12:30'
    amplitude_fraca_macd = 240.0 <= amplitude <= 340.0
    if (
        not bloqueado_macd
        and not amplitude_fraca_macd
        and row['distancia_ma21'] > 200.0
        and variacao_estocastico >= 4.5
    ):
        if tendencia == 1 and row['stoch_subindo'] and row['macd_cross_up']:
            return 1
        if tendencia == -1 and row['stoch_descendo'] and row['macd_cross_down']:
            return -1

    # Porta 3: saída de extremo
    bloqueado_estocastico = '12:30' <= hora <= '13:15'
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    if not bloqueado_estocastico and not amplitude_fraca_estocastico:
        if amplitude > 0 and corpo <= 0.70 * amplitude:
            if tendencia == 1 and row['stoch_cross_up_20']:
                return 1
            if tendencia == -1 and row['stoch_cross_down_80']:
                return -1

    return 0
