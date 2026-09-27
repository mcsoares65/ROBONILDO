"""
saida_grok_v6.py — trava de lucro no fim do pregão

Autoria original: Grok (xAI). Adaptação de contrato para a Regra 1 v10:
Claude (Anthropic), a pedido do dono do laboratório.

CORREÇÃO IMPORTANTE (revertida uma tentativa anterior de "consertar" isto)
---------------------------------------------------------------------------
Uma versão anterior deste patch tinha colado, aqui dentro, a MESMA fórmula
de stop estrutural + RR fixo que antes vivia em `motor.py` — na prática,
emprestando a regra fixa antiga para "tapar" a ausência de stop deste
arquivo. Isso violava o próprio princípio da Regra 1 v10: quem define a
saída é a estratégia de saída titular, e não uma fórmula genérica
reaproveitada de outro lugar (mesmo que o "outro lugar" seja o próprio
motor antigo). O sintoma disso apareceu no ranking ao vivo: como
`baseline.py` usa a mesma fórmula, os dois cartuchos produziam o mesmo
resultado — não são duas saídas diferentes, eram a mesma regra com dois
nomes.

Revertido. Este arquivo agora só contém a lógica que o autor (Grok)
realmente desenhou: um profit-lock pós-17:30, nada além disso.

O QUE ISSO SIGNIFICA NA PRÁTICA: esta saída, hoje, NÃO tem nenhuma regra
própria de stop de perda. A lógica original sempre presumiu que "stop/alvo
do motor continuam prioritários" — nunca foi desenhada para cobrir essa
função. Sob a Regra 1 v10 (motor sem fórmula própria nenhuma), isso quer
dizer que uma posição aberta com esta saída como titular só se fecha por
duas vias: o próprio profit-lock (se estiver no lucro depois das 17:30) ou
o corte de horário forçado (18:20:58), absorvendo o prejuízo inteiro de
qualquer dia ruim até lá.

Esse é um resultado real e válido de "cada saída dona da própria regra":
esta saída, do jeito que o autor a desenhou, não gerencia perda. Se isso é
aceitável como está, ou se precisa de uma regra de stop pensada
especificamente para ela (não emprestada de `baseline.py` nem de nenhum
outro arquivo), é uma decisão do dono do laboratório — não uma correção
que este patch deveria tomar sozinho.

Enquanto essa decisão não é tomada, o dono do laboratório optou por manter
`baseline.py` como saída titular em produção (ele tem uma regra de stop
coerente e testada, assumida como estratégia própria dela, não emprestada
para tapar buraco de outro arquivo).

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
  existindo, aplicado como piso/teto por fora deste arquivo) — não é mais
  um número válido sob o motor v10 (sem stop nenhum do motor): precisa ser
  re-testado antes de qualquer nova comparação/promoção (Regra 4).

Contrato (Regra 1 v10): avaliar_saida(row, posicao) -> dict
Sem I/O, sem estado, sem imports do projeto. `novo_stop`/`novo_alvo`
sempre None — este arquivo não define nenhum, por design (ver acima).
"""

from __future__ import annotations

HORA_MINIMA = "17:30"
MIN_FLUT_ATR = 1.0
MIN_CANDLES = 2


def avaliar_saida(row: dict, posicao: dict) -> dict:
    """Lógica original do autor (Grok), inalterada — só o formato do
    retorno virou dict (Regra 1 v10) em vez de bool. Nunca define
    novo_stop/novo_alvo: esta saída não tem regra própria de stop de
    perda (ver docstring do módulo)."""
    candles_decorridos = posicao.get("candles_decorridos", 0)

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
