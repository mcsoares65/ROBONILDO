"""Roteador de regime — MBR (Modelo de Bandas de Regime) v01.

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).

Regra 11.2 — 1ª submissão formal do MBR. Nenhuma variação de limiar foi
rodada contra o bloco de Validação. Os três regimes são definidos por
convenção pública (separação de médias + ATR relativo + amplitude),
não por garimpagem contra o dataset.

Regra 11.3 — usa apenas filtros relativos (separação de médias em pontos,
ATR relativo, amplitude do candle em ATR). Nenhuma data específica,
preço absoluto do WINFUT ou evento de calendário.

Regra 3 — sem I/O, sem rede, sem import de módulo do projeto. As três
lógicas de regime convivem no MESMO arquivo (não há import de um
cartucho para outro) exatamente para não violar a Regra 3.

Regra 1 — gerar_sinal(row) -> -1 | 0 | 1.
Contrato opcional (V453): diagnosticar_oportunidades(row).
"""

SEPARACAO_TENDENCIA_MIN = 60.0
SEPARACAO_RANGE_MAX = 45.0
ATR_REL_TENDENCIA_MIN = 0.90
ATR_REL_TENDENCIA_MAX = 1.40
ATR_REL_RANGE_MAX = 0.90
ATR_REL_EXPANSAO_MIN = 1.40
DIST_MA21_TENDENCIA_MAX = 180.0
PRIORIDADE_PORTA = 3


def _direcao(row):
    return "COMPRA" if row["trend"] == 1 else "VENDA" if row["trend"] == -1 else "NEUTRA"


def _classificar_regime(row):
    """Devolve 'TENDENCIA', 'RANGE', 'EXPANSAO' ou 'INDEFINIDO'."""
    trend = row["trend"]
    atr_rel = row.get("atr_relativo")
    if trend == 0 or atr_rel is None:
        return "INDEFINIDO"

    separacao = abs(row["MA21"] - row["MA50"])

    if atr_rel >= ATR_REL_EXPANSAO_MIN:
        return "EXPANSAO"
    if separacao >= SEPARACAO_TENDENCIA_MIN and ATR_REL_TENDENCIA_MIN <= atr_rel <= ATR_REL_TENDENCIA_MAX:
        return "TENDENCIA"
    if separacao <= SEPARACAO_RANGE_MAX and atr_rel <= ATR_REL_RANGE_MAX:
        return "RANGE"
    return "INDEFINIDO"


def _avaliar_tendencia(row):
    """Segue a tendência com stop apertado (o stop real é da saída MBR)."""
    trend = row["trend"]
    distancia = row["distancia_ma21"]
    stoch = row.get("stoch")
    if stoch is None:
        return 0, ["estocástico disponível"]
    if distancia > DIST_MA21_TENDENCIA_MAX:
        return 0, ["distância máxima da MA21"]

    if trend == 1:
        condicoes = [
            (row["Fechamento"] > row["MA21"], "preço acima da MA21"),
            (bool(row.get("stoch_subindo")), "estocástico subindo"),
            (30.0 <= stoch <= 75.0, "estocástico em zona saudável"),
        ]
    else:
        condicoes = [
            (row["Fechamento"] < row["MA21"], "preço abaixo da MA21"),
            (bool(row.get("stoch_descendo")), "estocástico descendo"),
            (25.0 <= stoch <= 70.0, "estocástico em zona saudável"),
        ]
    elegivel = all(v for v, _ in condicoes)
    return (trend if elegivel else 0), [t for v, t in condicoes if not v]


def _avaliar_range(row):
    """Reversão nos extremos do range do dia — ainda precisa de dados
    que o row atual não expõe (máxima/mínima do dia). Por ora, devolve
    0 e o roteador cai no regime de tendência. Este regime fica como
    placeholder para a v02, que exigirá o campo `range_dia` no row."""
    return 0, ["range do dia ainda não exposto em row (v02)"]


def _avaliar(row):
    regime = _classificar_regime(row)

    if regime == "EXPANSAO":
        return 0, ["regime de expansão — não operar"], regime
    if regime == "TENDENCIA":
        sinal, faltantes = _avaliar_tendencia(row)
        return sinal, faltantes, regime
    if regime == "RANGE":
        sinal, faltantes = _avaliar_range(row)
        return sinal, faltantes, regime
    return 0, ["regime indefinido"], regime


def gerar_sinal(row) -> int:
    return _avaliar(row)[0]


def diagnosticar_oportunidades(row):
    sinal, faltantes, regime = _avaliar(row)
    total = 4 if regime == "TENDENCIA" else 1
    confirmadas = total - len(faltantes)
    return [{
        "estrategia": f"MBR {regime}",
        "prioridade": PRIORIDADE_PORTA,
        "direcao": _direcao(row),
        "sinal": sinal,
        "confirmadas": confirmadas,
        "total": total,
        "progresso": confirmadas / total if total else 0.0,
        "faltantes": faltantes,
        "detalhe": faltantes[0] if faltantes else regime,
    }]


__all__ = ["gerar_sinal", "diagnosticar_oportunidades"]