"""Entrada Manus Rompimento V1 — candidata para revisão e ranking oficial.

Hipótese de primeira tentativa, sem otimização contra o histórico oficial.
Mantém integralmente as três portas da entrada_grok_3_v1 e acrescenta uma
quarta porta de continuação: rompimento confirmado do extremo dos três candles
anteriores do próprio pregão, alinhado à tendência, ao RSI, ao estocástico e a
um candle direcional. A nova porta é avaliada somente quando nenhuma das três
portas originais disparou.

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto.

Esta candidata ainda não possui resultado financeiro oficial. Não promover
para titular antes dos rankings E e C e dos testes de robustez definidos em
compliance.md. Resultado histórico não garante desempenho futuro.
"""

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.5
ATR_RELATIVO_MAX_PORTA_1 = 1.40
CORTE_SEGUNDA_MANHA = "12:00"

ROMPIMENTO_LOOKBACK = 3
ROMPIMENTO_DISTANCIA_MIN = 90.0
ROMPIMENTO_DISTANCIA_MAX = 260.0
ROMPIMENTO_SEPARACAO_MIN = 175.0
ROMPIMENTO_ATR_REL_MIN = 0.75
ROMPIMENTO_ATR_REL_MAX = 1.60
ROMPIMENTO_CORPO_MIN = 0.55
ROMPIMENTO_FECHAMENTO_EXTREMO = 0.75
ROMPIMENTO_RSI_COMPRA = 55.0
ROMPIMENTO_RSI_VENDA = 45.0
ROMPIMENTO_STOCH_COMPRA_MIN = 50.0
ROMPIMENTO_STOCH_COMPRA_MAX = 88.0
ROMPIMENTO_STOCH_VENDA_MIN = 12.0
ROMPIMENTO_STOCH_VENDA_MAX = 50.0


def _resultado(sinal: int, porta: int, explicacao: str, detalhar: bool):
    if not detalhar:
        return sinal
    return {
        "sinal": sinal,
        "lado": "COMPRA" if sinal == 1 else "VENDA",
        "porta": porta,
        "total_portas": 4,
        "explicacao": explicacao,
    }


def _candles_anteriores_do_pregao(row):
    """Obtém os três candles fechados anteriores, sem atravessar o pregão."""
    ohlc = row.get("ohlc_recentes") or ()
    dt_atual = row.get("dt")
    if dt_atual is None or len(ohlc) < ROMPIMENTO_LOOKBACK + 1:
        return ()

    data_atual = dt_atual.date()
    anteriores = []
    for candle in ohlc[:-1]:
        dt_candle = candle.get("dt")
        if dt_candle is not None and dt_candle.date() == data_atual:
            anteriores.append(candle)
    return tuple(anteriores[-ROMPIMENTO_LOOKBACK:])


def _avaliar(row, detalhar: bool = False):
    tendencia = int(row["trend"])
    if tendencia == 0:
        return None if detalhar else 0

    hora = row["dt"].strftime("%H:%M")
    weekday = row["dt"].weekday()
    amplitude = float(row["Maximo"]) - float(row["Minimo"])
    corpo = abs(float(row["Fechamento"]) - float(row["Abertura"]))
    separacao_medias = abs(float(row["MA21"]) - float(row["MA50"]))
    variacao_estocastico = abs(float(row["stoch"]) - float(row["stoch_prev"]))

    # Porta 1: retomada da MA21 — idêntica à base titular informada.
    bloqueado_segunda_compra = (
        weekday == 0 and hora <= CORTE_SEGUNDA_MANHA and tendencia == 1
    )
    bloqueado_ma21 = (
        weekday == 3
        or bloqueado_segunda_compra
        or "12:00" <= hora <= "13:15"
        or "15:00" <= hora <= "16:59"
    )
    separacao_fraca_ma21 = 75.0 <= separacao_medias <= 175.0
    if (
        not bloqueado_ma21
        and not separacao_fraca_ma21
        and float(row["atr_relativo"]) <= ATR_RELATIVO_MAX_PORTA_1
        and float(row["distancia_ma21"]) <= MAX_DISTANCIA_MA21
        and STOCH_MIN <= float(row["stoch"]) <= STOCH_MAX
    ):
        if tendencia == 1 and row["stoch_subindo"]:
            return _resultado(
                1,
                1,
                "Retomada compradora perto da MA21 com estocástico subindo.",
                detalhar,
            )
        if tendencia == -1 and row["stoch_descendo"]:
            return _resultado(
                -1,
                1,
                "Retomada vendedora perto da MA21 com estocástico caindo.",
                detalhar,
            )

    # Porta 2: cruzamento MACD com deslocamento mínimo do estocástico.
    bloqueado_macd = "11:45" <= hora <= "12:30"
    amplitude_fraca_macd = 240.0 <= amplitude <= 340.0
    if (
        not bloqueado_macd
        and not amplitude_fraca_macd
        and float(row["distancia_ma21"]) > 200.0
        and variacao_estocastico >= VARIACAO_MINIMA_ESTOCASTICO_MACD
    ):
        if tendencia == 1 and row["stoch_subindo"] and row["macd_cross_up"]:
            return _resultado(
                1,
                2,
                "Continuação compradora confirmada por cruzamento do MACD.",
                detalhar,
            )
        if tendencia == -1 and row["stoch_descendo"] and row["macd_cross_down"]:
            return _resultado(
                -1,
                2,
                "Continuação vendedora confirmada por cruzamento do MACD.",
                detalhar,
            )

    # Porta 3: saída de extremo do estocástico.
    bloqueado_estocastico = "12:30" <= hora <= "13:15"
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    if not bloqueado_estocastico and not amplitude_fraca_estocastico:
        if amplitude > 0.0 and corpo <= 0.70 * amplitude:
            if tendencia == 1 and row["stoch_cross_up_20"]:
                return _resultado(
                    1,
                    3,
                    "Compra após o estocástico sair da região de sobrevenda.",
                    detalhar,
                )
            if tendencia == -1 and row["stoch_cross_down_80"]:
                return _resultado(
                    -1,
                    3,
                    "Venda após o estocástico sair da região de sobrecompra.",
                    detalhar,
                )

    # Porta 4: rompimento confirmado dos três candles anteriores do pregão.
    anteriores = _candles_anteriores_do_pregao(row)
    rsi = float(row.get("rsi", 50.0))
    atr_relativo = float(row["atr_relativo"])
    distancia_ma21 = float(row["distancia_ma21"])
    fechamento = float(row["Fechamento"])
    abertura = float(row["Abertura"])
    minimo = float(row["Minimo"])
    maximo = float(row["Maximo"])
    stoch = float(row["stoch"])

    rompimento_horario_valido = not (
        "11:45" <= hora <= "13:15" or hora >= "17:15"
    )
    rompimento_regime_valido = (
        len(anteriores) == ROMPIMENTO_LOOKBACK
        and rompimento_horario_valido
        and ROMPIMENTO_DISTANCIA_MIN <= distancia_ma21 <= ROMPIMENTO_DISTANCIA_MAX
        and separacao_medias >= ROMPIMENTO_SEPARACAO_MIN
        and ROMPIMENTO_ATR_REL_MIN <= atr_relativo <= ROMPIMENTO_ATR_REL_MAX
        and amplitude > 0.0
        and corpo >= ROMPIMENTO_CORPO_MIN * amplitude
    )

    if rompimento_regime_valido:
        topo_anterior = max(float(c["Maximo"]) for c in anteriores)
        fundo_anterior = min(float(c["Minimo"]) for c in anteriores)
        posicao_fechamento = (fechamento - minimo) / amplitude

        if (
            tendencia == 1
            and fechamento > topo_anterior
            and fechamento > abertura
            and posicao_fechamento >= ROMPIMENTO_FECHAMENTO_EXTREMO
            and rsi >= ROMPIMENTO_RSI_COMPRA
            and ROMPIMENTO_STOCH_COMPRA_MIN <= stoch <= ROMPIMENTO_STOCH_COMPRA_MAX
            and row["stoch_subindo"]
        ):
            return _resultado(
                1,
                4,
                "Rompimento comprador confirmado acima dos três candles anteriores.",
                detalhar,
            )

        if (
            tendencia == -1
            and fechamento < fundo_anterior
            and fechamento < abertura
            and posicao_fechamento <= 1.0 - ROMPIMENTO_FECHAMENTO_EXTREMO
            and rsi <= ROMPIMENTO_RSI_VENDA
            and ROMPIMENTO_STOCH_VENDA_MIN <= stoch <= ROMPIMENTO_STOCH_VENDA_MAX
            and row["stoch_descendo"]
        ):
            return _resultado(
                -1,
                4,
                "Rompimento vendedor confirmado abaixo dos três candles anteriores.",
                detalhar,
            )

    return None if detalhar else 0


def gerar_sinal(row) -> int:
    return _avaliar(row, detalhar=False)


def diagnosticar_sinal(row):
    return _avaliar(row, detalhar=True)


__all__ = ["gerar_sinal", "diagnosticar_sinal"]
