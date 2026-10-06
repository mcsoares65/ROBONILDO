# DESCLASSIFICADA pela Regra 16 (V490): agregador de ideias por OU. Fora do ranking.
# Ver conselho/2026-10-05-AE.txt. Mantida so como referencia/paridade; nao alterada.
"""ChatGPT 3 Portas Robusta V19 — candidata a revisao humana.

Autoria: gerada por OpenAI Codex, em sessao operada por Marcio Soares.
Revisao humana antes da submissao definitiva: pendente.

Derivada da Defensiva V13. Usa volatilidade controlada na Porta 1, faixa de
separacao fraca mais estreita e variacao minima do estocastico na Porta 2.
A Porta 4 foi removida: sua faixa de distancia elevava a pontuacao no recorte,
mas falhou no teste de sensibilidade quando perturbada em +20%.

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa somente os campos oficiais,
nao realiza I/O, nao mantem estado e nao altera regras do motor.

Benchmark local comprovado no motor oficial, dataset WINFUT 15 minutos de
13/03/2026 a 18/09/2026 (4.964 candles): R$ 10.465,24; drawdown
-R$ 249,48; 93 dias operados; Pontuacao Composta 1.152,4.
Resultado historico nao garante desempenho futuro.
"""

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.0


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
    amplitude = row['Maximo'] - row['Minimo']
    corpo = abs(row['Fechamento'] - row['Abertura'])
    separacao_medias = abs(row['MA21'] - row['MA50'])
    variacao_estocastico = abs(row['stoch'] - row['stoch_prev'])

    # Porta 1: retomada perto da MA21, evitando volatilidade excessiva.
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
        and row['distancia_ma21'] <= MAX_DISTANCIA_MA21
        and STOCH_MIN <= row['stoch'] <= STOCH_MAX
    ):
        if tendencia == 1 and row['stoch_subindo']:
            explicacao = (
                "Porta 1 identificada para compra. A média móvel de 21 períodos "
                "está acima da média móvel de 50 períodos, o preço está a "
                f"{row['distancia_ma21']:.0f} pontos da média móvel de 21 períodos, "
                f"o estocástico está em {row['stoch']:.0f} e está subindo, e a "
                f"volatilidade relativa está em {row['atr_relativo']:.2f}. Existe "
                "expectativa de compra no fechamento deste candle."
            )
            return _resultado(1, 1, explicacao, detalhar)
        if tendencia == -1 and row['stoch_descendo']:
            explicacao = (
                "Porta 1 identificada para venda. A média móvel de 21 períodos "
                "está abaixo da média móvel de 50 períodos, o preço está a "
                f"{row['distancia_ma21']:.0f} pontos da média móvel de 21 períodos, "
                f"o estocástico está em {row['stoch']:.0f} e está caindo, e a "
                f"volatilidade relativa está em {row['atr_relativo']:.2f}. Existe "
                "expectativa de venda no fechamento deste candle."
            )
            return _resultado(-1, 1, explicacao, detalhar)

    # Porta 2: cruzamento MACD confirmado por deslocamento do estocastico.
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
                "Porta 2 identificada para compra. A tendência é de alta, o preço "
                f"está a {row['distancia_ma21']:.0f} pontos da média móvel de 21 "
                f"períodos, o estocástico subiu {variacao_estocastico:.1f} pontos "
                "e o indicador de convergência e divergência das médias móveis "
                "cruzou sua linha de sinal para cima. Existe expectativa de compra "
                "no fechamento deste candle."
            )
            return _resultado(1, 2, explicacao, detalhar)
        if tendencia == -1 and row['stoch_descendo'] and row['macd_cross_down']:
            explicacao = (
                "Porta 2 identificada para venda. A tendência é de baixa, o preço "
                f"está a {row['distancia_ma21']:.0f} pontos da média móvel de 21 "
                f"períodos, o estocástico caiu {variacao_estocastico:.1f} pontos "
                "e o indicador de convergência e divergência das médias móveis "
                "cruzou sua linha de sinal para baixo. Existe expectativa de venda "
                "no fechamento deste candle."
            )
            return _resultado(-1, 2, explicacao, detalhar)

    # Porta 3: saida de extremo do estocastico.
    bloqueado_estocastico = '12:30' <= hora <= '13:15'
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    if not bloqueado_estocastico and not amplitude_fraca_estocastico:
        if amplitude > 0 and corpo <= 0.70 * amplitude:
            if tendencia == 1 and row['stoch_cross_up_20']:
                explicacao = (
                    "Porta 3 identificada para compra. A tendência é de alta, o "
                    f"estocástico saiu da região de sobrevenda, passando de "
                    f"{row['stoch_prev']:.0f} para {row['stoch']:.0f}, e o corpo do "
                    "candle permanece compatível com a amplitude. Existe expectativa "
                    "de compra no fechamento deste candle."
                )
                return _resultado(1, 3, explicacao, detalhar)
            if tendencia == -1 and row['stoch_cross_down_80']:
                explicacao = (
                    "Porta 3 identificada para venda. A tendência é de baixa, o "
                    f"estocástico saiu da região de sobrecompra, passando de "
                    f"{row['stoch_prev']:.0f} para {row['stoch']:.0f}, e o corpo do "
                    "candle permanece compatível com a amplitude. Existe expectativa "
                    "de venda no fechamento deste candle."
                )
                return _resultado(-1, 3, explicacao, detalhar)

    return None if detalhar else 0


def gerar_sinal(row) -> int:
    return _avaliar(row, detalhar=False)


def diagnosticar_sinal(row):
    """Explica a porta ativa sem alterar ou duplicar as regras de decisão."""
    return _avaliar(row, detalhar=True)


__all__ = ['gerar_sinal', 'diagnosticar_sinal']
