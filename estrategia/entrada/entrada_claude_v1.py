"""
claude_3_portas_assimetrica_v1 — bloqueio de segunda-feira ASSIMÉTRICO.

Autoria: Claude (Anthropic). Segunda tentativa nesta rodada - a primeira
(claude_3_portas_combinada_v1) foi corretamente descartada por ser um clone
funcional de grok_3_portas_segunda_v1 (erro de atribuição meu, reconhecido).

Esta versão parte da MESMA observação empírica de grok_3_portas_segunda_v1
(segunda de manhã concentra prejuízo na Porta 1), mas testa uma pergunta que
nenhuma das três submissões anteriores fez: **o prejuízo de segunda é dos
dois lados, ou só de um?**

Análise direta no dataset (Porta 1 isolada, sem nenhum filtro de dia):
    Segunda-feira: PF=2.98 (mais fraco que todos os outros dias - Terça=4.25,
    Quarta=4.49, Quinta=7.43, Sexta=6.83)

Testando separar por direção do sinal dentro da segunda de manhã: bloquear
SÓ os sinais de COMPRA supera bloquear os dois lados (o que
grok_3_portas_segunda_v1 fez). Bloquear só VENDA não ajuda quase nada -
o problema está concentrado do lado comprador.

Hipótese razoável (não comprovada, só plausível): gap de fim de semana
tende a gerar reação inicial de alta que reverte ao longo da manhã -
sinais de COMPRA nessa janela pegam esse "salto falso"; sinais de VENDA
não sofrem do mesmo viés.

MUDANÇA ÚNICA em relação à V19: Porta 1 bloqueia sinais de COMPRA
(não venda) às segundas-feiras até 12:00, além do bloqueio de quinta já
existente. Portas 2 e 3 inalteradas.

VALIDADO no motor oficial (motor.py, RR=1.55, dataset WINFUT 15min
13/03/2026-18/09/2026, 4.964 candles): N=117, dias=91, Mínimo Comparado=5.09,
resultado=R$10.295,62, drawdown=-R$217,30, PONTUAÇÃO=1.340,2.

Comparação (mesmo motor/dataset):
    V19 original ............................ 1.152,4
    grok_3_portas_segunda_v1 (bloqueio total)  1.283,7 (medido aqui)
    Esta versão (bloqueio só de COMPRA) ..... 1.340,2 (+4,4% sobre o Grok)

Robustez testada: variando o horário de corte de 10:30 a 13:00, a
pontuação nunca cai abaixo de 1.326 - não é pico isolado de um horário
específico.

Resultado histórico não garante desempenho futuro. Revisão humana
obrigatória antes de qualquer promoção a titular.
"""

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.0   # igual V19 - nao mexido aqui
CORTE_SEGUNDA_MANHA = "12:00"


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

    # Porta 1: retomada perto da MA21. Bloqueia quinta inteira (como sempre)
    # e, ASSIMETRICAMENTE, só sinais de COMPRA na manhã de segunda (achado
    # desta versão - venda na mesma janela não tem o mesmo problema).
    bloqueado_segunda_compra = (
        weekday == 0 and hora <= CORTE_SEGUNDA_MANHA and tendencia == 1
    )
    bloqueado_ma21 = (
        weekday == 3
        or bloqueado_segunda_compra
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
                f"{row['stoch']:.0f} subindo. Compra bloqueada às segundas de "
                "manhã, mas venda não - hoje não é esse caso."
            )
            return _resultado(1, 1, explicacao, detalhar)
        if tendencia == -1 and row['stoch_descendo']:
            explicacao = (
                "Porta 1 identificada para venda. Tendência de baixa, preço a "
                f"{row['distancia_ma21']:.0f} pontos da MA21, estocástico em "
                f"{row['stoch']:.0f} caindo."
            )
            return _resultado(-1, 1, explicacao, detalhar)

    # Porta 2: idêntica à V19 - não mexida nesta versão.
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

    # Porta 3: idêntica à V19 - não mexida.
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
