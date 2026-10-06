# DESCLASSIFICADA pela Regra 16 (V490): agregador de ideias por OU. Fora do ranking.
# Ver conselho/2026-10-05-AE.txt. Mantida so como referencia/paridade; nao alterada.
"""
deepseek_3_portas_robusta_v5 — submissao final como concorrente.

Autoria: DeepSeek, em sessao operada por Marcio Soares.

Historico honesto:
  - v2 (RSI>50 + corpo>=30% na Porta 2) MEDIU 986.6. Hipotese rejeitada.
  - v5 (este arquivo) aposta TUDO no padrao que a grok v1 ja provou:
    apertar cada porta NA DIRECAO NATURAL dela aumenta minimo_comparado.
    Grok v1 fez isso so na Porta 2 (4.0 -> 4.5) e saltou de 1152 para 1190.

DUAS MUDANCAS, as duas apertos estruturais, uma por porta:

  MUDANCA 1 — Porta 2, piso da variacao do estocastico: 4.5 -> 5.0.
    Continuacao direta do unico eixo comprovado. Passo de +0.5
    (mesma magnitude relativa do passo grok 4.0->4.5), nao salto
    agressivo. Se a curva 4.0->4.5 nao saturou, 5.0 sobe mais.

  MUDANCA 2 — Porta 1, teto de volatilidade: atr_relativo <= 1.40
    -> <= 1.20. Ataque direto ao drawdown. Em TODAS as versoes
    medidas, drawdown foi fixo em -249.48 — logo vive fora da
    Porta 2 (senao teria mudado na v2). Porta 1 e a candidata.
    Entradas em volatilidade alta = stops mais largos (SWING_LOOKBACK
    pega swing maior em mercado agitado) = drawdown maior.
    Teto 1.20 restringe a porta a regime mais calmo sem cortar o
    nucleo do sinal (a Porta 1 ja exige pullback perto da MA21,
    o que so acontece em regime calmo por natureza).

Porta 3 fica INTOCADA — espelho do que a Grok fez (mexeu so na 2).
Se v5 ganhar, foi UMA das duas mudancas. Se perder, sei onde nao
cavar. Porta 3 vira a proxima tentativa, se houver.

Nenhuma afirmacao de benchmark — numero a medir no motor (Regras 4,8,9).
"""

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5

# --- Mudanca 1: Porta 2 ---
VARIACAO_MINIMA_ESTOCASTICO_MACD = 5.0    # grok v1 = 4.5

# --- Mudanca 2: Porta 1 ---
ATR_RELATIVO_MAX_PORTA_1 = 1.20           # grok v1 = 1.40


def gerar_sinal(row) -> int:
    tendencia = row['trend']
    if tendencia == 0:
        return 0

    hora = row['dt'].strftime('%H:%M')
    amplitude = row['Maximo'] - row['Minimo']
    corpo = abs(row['Fechamento'] - row['Abertura'])
    separacao_medias = abs(row['MA21'] - row['MA50'])
    variacao_estocastico = abs(row['stoch'] - row['stoch_prev'])

    # Porta 1 — grok v1 com teto de ATR apertado (MUDANCA 2).
    bloqueado_ma21 = (
        row['dt'].weekday() == 3
        or '12:00' <= hora <= '13:15'
        or '15:00' <= hora <= '16:59'
    )
    separacao_fraca_ma21 = 75.0 <= separacao_medias <= 175.0
    if (
        not bloqueado_ma21
        and not separacao_fraca_ma21
        and row['atr_relativo'] <= ATR_RELATIVO_MAX_PORTA_1
        and row['distancia_ma21'] <= MAX_DISTANCIA_MA21
        and STOCH_MIN <= row['stoch'] <= STOCH_MAX
    ):
        if tendencia == 1 and row['stoch_subindo']:
            return 1
        if tendencia == -1 and row['stoch_descendo']:
            return -1

    # Porta 2 — grok v1 com piso apertado (MUDANCA 1).
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

    # Porta 3 — identica a grok v1. NAO mexida.
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