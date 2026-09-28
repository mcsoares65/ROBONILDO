"""Continuação por RSI — candidata de entrada.

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).

Regra 6 — o "v1" no nome é numeração própria deste autor, não a VERSAO do
projeto (versionamento.py).

Regra 11.2 — declaração de variações testadas:
  Esta é a 1ª submissão formal desta ideia ao laboratório. Nenhuma variação
  de limiar foi oficialmente testada contra o bloco de Validação; as faixas
  escolhidas são derivadas de convenção pública de RSI (50 como linha
  neutra, 72/28 como início de exaustão) e não de garimpagem contra o
  dataset oficial.

Regra 11.3 — nenhuma lógica depende de data específica, evento, preço
absoluto ou estrutura particular do dataset. Todos os filtros são relativos
(tendência das médias, faixa de RSI, faixa de estocástico, ATR relativo,
distância à MA21 em pontos).

Regra 3 — sem I/O, sem rede, sem import de qualquer módulo do projeto
(inclusive configuracao.py). Todas as constantes abaixo são cópias
explícitas e documentadas.

Regra 1 — contrato: gerar_sinal(row) -> -1 | 0 | 1.
Contrato opcional: diagnosticar_oportunidades(row) -> list[dict].
"""

# ---------------------------------------------------------------------------
# Constantes copiadas (Regra 3: nunca importadas de configuracao.py)
# ---------------------------------------------------------------------------
RSI_MIN_COMPRA = 50.0
RSI_MAX_COMPRA = 72.0
RSI_MIN_VENDA = 28.0
RSI_MAX_VENDA = 50.0
STOCH_MIN = 20.0
STOCH_MAX = 80.0
ATR_REL_MAX = 1.50
DIST_MA21_MAX = 250.0
PRIORIDADE_PORTA = 5


def _direcao(row):
    return "COMPRA" if row["trend"] == 1 else "VENDA" if row["trend"] == -1 else "NEUTRA"


def _avaliar(row):
    """Devolve (sinal, lista_de_faltantes).

    O sinal é 1 (compra), -1 (venda) ou 0 (nada), sempre alinhado com
    row["trend"] — esta porta não opera contra a tendência estrutural.
    """
    trend = row["trend"]
    if trend == 0:
        return 0, ["definição de tendência"]

    rsi = row.get("rsi")
    rsi_prev = row.get("rsi_prev")
    if rsi is None or rsi_prev is None:
        return 0, ["RSI disponível"]

    atr_rel = row.get("atr_relativo")
    stoch = row.get("stoch")
    if stoch is None or atr_rel is None:
        return 0, ["indicadores-base disponíveis"]

    condicoes_comuns = [
        (atr_rel <= ATR_REL_MAX, "volatilidade aceitável"),
        (row["distancia_ma21"] <= DIST_MA21_MAX, "aproximação das médias"),
        (STOCH_MIN <= stoch <= STOCH_MAX, "estocástico fora dos extremos"),
    ]

    if trend == 1:
        condicoes = condicoes_comuns + [
            (row["Fechamento"] > row["MA21"], "preço acima da MA21"),
            (RSI_MIN_COMPRA <= rsi <= RSI_MAX_COMPRA, "RSI em zona de continuação"),
            (rsi > rsi_prev, "RSI subindo"),
            (bool(row.get("rsi_subindo")), "RSI com momentum de alta"),
        ]
    else:
        condicoes = condicoes_comuns + [
            (row["Fechamento"] < row["MA21"], "preço abaixo da MA21"),
            (RSI_MIN_VENDA <= rsi <= RSI_MAX_VENDA, "RSI em zona de continuação"),
            (rsi < rsi_prev, "RSI descendo"),
            (bool(row.get("rsi_descendo")), "RSI com momentum de baixa"),
        ]

    elegivel = all(valor for valor, _ in condicoes)
    faltantes = [texto for valor, texto in condicoes if not valor]
    return (trend if elegivel else 0), faltantes


def gerar_sinal(row) -> int:
    """Contrato oficial da Regra 1: -1, 0 ou 1."""
    return _avaliar(row)[0]


def diagnosticar_oportunidades(row):
    """Radar opcional (contrato da V453). Nunca interfere no sinal."""
    sinal, faltantes = _avaliar(row)
    total = 7
    confirmadas = total - len(faltantes)
    return [{
        "estrategia": "Continuação RSI",
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