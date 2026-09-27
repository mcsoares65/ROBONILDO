"""
estrategia/saida/saida_claude_v4.py

Autoria: Claude (Anthropic), gerado nesta sessão, ainda SEM revisão
humana completa. Backtest rodado (ver seção "Resultado medido" abaixo) —
não promover a titular sem passar pelos testes de robustez/holdout
(Regras 10/11).

Numeração (Regra 6): "v4" é a contagem própria do autor (Claude) para
candidatas de saída neste laboratório — NÃO a VERSAO do projeto
(versionamento.py). v1 foi o baseline original (renomeado para
baseline.py); v2 (`saida_claude_v2.py`) já existe no laboratório; v3
(`saida_claude_v3.py`) foi a primeira a testar a autoridade de
reconfiguração de stop da Regra 1 v8/v9. Esta v4 corrige um problema que
só apareceu depois que a Regra 1 avançou para v10.

Variações testadas antes desta versão (Regra 11.2): v3 (mesma lógica de
breakeven/trailing, sem stop inicial) já foi rodada contra o dataset
oficial e SUPERADA pelo baseline (R$6.537,75 vs R$16.585,04 sob a Regra 1
v9). Esta v4 muda exatamente UMA coisa em relação à v3: adiciona um stop
inicial na abertura. O resto (limiares de breakeven/trailing) é idêntico
à v3, não houve nova rodada de ajuste fino desses valores.

O QUE MUDOU DA v3 PARA A v4 (e por quê)
------------------------------------------
A v3 nunca definia `novo_stop` até o resultado flutuante atingir
`LIMIAR_BREAKEVEN_PTS` (300 pontos) — sob a Regra 1 v9, isso era
inofensivo porque o motor ainda calculava um stop/alvo inicial próprio
como "piso" implícito. Sob a Regra 1 v10, o motor não calcula mais nada:
uma posição cujo cartucho de saída não definir nível nenhum fica
GENUINAMENTE sem stop, por tempo indefinido, até o corte de horário do
pregão — um risco que a v3 nunca foi desenhada para assumir (e que não
tinha sido percebido antes de testar contra o motor v10 de verdade).

A v4 corrige isso da forma mais direta: define um stop estrutural inicial
na abertura (mesma fórmula do baseline — swing dos últimos
`SWING_LOOKBACK_CANDLES` candles via `row["ohlc_recentes"]`), sem alvo
fixo (o alvo continua sempre `None` — a aposta desta família de
candidatas é deixar o lucro correr via trailing, não travar num RR fixo).
Da segunda chamada em diante, o comportamento de breakeven/trailing da v3
é preservado sem nenhuma mudança.

Nenhum campo usado aqui é inventado — só os que `posicao` e `row` já
documentam oficialmente hoje: `lado`, `entrada`, `candles_decorridos`,
`maxima_desde_entrada`, `minima_desde_entrada`, `resultado_flutuante_pts`
e `row["ohlc_recentes"]` (V444).
"""

from __future__ import annotations

# Limiares em PONTOS do WINFUT — mesmos valores da v3, não reajustados
# nesta versão (só o stop inicial é novo). Regra 10 exige perturbar esses
# valores em +/-10-30% antes de qualquer promoção.
LIMIAR_BREAKEVEN_PTS = 300.0
LIMIAR_TRAILING_PTS = 600.0
DISTANCIA_TRAILING_PTS = 250.0

# Fórmula do stop inicial — copiada do baseline.py (mesmos valores de
# configuracao.py, não importados — Regra 3).
SWING_LOOKBACK_CANDLES = 4


def _stop_inicial(row: dict, entrada: float, lado: str):
    ohlc = row.get("ohlc_recentes") or ()
    janela = ohlc[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        return None
    if lado == "COMPRA":
        stop = min(c["Minimo"] for c in janela)
        return stop if stop < entrada else None
    stop = max(c["Maximo"] for c in janela)
    return stop if stop > entrada else None


def avaliar_saida(row: dict, posicao: dict) -> dict:
    lado = posicao["lado"]
    entrada = posicao["entrada"]
    maxima = posicao["maxima_desde_entrada"]
    minima = posicao["minima_desde_entrada"]
    resultado_flutuante_pts = posicao["resultado_flutuante_pts"]

    if posicao["candles_decorridos"] == 0:
        # NOVO na v4: sem isto, a posição nasce sem stop nenhum sob a
        # Regra 1 v10 (motor não tem mais fórmula própria) e fica exposta
        # até o corte de horário, se o preço nunca andar 300pts a favor.
        return {
            "fechar": False,
            "novo_stop": _stop_inicial(row, entrada, lado),
            "novo_alvo": None,
        }

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
        "fechar": False,
        "novo_stop": novo_stop,
        "novo_alvo": None,
    }
