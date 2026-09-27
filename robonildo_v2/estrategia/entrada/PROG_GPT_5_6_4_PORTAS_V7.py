"""
PROG_GPT_5_6_4_PORTAS_V7

Autoria: OpenAI GPT-5.6 Sol.
Status: experimental / nao validada.
Revisao humana obrigatoria.

BASE:
    PROG_GPT_5_6_4_PORTAS_V5

Benchmark atual da V5:
    resultado  = 18.871,76
    drawdown   = -1.925,39
    pontuacao  = 367,7

Hipotese V7:
    Preservar as Portas 1, 2, 3 e 4A.
    Alterar somente a expansao 4B para aumentar sua frequencia
    sem introduzir os filtros da V6.
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
    proporcao_corpo = corpo / amplitude

    separacao = abs(row['MA21'] - row['MA50'])
    delta_stoch = abs(row['stoch'] - row['stoch_prev'])

    candle_alinhado = movimento * tendencia > 0

    macd_alinhado = (
        (row['macd'] - row['macd_signal']) * tendencia > 0
    )


    # ============================================================
    # PORTA 1 — MA21
    # Mantida
    # ============================================================

    bloqueado_ma21 = (
        dia == 3
        or '12:00' <= hora <= '13:15'
        or '15:00' <= hora <= '16:59'
    )

    if (
        not bloqueado_ma21
        and not (75.0 <= separacao <= 275.0)
        and not (0.85 <= proporcao_corpo <= 1.01)
        and row['distancia_ma21'] <= 90.0
        and 16.5 <= row['stoch'] <= 83.5
    ):
        if tendencia == 1 and row['stoch_subindo']:
            return 1

        if tendencia == -1 and row['stoch_descendo']:
            return -1


    # ============================================================
    # PORTA 2 — MACD
    # Mantida
    # ============================================================

    if (
        not ('11:45' <= hora <= '12:30')
        and not (240.0 <= amplitude <= 340.0)
        and row['distancia_ma21'] > 200.0
        and delta_stoch >= 3.0
    ):
        if (
            tendencia == 1
            and row['stoch_subindo']
            and row['macd_cross_up']
        ):
            return 1

        if (
            tendencia == -1
            and row['stoch_descendo']
            and row['macd_cross_down']
        ):
            return -1


    # ============================================================
    # PORTA 3 — EXTREMO ESTOCASTICO
    # Mantida
    # ============================================================

    if (
        not ('12:30' <= hora <= '13:15')
        and not (279.0 <= amplitude <= 360.0)
        and not (0.55 <= proporcao_corpo <= 0.625)
        and proporcao_corpo <= 0.70
    ):
        if tendencia == 1 and row['stoch_cross_up_20']:
            return 1

        if tendencia == -1 and row['stoch_cross_down_80']:
            return -1


    # ============================================================
    # PORTA 4 — CONTINUACAO
    # ============================================================

    if dia == 4:
        return 0

    if '12:00' <= hora <= '14:59':
        return 0

    if separacao <= 75.0:
        return 0

    if not (200.0 <= row['distancia_ma21'] <= 1000.0):
        return 0

    if not candle_alinhado:
        return 0

    if not macd_alinhado:
        return 0


    # ============================================================
    # PORTA 4A — NUCLEO V5
    # Mantida
    # ============================================================

    if proporcao_corpo >= 0.65:

        if tendencia == 1 and row['stoch_subindo']:
            return 1

        if tendencia == -1 and row['stoch_descendo']:
            return -1


    # ============================================================
    # PORTA 4B — V7
    #
    # V5:
    # corpo >= 0.60
    # separacao >= 150
    # delta >= 4.0
    # ATR <= 1.35
    #
    # V7:
    # pequena expansao para tentar capturar mais continuacoes
    # sem modificar o nucleo principal.
    # ============================================================

    if not (0.58 <= proporcao_corpo < 0.65):
        return 0

    if separacao < 125.0:
        return 0

    if delta_stoch < 3.0:
        return 0

    # Continua evitando regime de volatilidade excessiva.
    if row['atr_relativo'] > 1.40:
        return 0


    # ------------------------------------------------------------
    # COMPRA
    # ------------------------------------------------------------

    if tendencia == 1:

        if not row['stoch_subindo']:
            return 0

        if row['stoch'] >= 90.0:
            return 0

        if row['rsi'] < 50.0:
            return 0

        if not row['rsi_subindo']:
            return 0

        return 1


    # ------------------------------------------------------------
    # VENDA
    # ------------------------------------------------------------

    if tendencia == -1:

        if not row['stoch_descendo']:
            return 0

        if row['stoch'] <= 10.0:
            return 0

        if row['rsi'] > 50.0:
            return 0

        if not row['rsi_descendo']:
            return 0

        return -1


    return 0


__all__ = ['gerar_sinal']