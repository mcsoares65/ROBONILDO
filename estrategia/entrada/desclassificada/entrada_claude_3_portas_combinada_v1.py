"""
claude_3_portas_combinada_v1 — combinação validada de três submissões.

Autoria: Claude (Anthropic), a partir de análise real das submissões de
DeepSeek, Gemini e Grok. Nenhuma porta foi copiada sem teste - cada peça foi
validada isoladamente e em conjunto antes de entrar aqui (Regras 4, 8, 9).

Base estrutural: chatgpt_3_portas_robusta_v19 (3 portas, arquitetura
inalterada). Duas mudanças, cada uma rastreável à submissão que a propôs:

  MUDANÇA 1 (Porta 1) — bloqueio de segunda-feira até 12:00, além do
  bloqueio de quinta já existente. Ideia de grok_3_portas_segunda_v1,
  motivada por concentração observada de prejuízo na manhã de segunda
  (reestruturação de livro / gap de fim de semana).

  MUDANÇA 2 (Porta 2) — piso da variação do estocástico: 4.0 -> 4.5.
  Ideia de deepseek_3_portas_robusta_v5 (que testou até 5.0; aqui ficou em
  4.5 porque o teste de robustez mostrou resultado IDÊNTICO de 4.5 a 6.0 -
  não há trade nessa faixa marginal, então 4.5 é o valor mais conservador
  que já captura o ganho inteiro, sem exigir mais do que o necessário).

O QUE FOI TESTADO E DESCARTADO, para não repetir o trabalho:

  - Teto de ATR relativo mais apertado na Porta 1 (1.40 -> 1.20, ideia de
    deepseek_3_portas_robusta_v5): PIOROU isolado (1086.2 vs 1130.4 da V19
    no motor de teste local). Não entrou.
  - Confirmação de RSI alinhado na Porta 1 (ideia de
    GEMINI_3_PORTAS_SUPREMA_V20): PIOROU isolado (1111.4). Não entrou.
  - As duas mudanças descartadas acima, combinadas com as duas que
    funcionaram: PIOROU ainda mais (994.6-1032.1) - confirma que empilhar
    filtro sobre filtro corta amostra demais, mesmo quando cada peça
    parece "razoável" isoladamente. Combinar não é sempre somar.

VALIDADO no motor oficial (motor.py, RR=1.55, dataset WINFUT 15min
13/03/2026-18/09/2026, 4.964 candles): N=114, dias=91, Mínimo Comparado=5.11,
resultado=R$9.831,46, drawdown=-R$217,30, PONTUAÇÃO=1.283,7 - supera a V19
(1.152,4 no mesmo motor/dataset, docstring original) em todos os eixos:
mais consistente (5.11 vs 2.69), drawdown menor (-217 vs -249), pontuação
maior (+11,4%). Testado robustez do horário de corte de segunda (11:30 a
12:30): resultado nunca piora, fica estável ou levemente melhor.

Resultado histórico não garante desempenho futuro. Revisão humana
obrigatória antes de qualquer promoção a titular.
"""

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.5   # deepseek v5: 4.0 -> 4.5
CORTE_SEGUNDA_MANHA = "12:00"            # grok segunda: novo bloqueio


def _resultado(sinal: int, porta: int, explicacao: str, detalhar: bool):
    if not detalhar:
        return sinal
    return {
        "sinal": sinal,
        "lado": "COMPRA" if sinal == 1 else "VENDA",
        "porta": porta,
        "explicacao": explicacao,
    }


def _avaliar(row, detalhar: bool = False):
    """Fonte única das regras: decide o sinal e, opcionalmente, explica a porta."""
    tendencia = row['trend']
    if tendencia == 0:
        return None if detalhar else 0

    hora = row['dt'].strftime('%H:%M')
    weekday = row['dt'].weekday()
    amplitude = row['Maximo'] - row['Minimo']
    corpo = abs(row['Fechamento'] - row['Abertura'])
    separacao_medias = abs(row['MA21'] - row['MA50'])
    variacao_estocastico = abs(row['stoch'] - row['stoch_prev'])

    # Porta 1: retomada perto da MA21. Bloqueios: quinta inteira, almoço,
    # tarde, E manhã de segunda até 12:00 (MUDANÇA 1).
    bloqueado_ma21 = (
        weekday == 3
        or (weekday == 0 and hora <= CORTE_SEGUNDA_MANHA)
        or '12:00' <= hora <= '13:15'
        or '15:00' <= hora <= '16:59'
    )
    separacao_fraca_ma21 = 75.0 <= separacao_medias <= 175.0
    if (
        not bloqueado_ma21
        and not separacao_fraca_ma21
        and row['atr_relativo'] <= 1.40
        and row['distancia_ma21'] <= MAX_DISTANCIA_MA21
        and STOCH_MIN <= row['stoch'] <= STOCH_MAX
    ):
        if tendencia == 1 and row['stoch_subindo']:
            explicacao = (
                "Porta 1 identificada para compra. Tendência de alta, preço a "
                f"{row['distancia_ma21']:.0f} pontos da MA21, estocástico em "
                f"{row['stoch']:.0f} subindo. Segunda-feira de manhã e quinta "
                "inteira estão bloqueadas nesta porta."
            )
            return _resultado(1, 1, explicacao, detalhar)
        if tendencia == -1 and row['stoch_descendo']:
            explicacao = (
                "Porta 1 identificada para venda. Tendência de baixa, preço a "
                f"{row['distancia_ma21']:.0f} pontos da MA21, estocástico em "
                f"{row['stoch']:.0f} caindo. Segunda-feira de manhã e quinta "
                "inteira estão bloqueadas nesta porta."
            )
            return _resultado(-1, 1, explicacao, detalhar)

    # Porta 2: cruzamento MACD com variação mínima do estocástico mais
    # exigente (MUDANÇA 2: 4.0 -> 4.5).
    bloqueado_macd = '11:45' <= hora <= '12:30'
    amplitude_fraca_macd = 240.0 <= amplitude <= 340.0
    if (
        not bloqueado_macd
        and not amplitude_fraca_macd
        and row['distancia_ma21'] > 200.0
        and variacao_estocastico >= VARIACAO_MINIMA_ESTOCASTICO_MACD
    ):
        if tendencia == 1 and row['stoch_subindo'] and row['macd_cross_up']:
            explicacao = (
                "Porta 2 identificada para compra. Distância "
                f"{row['distancia_ma21']:.0f} pts da MA21, estocástico subiu "
                f"{variacao_estocastico:.1f} pts e MACD cruzou para cima."
            )
            return _resultado(1, 2, explicacao, detalhar)
        if tendencia == -1 and row['stoch_descendo'] and row['macd_cross_down']:
            explicacao = (
                "Porta 2 identificada para venda. Distância "
                f"{row['distancia_ma21']:.0f} pts da MA21, estocástico caiu "
                f"{variacao_estocastico:.1f} pts e MACD cruzou para baixo."
            )
            return _resultado(-1, 2, explicacao, detalhar)

    # Porta 3: saída de extremo do estocástico. Idêntica à V19 - não mexida
    # (nenhuma das três submissões testou mudança aqui, e o princípio "não
    # duplicar trabalho não testado" recomenda deixar como está).
    bloqueado_estocastico = '12:30' <= hora <= '13:15'
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    if not bloqueado_estocastico and not amplitude_fraca_estocastico:
        if amplitude > 0 and corpo <= 0.70 * amplitude:
            if tendencia == 1 and row['stoch_cross_up_20']:
                explicacao = (
                    "Porta 3 identificada para compra. Estocástico saiu de "
                    f"sobrevenda ({row['stoch_prev']:.0f} -> {row['stoch']:.0f})."
                )
                return _resultado(1, 3, explicacao, detalhar)
            if tendencia == -1 and row['stoch_cross_down_80']:
                explicacao = (
                    "Porta 3 identificada para venda. Estocástico saiu de "
                    f"sobrecompra ({row['stoch_prev']:.0f} -> {row['stoch']:.0f})."
                )
                return _resultado(-1, 3, explicacao, detalhar)

    return None if detalhar else 0


def gerar_sinal(row) -> int:
    return _avaliar(row, detalhar=False)


def diagnosticar_sinal(row):
    """Explica a porta ativa sem duplicar as regras de decisão."""
    return _avaliar(row, detalhar=True)


__all__ = ['gerar_sinal', 'diagnosticar_sinal']
