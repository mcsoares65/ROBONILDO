"""
CHATGPT COMPOSTA V18

Autoria: gerada por OpenAI Codex, operada por Marcio Soares.
Revisao humana: obrigatoria antes da inclusao definitiva no laboratorio.

Contrato: gerar_sinal(row) -> 1 (compra), -1 (venda), 0 (sem entrada).
Usa apenas campos documentados no _template.py. Nao realiza I/O, nao mantem
estado e nao altera stop, alvo, limites diarios ou custos do motor.

Validacao local no motor oficial com MIN_RR=1.55:
dataset WINFUT 15 min, 02/01/2025 a 18/09/2026, 16.251 candles.
Resultado: R$ 20.584,64; dias operados: 337; drawdown: R$ -754,88;
capital minimo: R$ 910,88; minimo comparado: 2,69;
pontuacao composta oficial: 1.116,0.

Os parametros foram pesquisados nesse historico. A estrategia permanece
experimental e requer teste prospectivo antes de qualquer uso real.
"""


def gerar_sinal(row) -> int:
    tendencia = row['trend']
    if tendencia == 0:
        return 0

    hora = row['dt'].strftime('%H:%M')
    hora_inteira = row['dt'].hour
    amplitude = row['Maximo'] - row['Minimo']
    corpo = abs(row['Fechamento'] - row['Abertura'])
    proporcao_corpo = corpo / amplitude if amplitude > 0 else 2.0
    separacao_medias = abs(row['MA21'] - row['MA50'])
    variacao_estocastico = abs(row['stoch'] - row['stoch_prev'])

    # Porta 1: retomada junto da MA21 com confirmacao de RSI e ATR.
    bloqueado_ma21 = (
        row['dt'].weekday() == 3
        or '12:00' <= hora <= '13:15'
        or '15:00' <= hora <= '16:59'
    )
    separacao_fraca_ma21 = 75.0 <= separacao_medias <= 175.0
    candle_excessivo_ma21 = 0.85 <= proporcao_corpo <= 1.01
    rsi_alinhado = (
        row['rsi'] >= 50.0 if tendencia == 1 else row['rsi'] <= 50.0
    )
    if (
        rsi_alinhado
        and row['atr_relativo'] <= 1.40
        and not bloqueado_ma21
        and not separacao_fraca_ma21
        and not candle_excessivo_ma21
    ):
        if row['distancia_ma21'] <= 90.0 and 16.5 <= row['stoch'] <= 83.5:
            if tendencia == 1 and row['stoch_subindo']:
                return 1
            if tendencia == -1 and row['stoch_descendo']:
                return -1

    # Porta 2: cruzamento de MACD; 15h e 17h ficam fora desta familia.
    bloqueado_macd = (
        hora_inteira in (15, 17)
        or '11:45' <= hora <= '12:30'
    )
    amplitude_fraca_macd = 240.0 <= amplitude <= 340.0
    if (
        not bloqueado_macd
        and not amplitude_fraca_macd
        and row['distancia_ma21'] > 175.0
        and variacao_estocastico >= 3.0
    ):
        if tendencia == 1 and row['stoch_subindo'] and row['macd_cross_up']:
            return 1
        if tendencia == -1 and row['stoch_descendo'] and row['macd_cross_down']:
            return -1

    # Porta 3: saida de extremo em volatilidade controlada.
    bloqueado_estocastico = (
        hora_inteira == 11
        or '12:30' <= hora <= '13:15'
    )
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    corpo_fraco_estocastico = 0.55 <= proporcao_corpo <= 0.625
    if (
        row['atr_relativo'] <= 1.50
        and not bloqueado_estocastico
        and not amplitude_fraca_estocastico
        and not corpo_fraco_estocastico
        and amplitude > 0
        and proporcao_corpo <= 0.70
    ):
        if tendencia == 1 and row['stoch_cross_up_20']:
            return 1
        if tendencia == -1 and row['stoch_cross_down_80']:
            return -1

    # Porta 4: continuacao; terça-feira exige confluencia adicional.
    dia = row['dt'].weekday()
    if dia not in (0, 2, 3):
        if dia != 1:
            return 0
        rsi_extra = (
            row['rsi'] >= 50.0 if tendencia == 1 else row['rsi'] <= 50.0
        )
        if (
            proporcao_corpo < 0.74
            or separacao_medias < 125.0
            or row['atr_relativo'] > 1.30
            or not rsi_extra
        ):
            return 0

    if '12:00' <= hora <= '14:59':
        return 0
    if amplitude <= 0 or separacao_medias <= 75.0:
        return 0
    if not (200.0 <= row['distancia_ma21'] <= 1000.0):
        return 0
    if proporcao_corpo < 0.70:
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
