"""
saida_grok_v6.py — trava de lucro no fim do pregão

Autoria original: Grok (xAI). Patch de migração para a Regra 1 v10:
Claude (Anthropic), a pedido do dono do laboratório.

POR QUE ESTE ARQUIVO PRECISOU SER ATUALIZADO
----------------------------------------------
A lógica original (a partir de "lógica original do autor" abaixo, sem
nenhuma mudança) sempre assumiu que "stop/alvo do motor continuam
prioritários" — ela só ANTECIPA um fechamento lucrativo perto do fim do
pregão; nunca foi desenhada para cuidar de stop/alvo, porque isso sempre
foi trabalho do motor.

A partir da Regra 1 v10 (compliance.md v8), o motor não calcula mais
NENHUM stop/alvo — quem for a saída titular é a única responsável por
defini-los, desde a abertura da posição. Como este arquivo nunca fazia
isso, promovê-lo a titular sem esta correção deixou TODA operação sem
nenhum stop de perda: constatado em produção via `classificacao.py` — o
drawdown ficou quase idêntico (-498,39) repetido em quase todas as
estratégias de entrada do ranking, porque sem stop nenhum a posição só
fecha no corte de horário forçado (18:20:58), absorvendo o prejuízo
inteiro de qualquer dia ruim — e como as entradas "3 portas" são variações
próximas da mesma ideia, várias caem no mesmo dia catastrófico.

O QUE MUDOU
-----------
Adicionado, uma única vez na abertura da posição (`candles_decorridos ==
0`), o MESMO stop estrutural + alvo em RR fixo que o motor calculava antes
— migração 1:1 da regra (mesma fórmula usada em `baseline.py`),
restaurando exatamente a suposição original do autor ("stop/alvo do motor
continuam prioritários"). Nada na lógica original de antecipação de lucro
foi alterado — mesmo limiar, mesmo horário, mesmo ATR, mesmas duas
funções.

Docstring original do autor (preservado para rastreabilidade):

  Ideia:
    Depois das 17:30, se a posição ainda está com lucro flutuante >= 1,0 x
    ATR, realiza. Evita devolver ganho no leilão/final do dia (muitos
    CORTEs da baseline eram lucros que encolhiam entre 17:30 e 18:20).

  Backtest (V19, jun-set/2026, mesmo motor, MAX 2 ops/dia):
    Baseline:     R$ 6.809,63 | DD -249,48 | PF 4,75 | score 622,9
    Esta saída:   R$ 6.974,73 | DD -249,48 | PF 5,01 | score 673,5
    Delta          +R$ 165,09  | DD igual   | stops 14->13

  Grade testada (hora x limiar ATR): melhor combinação 17:30 + 1,0 ATR.
  Várias vizinhas (17:30/0,8, 17:45/0,8) também bateram a baseline.

  Esse backtest foi medido com o motor v7 (stop/alvo fixo do motor ainda
  existindo) — não é mais um número válido: a mudança de contrato desta
  versão moveu a MESMA fórmula de stop/alvo pra dentro deste arquivo (ver
  abaixo), então precisa ser re-testado contra o motor v10 antes de
  qualquer nova comparação/promoção (Regra 4 — nenhum resultado antigo
  vale sem rodar de novo contra o motor atual).

Contrato (Regra 1 v10): avaliar_saida(row, posicao) -> dict
Sem I/O, sem estado, sem imports do projeto (SWING_LOOKBACK_CANDLES e
RELACAO_RISCO_RETORNO copiados de configuracao.py, não importados —
mesmos valores usados em baseline.py).
"""

from __future__ import annotations

HORA_MINIMA = "17:30"
MIN_FLUT_ATR = 1.0
MIN_CANDLES = 2

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55


def _stop_alvo_inicial(row: dict, entrada: float, lado: str):
    """Mesma fórmula que o motor usava (stop estrutural via
    row["ohlc_recentes"] + alvo em RR fixo) — migrada para dentro do
    cartucho, ver docstring do módulo. Calculada só na abertura."""
    ohlc = row.get("ohlc_recentes") or ()
    janela = ohlc[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        return None, None

    if lado == "COMPRA":
        stop = min(c["Minimo"] for c in janela)
        risco = entrada - stop
        if risco <= 0:
            return None, None
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    else:
        stop = max(c["Maximo"] for c in janela)
        risco = stop - entrada
        if risco <= 0:
            return None, None
        alvo = entrada - RELACAO_RISCO_RETORNO * risco

    return stop, alvo


def avaliar_saida(row: dict, posicao: dict) -> dict:
    candles_decorridos = posicao.get("candles_decorridos", 0)

    if candles_decorridos == 0:
        # NOVO (migração v10): define o stop/alvo inicial que o motor
        # calculava antes - sem isto a posição nasceria sem nenhuma
        # proteção de preço, e a lógica abaixo (do autor original) nunca
        # foi desenhada para cobrir essa lacuna.
        stop, alvo = _stop_alvo_inicial(row, posicao["entrada"], posicao["lado"])
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    # ---- lógica original do autor (Grok), inalterada, a partir daqui ----
    if candles_decorridos < MIN_CANDLES:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    atr = row.get("atr")
    if atr is None or atr != atr or atr <= 0:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    hm = row["dt"].strftime("%H:%M")
    if hm < HORA_MINIMA:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    flutuante = posicao["resultado_flutuante_pts"]
    if flutuante >= atr * MIN_FLUT_ATR:
        return {"fechar": True, "novo_stop": None, "novo_alvo": None}

    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    """Lógica original do autor (Grok), inalterada."""
    atr = row.get("atr")
    if atr is None or atr != atr or atr <= 0:
        return "ATR inválido"
    if posicao.get("candles_decorridos", 0) < MIN_CANDLES:
        return f"Aguarda {MIN_CANDLES} candles"

    hm = row["dt"].strftime("%H:%M")
    flut = posicao["resultado_flutuante_pts"]
    if hm < HORA_MINIMA:
        return f"Antes de {HORA_MINIMA} — não trava"
    if flut >= atr * MIN_FLUT_ATR:
        return f"TRAVA fim de pregão ({hm}, flut={flut:.0f} >= {MIN_FLUT_ATR} ATR)"
    return f"Após {HORA_MINIMA} mas flut={flut:.0f} < {MIN_FLUT_ATR} ATR"


__all__ = ["avaliar_saida", "diagnosticar_saida"]
