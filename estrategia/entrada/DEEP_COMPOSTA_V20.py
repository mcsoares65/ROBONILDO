"""
DEEP_COMPOSTA_V20 — CHATGPT COMPOSTA V17 + filtro de volume e direcao
de candle na porta 1.

Base direta: CHATGPT COMPOSTA V17 (docstring declara pontuacao 1.088,4
no motor oficial com RR=1.55, dataset 02/01/2025 a 18/09/2026). Portas
2, 3 e 4 identicas ao V17. Unica regiao alterada: porta 1, que recebe
duas condicoes novas.

CORRECAO: usa 'volume_relativo' (ja calculado em indicadores.py) em vez
de 'volume_media_21' (que nao existe no indicadores.py atual - causava
KeyError). volume_relativo = Quantidade / media movel 21 de Quantidade,
entao o teste >= 0.85 e equivalente ao filtro original pretendido.

Condicoes adicionadas (somente na porta 1):
  (a) volume relativo >= 0.85.
  (b) direcao do candle confirma o trade.

Autoria: IA assistente em sessao operada pelo usuario do laboratorio.
Revisao humana: obrigatoria antes de importar e rodar.
Status: candidata - NAO validada.

Contrato: gerar_sinal(row) -> 1 (compra), -1 (venda) ou 0 (sem operacao).
Colunas usadas: dt, trend, MA21, MA50, distancia_ma21, stoch, stoch_prev,
stoch_subindo, stoch_descendo, stoch_cross_up_20, stoch_cross_down_80,
macd, macd_signal, macd_cross_up, macd_cross_down, rsi, atr_relativo,
volume_relativo, Abertura, Fechamento, Maximo, Minimo.
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

    # ============ Porta 1: V17 + volume + direcao de candle ============
    bloqueado_ma21 = (
        row['dt'].weekday() == 3
        or '12:00' <= hora <= '13:15'
        or '15:00' <= hora <= '16:59'
        or hora_inteira == 18
    )
    separacao_fraca_ma21 = 75.0 <= separacao_medias <= 200.0
    candle_excessivo_ma21 = 0.85 <= proporcao_corpo <= 1.01
    rsi_alinhado = (
        row['rsi'] >= 50.0 if tendencia == 1 else row['rsi'] <= 50.0
    )

    vol_rel = row['volume_relativo']
    volume_suficiente = (
        vol_rel is not None and vol_rel == vol_rel and vol_rel >= 0.85
    )

    candle_altista = row['Fechamento'] >= row['Abertura']
    candle_baixista = row['Fechamento'] <= row['Abertura']

    if (
        rsi_alinhado
        and row['atr_relativo'] <= 1.40
        and volume_suficiente
        and not bloqueado_ma21
        and not separacao_fraca_ma21
        and not candle_excessivo_ma21
    ):
        if row['distancia_ma21'] <= 90.0 and 16.5 <= row['stoch'] <= 83.5:
            if tendencia == 1 and row['stoch_subindo'] and candle_altista:
                return 1
            if tendencia == -1 and row['stoch_descendo'] and candle_baixista:
                return -1

    # ============ Porta 2: V17 (inalterada) ============
    bloqueado_macd = (
        hora_inteira in (15, 17)
        or '11:45' <= hora <= '12:30'
    )
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

    # ============ Porta 3: V17 (inalterada) ============
    bloqueado_estocastico = (
        hora_inteira in (11, 15)
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

    # ============ Porta 4: V17 (inalterada) ============
    if row['dt'].weekday() not in (0, 2, 3):
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