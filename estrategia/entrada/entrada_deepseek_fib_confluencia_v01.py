"""Confluência por Fibonacci do swing recente — candidata de entrada.

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).
O "v01" no nome é numeração própria deste autor, NÃO a VERSAO do projeto
(versionamento.py, hoje V456).

Regra 11.2 — declaração de variações testadas:
  Esta é a 1ª submissão formal desta ideia. Nenhuma variação de limiar foi
  rodada contra o bloco de Validação. Os níveis de Fibonacci (23,6%, 38,2%,
  50%, 61,8%) são convenção pública da literatura técnica, não ajustados
  contra o dataset oficial.

Regra 11.3 — nenhuma lógica depende de data específica, evento de calendário
ou preço absoluto do WINFUT. Os níveis são calculados sobre o swing de
row["ohlc_recentes"], que é relativo ao preço corrente. A tolerância de
confluência é uma fração do próprio swing, não um valor fixo em pontos.

Regra 3 — sem I/O, sem rede, sem import de módulo do projeto (inclusive
configuracao.py). Todas as constantes abaixo são cópias explícitas.

Regra 1 — contrato: gerar_sinal(row) -> -1 | 0 | 1.
Contrato opcional: diagnosticar_oportunidades(row) -> list[dict].

Estratégia de origem: esta porta replica as TRÊS condições do composto
titular (Retomada MA21, MACD + Estocástico, Saída de Extremo) e adiciona
uma quarta condição de confluência — o preço precisa estar próximo de um
nível de Fibonacci calculado sobre o swing dos últimos N candles. Se a
confluência não estiver presente, o sinal é 0 mesmo que todas as três
portas do composto estejam confirmadas.
"""

# ---------------------------------------------------------------------------
# Constantes copiadas (Regra 3: nunca importadas de configuracao.py)
# ---------------------------------------------------------------------------
SWING_LOOKBACK_CANDLES = 8
NIVEIS_FIBONACCI = (0.236, 0.382, 0.500, 0.618)
TOLERANCIA_FRACAO_SWING = 0.05  # 5% do swing
ATR_REL_MAX = 1.55
STOCH_MIN = 20.0
STOCH_MAX = 80.0
DIST_MA21_MAX_PORTA1 = 90.0
DIST_MA21_MIN_PORTA2 = 200.0
AMPLITUDE_PORTA2_MIN = 240.0
AMPLITUDE_PORTA2_MAX = 340.0
AMPLITUDE_PORTA3_MIN = 279.0
AMPLITUDE_PORTA3_MAX = 360.0
CORPO_PORTA3_FRACAO_MAX = 0.70
PRIORIDADE_PORTA = 2


def _direcao(row):
    return "COMPRA" if row["trend"] == 1 else "VENDA" if row["trend"] == -1 else "NEUTRA"


def _swing_recente(row):
    """Devolve (minima, maxima) da janela ohlc_recentes, ou (None, None)."""
    janela = (row.get("ohlc_recentes") or ())[-SWING_LOOKBACK_CANDLES:]
    if len(janela) < SWING_LOOKBACK_CANDLES:
        return None, None
    minima = min(float(c["Minimo"]) for c in janela)
    maxima = max(float(c["Maximo"]) for c in janela)
    if maxima <= minima:
        return None, None
    return minima, maxima


def _proximo_de_fibonacci(preco, minima, maxima, lado):
    """Devolve True se `preco` está dentro da tolerância de algum nível de Fib.

    Numa COMPRA, Fibonacci relevante é a retração do swing de alta (preço
    desce até um nível e continua); numa VENDA, é a retração do swing de
    baixa (preço sobe até um nível e continua). A tolerância é uma fração
    do próprio swing, não um valor fixo em pontos — portanto escalável.
    """
    amplitude = maxima - minima
    if amplitude <= 0:
        return False
    tolerancia = TOLERANCIA_FRACAO_SWING * amplitude

    for nivel in NIVEIS_FIBONACCI:
        # Em compra, procuramos retração a partir da máxima.
        # Em venda, procuramos retração a partir da mínima.
        if lado == "COMPRA":
            ponto = maxima - nivel * amplitude
        else:
            ponto = minima + nivel * amplitude
        if abs(preco - ponto) <= tolerancia:
            return True
    return False


def _avaliar(row):
    """Devolve (sinal, lista_de_faltantes).

    Replica as três portas do composto titular e exige confluência de
    Fibonacci como quarta condição. Se qualquer porta dispararia, mas o
    preço não está em nível de Fibonacci, o sinal é 0 — este cartucho
    é mais restritivo que o titular por design.
    """
    trend = row["trend"]
    if trend == 0:
        return 0, ["definição de tendência"]

    atr_rel = row.get("atr_relativo")
    stoch = row.get("stoch")
    if atr_rel is None or stoch is None:
        return 0, ["indicadores-base disponíveis"]
    if atr_rel > ATR_REL_MAX:
        return 0, ["volatilidade aceitável"]

    minima, maxima = _swing_recente(row)
    if minima is None:
        return 0, ["histórico recente suficiente"]

    preco = row["Fechamento"]
    lado = "COMPRA" if trend == 1 else "VENDA"
    if not _proximo_de_fibonacci(preco, minima, maxima, lado):
        return 0, ["confluência com nível de Fibonacci"]

    # --- Porta 1: Retomada MA21 ---
    p1 = [
        row["distancia_ma21"] <= DIST_MA21_MAX_PORTA1,
        STOCH_MIN <= stoch <= STOCH_MAX,
        bool(row.get("stoch_subindo")) if trend == 1 else bool(row.get("stoch_descendo")),
    ]
    # --- Porta 2: MACD + Estocástico ---
    amplitude = row["Maximo"] - row["Minimo"]
    p2 = [
        row["distancia_ma21"] > DIST_MA21_MIN_PORTA2,
        abs(stoch - (row.get("stoch_prev") or stoch)) >= 4.5,
        bool(row.get("stoch_subindo")) if trend == 1 else bool(row.get("stoch_descendo")),
        bool(row.get("macd_cross_up")) if trend == 1 else bool(row.get("macd_cross_down")),
    ]
    # --- Porta 3: Saída de Extremo ---
    corpo = abs(row["Fechamento"] - row["Abertura"])
    p3 = [
        amplitude > 0,
        corpo <= CORPO_PORTA3_FRACAO_MAX * amplitude,
        bool(row.get("stoch_cross_up_20")) if trend == 1 else bool(row.get("stoch_cross_down_80")),
    ]

    if all(p1) or all(p2) or all(p3):
        return trend, []

    # Se nenhuma porta inteira confirmou, devolve o que falta da porta
    # mais próxima (mais condições verdadeiras) para o radar.
    candidatas = [("Porta 1 (Retomada MA21)", p1), ("Porta 2 (MACD+Estoc.)", p2), ("Porta 3 (Extremo)", p3)]
    candidatas.sort(key=lambda x: sum(bool(c) for c in x[1]), reverse=True)
    nome, condicoes = candidatas[0]
    faltantes = [f"{nome}: condição {i+1}" for i, c in enumerate(condicoes) if not c]
    return 0, faltantes


def gerar_sinal(row) -> int:
    return _avaliar(row)[0]


def diagnosticar_oportunidades(row):
    sinal, faltantes = _avaliar(row)
    total = 5
    confirmadas = total - len(faltantes)
    return [{
        "estrategia": "Fibonacci Confluência",
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