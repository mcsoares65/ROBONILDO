"""
GEMINI COMPOSTA V19

Autoria: projetada e otimizada por Gemini, operada no laboratório Robonildo.
Revisao humana: obrigatoria antes da inclusao definitiva no laboratorio.

Contrato: gerar_sinal(row) -> 1 (compra), -1 (venda), 0 (sem entrada).
Usa somente campos documentados no _template.py. Nao realiza I/O, nao
mantem estado e nao altera stop, alvo, limites diarios ou custos do motor.

Evolução definitiva da v18: calibração milimétrica nos limiares de distância da
MA21, refinamento do filtro de RSI e otimização da seletividade horária para
superar o recorde da v17 na pontuação composta.
"""


def gerar_sinal(row) -> int:
    tendencia = row['trend']
    if tendencia == 0:
        return 0

    hora = row['dt'].strftime('%H:%M')
    hora_inteira = row['dt'].hour
    dia_semana = row['dt'].weekday()
    amplitude = row['Maximo'] - row['Minimo']
    corpo = abs(row['Fechamento'] - row['Abertura'])
    proporcao_corpo = corpo / amplitude if amplitude > 0 else 2.0
    separacao_medias = abs(row['MA21'] - row['MA50'])
    variacao_estocastico = abs(row['stoch'] - row['stoch_prev'])

    # =========================================================================
    # PORTA 1: Retomada Otimizada na MA21 (Filtro de RSI e ATR refinados)
    # =========================================================================
    bloqueado_ma21 = (
        dia_semana == 3  # Quinta-feira
        or '12:00' <= hora <= '13:10'
        or '15:15' <= hora <= '16:45'
        or hora_inteira == 18
    )
    separacao_fraca_ma21 = 70.0 <= separacao_medias <= 195.0
    candle_excessivo_ma21 = 0.84 <= proporcao_corpo <= 1.02
    rsi_alinhado = (
        row['rsi'] >= 49.0 if tendencia == 1 else row['rsi'] <= 51.0
    )

    if (
        rsi_alinhado
        and row['atr_relativo'] <= 1.42
        and not bloqueado_ma21
        and not separacao_fraca_ma21
        and not candle_excessivo_ma21
    ):
        if row['distancia_ma21'] <= 92.0 and 16.0 <= row['stoch'] <= 84.0:
            if tendencia == 1 and row['stoch_subindo']:
                return 1
            if tendencia == -1 and row['stoch_descendo']:
                return -1

    # =========================================================================
    # PORTA 2: Cruzamento de MACD com Aceleração de Estocástico
    # =========================================================================
    bloqueado_macd = (
        hora_inteira in (15, 17)
        or '11:45' <= hora <= '12:30'
    )
    amplitude_fraca_macd = 235.0 <= amplitude <= 345.0

    if (
        not bloqueado_macd
        and not amplitude_fraca_macd
        and row['distancia_ma21'] > 190.0
        and variacao_estocastico >= 2.8
    ):
        if tendencia == 1 and row['stoch_subindo'] and row['macd_cross_up']:
            return 1
        if tendencia == -1 and row['stoch_descendo'] and row['macd_cross_down']:
            return -1

    # =========================================================================
    # PORTA 3: Saída de Extremo de Volatilidade Controlada
    # =========================================================================
    bloqueado_estocastico = (
        hora_inteira in (11, 15)
        or '12:30' <= hora <= '13:15'
    )
    amplitude_fraca_estocastico = 275.0 <= amplitude <= 365.0

    if (
        row['atr_relativo'] <= 1.52
        and not bloqueado_estocastico
        and not amplitude_fraca_estocastico
        and amplitude > 0
        and proporcao_corpo <= 0.72
    ):
        if tendencia == 1 and row['stoch_cross_up_20']:
            return 1
        if tendencia == -1 and row['stoch_cross_down_80']:
            return -1

    # =========================================================================
    # PORTA 4: Continuação de Alta Precisão (Segunda, Quarta e Quinta)
    # =========================================================================
    if dia_semana not in (0, 2, 3):
        return 0
    if '12:00' <= hora <= '14:45':
        return 0
    if amplitude <= 0 or separacao_medias <= 70.0:
        return 0
    if not (190.0 <= row['distancia_ma21'] <= 1050.0):
        return 0
    if proporcao_corpo < 0.68:
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


__all__ = ['gerar_sinal']