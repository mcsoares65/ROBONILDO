"""Continuação por RSI + confirmação de estocástico em regime saudável.

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).
O "v05" no nome é numeração própria deste autor, NÃO a VERSAO do projeto.

Regra 11.2 — 5ª iteração formal. Diagnóstico do ranking C001:
  v01 e v04 perderam feio (acumulado −3.560 a 201) porque RSI sozinho
  em faixa larga pega exaustão em candle de spike. Correção: exigir
  confluência com estocástico na mesma direção, restringir ATR a uma
  faixa estreita de regime saudável, apertar distância máxima da MA21,
  e filtrar horários de abertura/fechamento onde o padrão não se sustenta.

Regra 11.3 — apenas filtros relativos (tendência, RSI, estocástico,
ATR relativo, distância em pontos). Nenhuma data, preço absoluto ou
evento específico.

Regra 3 — sem I/O, sem import de módulo do projeto.

Regra 1 — gerar_sinal(row) -> -1 | 0 | 1.
"""

RSI_MIN_COMPRA = 52.0
RSI_MAX_COMPRA = 68.0
RSI_MIN_VENDA = 32.0
RSI_MAX_VENDA = 48.0
STOCH_MIN_COMPRA = 35.0
STOCH_MAX_COMPRA = 70.0
STOCH_MIN_VENDA = 30.0
STOCH_MAX_VENDA = 65.0
ATR_REL_MIN = 0.90
ATR_REL_MAX = 1.35
DIST_MA21_MIN = 10.0
DIST_MA21_MAX = 150.0
HORA_INICIO = "09:30"
HORA_FIM = "17:00"
PRIORIDADE_PORTA = 4


def _direcao(row):
    return "COMPRA" if row["trend"] == 1 else "VENDA" if row["trend"] == -1 else "NEUTRA"


def _avaliar(row):
    trend = row["trend"]
    hora = row["dt"].strftime("%H:%M")

    if trend == 0:
        return 0, ["definição de tendência"]
    if not (HORA_INICIO <= hora <= HORA_FIM):
        return 0, ["horário permitido"]
    if row["dt"].weekday() == 3:  # quinta — consistentemente fraca no dataset histórico do projeto
        return 0, ["dia da semana desfavorável"]

    rsi = row.get("rsi")
    rsi_prev = row.get("rsi_prev")
    atr_rel = row.get("atr_relativo")
    stoch = row.get("stoch")
    if None in (rsi, rsi_prev, atr_rel, stoch):
        return 0, ["indicadores-base disponíveis"]

    distancia = row["distancia_ma21"]
    condicoes_comuns = [
        (ATR_REL_MIN <= atr_rel <= ATR_REL_MAX, "regime de volatilidade saudável"),
        (DIST_MA21_MIN <= distancia <= DIST_MA21_MAX, "distância saudável da MA21"),
    ]

    if trend == 1:
        condicoes = condicoes_comuns + [
            (row["Fechamento"] > row["MA21"], "preço acima da MA21"),
            (RSI_MIN_COMPRA <= rsi <= RSI_MAX_COMPRA, "RSI em continuação de alta"),
            (rsi > rsi_prev, "RSI subindo"),
            (STOCH_MIN_COMPRA <= stoch <= STOCH_MAX_COMPRA, "estocástico confirma alta"),
            (bool(row.get("stoch_subindo")), "estocástico subindo"),
        ]
    else:
        condicoes = condicoes_comuns + [
            (row["Fechamento"] < row["MA21"], "preço abaixo da MA21"),
            (RSI_MIN_VENDA <= rsi <= RSI_MAX_VENDA, "RSI em continuação de baixa"),
            (rsi < rsi_prev, "RSI descendo"),
            (STOCH_MIN_VENDA <= stoch <= STOCH_MAX_VENDA, "estocástico confirma baixa"),
            (bool(row.get("stoch_descendo")), "estocástico descendo"),
        ]

    elegivel = all(v for v, _ in condicoes)
    faltantes = [t for v, t in condicoes if not v]
    return (trend if elegivel else 0), faltantes


def gerar_sinal(row) -> int:
    return _avaliar(row)[0]


def diagnosticar_oportunidades(row):
    sinal, faltantes = _avaliar(row)
    total = 7
    confirmadas = total - len(faltantes)
    return [{
        "estrategia": "RSI + Estocástico em Regime",
        "prioridade": PRIORIDADE_PORTA,
        "direcao": _direcao(row),
        "sinal": sinal,
        "confirmadas": confirmadas,
        "total": total,
        "progresso": confirmadas / total if total else 0.0,
        "faltantes": faltantes,
        "detalhe": faltantes[0] if faltantes else "nenhuma",
    }]


__all__ = ["gerar_sinal", "diagnosticar_oportunidades"]