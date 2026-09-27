"""
MANUS_HIBRIDA_V8 — retomada da MA21 com confirmacao alternativa pelo MACD.

Autoria: estrategia gerada por Manus AI, operada pelo usuario do laboratorio.
Revisao humana: obrigatoria antes da importacao e execucao.

Declaracao de conformidade:
    - respeita gerar_sinal(row) -> int;
    - usa apenas campos documentados em _template.py;
    - nao realiza I/O, rede ou acesso a arquivos;
    - nao mantem estado global;
    - deixa stop, alvo, limites, horarios e custos para o motor_backtest.py.
"""


def gerar_sinal(row) -> int:
    """Retorna 1 para compra, -1 para venda ou 0 sem entrada."""
    tendencia = row['trend']
    if tendencia == 0:
        return 0

    hora = row['dt'].strftime('%H:%M')
    amplitude = row['Maximo'] - row['Minimo']

    # Ramo principal: retomada da tendencia perto da MA21.
    bloqueio_v7 = (
        row['dt'].day_name() == 'Thursday'
        or '12:00' <= hora <= '13:30'
        or '15:00' <= hora <= '16:59'
    )

    if not bloqueio_v7 and amplitude > 0:
        distancia_maxima = 110 if tendencia == 1 else 90
        corpo_relativo = abs(row['Fechamento'] - row['Abertura']) / amplitude

        if (
            row['distancia_ma21'] <= distancia_maxima
            and corpo_relativo <= 0.775
        ):
            if tendencia == 1 and row['stoch_subindo']:
                return 1
            if tendencia == -1 and row['stoch_descendo']:
                return -1

    # Ramo complementar: confluencia simultanea entre tendencia,
    # direcao do estocastico e cruzamento do MACD.
    if tendencia == 1 and row['stoch_subindo'] and row['macd_cross_up']:
        return 1
    if tendencia == -1 and row['stoch_descendo'] and row['macd_cross_down']:
        return -1

    return 0
