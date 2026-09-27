"""
estrategia/saida/saida_claude_v3.py

Autoria: Claude (Anthropic), gerado nesta sessão, ainda SEM revisão
humana completa e SEM nenhum backtest rodado — candidata crua, não
validada. Não promover, não citar resultado nenhum até rodar de fato
contra `classificacao.py` (Regra 4).

Numeração (Regra 6): "v3" é a contagem própria do autor (Claude) para
candidatas de saída neste laboratório — NÃO a VERSAO do projeto
(versionamento.py, atualmente V444) e não relacionada a ela. v1 foi o
baseline original (`saida_claude_v1.py`, depois renomeado para
`baseline.py` na V434); v2 (`saida_claude_v2.py`) já existe no
laboratório; esta é a terceira entrega de Claude nesse slot.

Variações testadas antes desta versão (Regra 11.2): nenhuma além desta —
é a primeira ideia escrita para exercitar a nova autoridade da Regra 1
v8 (proposta, pendente de ratificação). Não houve iteração numérica
prévia nem "melhor de N tentativas".

O QUE ESTA CANDIDATA FAZ DE DIFERENTE
--------------------------------------
Todas as candidatas de saída anteriores (baseline, saida_chatgpt_v2/v3,
saida_grok_v6) só podiam ANTECIPAR o fechamento (devolver True/False).
Esta candidata nunca pede fechamento antecipado (`fechar` sempre False)
— ela testa exclusivamente o novo mecanismo da Regra 1 v8: propor um
APERTO de stop, em duas fases, com base só no que `posicao` já expõe
hoje (sem precisar conhecer o stop/alvo original do motor):

1. BREAKEVEN: assim que o resultado flutuante atinge
   `LIMIAR_BREAKEVEN_PTS`, propõe mover o stop para a própria entrada —
   a operação deixa de poder terminar em prejuízo (exceto custos/slippage
   dentro do candle, que o motor já trata como sempre).
2. TRAILING: assim que a máxima (ou mínima, na venda) desde a entrada
   avança `LIMIAR_TRAILING_PTS` além do breakeven, passa a propor um
   stop que segue essa máxima/mínima a uma distância fixa
   (`DISTANCIA_TRAILING_PTS`) — sempre apertando, nunca soltando (o
   motor garante isso de qualquer forma, mas a lógica aqui já respeita
   isso por construção: só recalcula pra frente, nunca guarda estado
   próprio, Regra 3).

Nenhum campo usado aqui é inventado — só os que `posicao` já documenta
oficialmente hoje: `lado`, `entrada`, `candles_decorridos`,
`maxima_desde_entrada`, `minima_desde_entrada`,
`resultado_flutuante_pts`. Nenhum acesso a `row` além do contrato.
"""

from __future__ import annotations

# Limiares em PONTOS do WINFUT — valores redondos de partida, escolhidos
# por bom senso (não otimizados/ajustados contra nenhum histórico ainda).
# Regra 10 exige perturbar esses três valores em ±10-30% antes de
# qualquer promoção, para confirmar que não é ajuste fino ao ruído.
LIMIAR_BREAKEVEN_PTS = 300.0
LIMIAR_TRAILING_PTS = 600.0
DISTANCIA_TRAILING_PTS = 250.0


def avaliar_saida(row: dict, posicao: dict) -> dict:
    lado = posicao["lado"]
    entrada = posicao["entrada"]
    maxima = posicao["maxima_desde_entrada"]
    minima = posicao["minima_desde_entrada"]
    resultado_flutuante_pts = posicao["resultado_flutuante_pts"]

    novo_stop = None

    if resultado_flutuante_pts >= LIMIAR_TRAILING_PTS:
        # Fase 2: trailing atrás da máxima/mínima favorável já vista.
        if lado == "COMPRA":
            novo_stop = maxima - DISTANCIA_TRAILING_PTS
        else:
            novo_stop = minima + DISTANCIA_TRAILING_PTS
    elif resultado_flutuante_pts >= LIMIAR_BREAKEVEN_PTS:
        # Fase 1: trava no breakeven (entrada).
        novo_stop = entrada

    return {
        "fechar": False,  # esta candidata nunca antecipa - só aperta stop
        "novo_stop": novo_stop,
        "novo_alvo": None,  # não mexe no alvo nesta versão
    }
