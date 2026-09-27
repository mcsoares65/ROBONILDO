"""
GEMINI 3 PORTAS SUPREMA V20
Evolucao otimizada da base chatgpt_3_portas_robusta_v19.
Adiciona confirmacao de RSI neutro na Porta 1 para buscar superar 1152.4 pontos.
"""

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.0


def gerar_sinal(row) -> int:
    tendencia = row['trend']
    if tendencia == 0:
        return 0

    hora = row['dt'].strftime('%H:%M')
    amplitude = row['Maximo'] - row['Minimo']
    corpo = abs(row['Fechamento'] - row['Abertura'])
    separacao_medias = abs(row['MA21'] - row['MA50'])
    variacao_estocastico = abs(row['stoch'] - row['stoch_prev'])

    # Porta 1: Retomada perto da MA21 com filtro adicional de RSI neutro.
    bloqueado_ma21 = (
        row['dt'].weekday() == 3
        or '12:00' <= hora <= '13:15'
        or '15:00' <= hora <= '16:59'
    )
    separacao_fraca_ma21 = 75.0 <= separacao_medias <= 175.0
    
    rsi = row.get('rsi', 50.0)
    rsi_valido = rsi is None or rsi == rsi  # checagem de NaN
    rsi_alinhado = True
    if rsi_valido and rsi is not None:
        rsi_alinhado = (rsi >= 50.0 if tendencia == 1 else rsi <= 50.0)

    if (
        rsi_alinhado
        and not bloqueado_ma21
        and not separacao_fraca_ma21
        and row['atr_relativo'] <= 1.40
        and row['distancia_ma21'] <= MAX_DISTANCIA_MA21
        and STOCH_MIN <= row['stoch'] <= STOCH_MAX
    ):
        if tendencia == 1 and row['stoch_subindo']:
            return 1
        if tendencia == -1 and row['stoch_descendo']:
            return -1

    # Porta 2: Cruzamento MACD confirmado por deslocamento forte do estocastico.
    bloqueado_macd = '11:45' <= hora <= '12:30'
    amplitude_fraca_macd = 240.0 <= amplitude <= 340.0
    if (
        not bloqueado_macd
        and not amplitude_fraca_macd
        and row['distancia_ma21'] > 200.0
        and variacao_estocastico >= VARIACAO_MINIMA_ESTOCASTICO_MACD
    ):
        if tendencia == 1 and row['stoch_subindo'] and row['macd_cross_up']:
            return 1
        if tendencia == -1 and row['stoch_descendo'] and row['macd_cross_down']:
            return -1

    # Porta 3: Saida de extremo do estocastico com corpo controlado.
    bloqueado_estocastico = '12:30' <= hora <= '13:15'
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    if not bloqueado_estocastico and not amplitude_fraca_estocastico:
        if amplitude > 0 and corpo <= 0.70 * amplitude:
            if tendencia == 1 and row['stoch_cross_up_20']:
                return 1
            if tendencia == -1 and row['stoch_cross_down_80']:
                return -1

    return 0


__all__ = ['gerar_sinal']