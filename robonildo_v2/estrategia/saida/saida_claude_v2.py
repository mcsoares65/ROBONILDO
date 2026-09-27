"""
saida_claude_v2.py — segunda candidata de saída.

Autoria: Claude (Anthropic).

IDEIA TESTADA: travar lucro antecipadamente quando o MACD cruza contra a
direção da posição, mas só depois que o lucro flutuante já passou de um
piso mínimo (evita reagir a ruído logo na entrada, quando qualquer
oscilação pequena ainda é normal).

    def avaliar_saida(row, posicao):
        if posicao["resultado_flutuante_pts"] < 250:
            return False
        if posicao["lado"] == "COMPRA":
            return row["macd_cross_down"]
        else:
            return row["macd_cross_up"]

HISTÓRICO HONESTO DE TESTES (entrada fixa: chatgpt_3_portas_robusta_v19,
dataset WINFUT 15min 13/03/2026-18/09/2026, 4.964 candles — isolando só a
variável saída, mesma prática usada em toda a rodada de entrada):

  1. Reversão do estocástico contra a posição, só em lucro: PIOROU muito
     (pontuação 455, baseline 1130,4) — reage a ruído candle a candle,
     corta ganhador antes da hora com frequência alta (~42% dos trades).
  2. Mesma ideia, exigindo 2 candles seguidos de reversão + piso de lucro
     de 150 pontos: melhorou mas continuou abaixo do baseline (950,3).
  3. Trailing de dar-back do pico (usando maxima/minima_desde_entrada, sem
     estado extra): PIOROU muito mais ainda (73-300) em toda a varredura
     de gatilho/folga testada — corta 50-80% dos trades prematuramente.
  4. MACD cruzando contra a posição, com piso de lucro (ESTE ARQUIVO):
     melhor resultado da rodada, mas AINDA abaixo do baseline —
     pontuação 908,7 (piso=250pts) contra 1130,4 do saida_claude_v1.

CONCLUSÃO DESTA RODADA: nenhuma das quatro ideias testadas supera o
comportamento atual (RR=1,55 fixo, sem antecipação). O motivo aparente:
o alvo fixo já captura ~35% dos trades no alvo cheio; qualquer saída
antecipada baseada em reversão de momentum tende a cortar justamente
esses vencedores antes de chegarem lá, sem compensar o suficiente nos
perdedores (que já são cortados pelo stop estrutural do motor, não por
este cartucho).

Este arquivo entra na competição mesmo perdendo hoje — é isso que uma
"competição de saída" significa: nem toda candidata vence de primeira,
e o ranking existe justamente para medir isso com transparência, não
para only aceitar vitórias.

VALIDADO por: motor de teste isolado (aproximação rápida, mesma lógica do
motor.py real) - NÃO validado ainda pelo motor.py oficial via
classificacao.py. Rodar o laboratório real antes de tirar qualquer
conclusão definitiva sobre a posição no ranking.
"""

LIMIAR_LUCRO_MINIMO_PONTOS = 250.0


def avaliar_saida(row, posicao) -> bool:
    if posicao["resultado_flutuante_pts"] < LIMIAR_LUCRO_MINIMO_PONTOS:
        return False
    if posicao["lado"] == "COMPRA":
        return bool(row["macd_cross_down"])
    else:
        return bool(row["macd_cross_up"])


def diagnosticar_saida(row, posicao):
    """Mesmo espírito de diagnosticar_sinal() do lado da entrada - explica
    a decisão quando houver decisão real de fechar antecipado."""
    if not avaliar_saida(row, posicao):
        return None
    return {
        "fechar": True,
        "motivo": "MACD_CONTRARIO_EM_LUCRO",
        "explicacao": (
            f"Lucro flutuante de {posicao['resultado_flutuante_pts']:.0f} pontos "
            f"já acima do piso de {LIMIAR_LUCRO_MINIMO_PONTOS:.0f}, e o MACD "
            f"cruzou contra a direção da posição — travando o ganho antes do "
            f"alvo cheio."
        ),
    }


__all__ = ['avaliar_saida', 'diagnosticar_saida']
