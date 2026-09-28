"""Entrada Manus V4 — compressão seguida de expansão direcional.

Autoria: gerada por Manus AI em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v4 é a contagem própria
do Manus para candidatas de entrada, não a VERSAO do projeto.

Origem: reformulação e desmembramento da Porta 4 de entrada_manus_v1.py. Em
relação à origem, o lookback muda de três para quatro candles; os ranges
anteriores precisam estar comprimidos em relação ao ATR50; o candle atual
precisa expandir em relação ao ATR50 e à própria base; e foram removidos os
filtros de horário, distância/separação, RSI e estocástico. A candidata não
reutiliza as Portas 1–3 da entrada titular e funciona como setup independente.

Hipótese pré-declarada: um rompimento tem maior chance de continuação quando
quatro candles fechados do mesmo pregão apresentam ranges comprimidos e o
candle atual expande acima dessa base, rompe o envelope e fecha perto do
extremo na direção da tendência. O isolamento facilita comparar o efeito da
entrada no ranking E, pareada à saída titular; não prova causalidade no ranking
cruzado.

Variações relevantes executadas antes desta versão: zero. Esta é a única
especificação de compressão-expansão implementada; outras sete famílias foram
apenas analisadas no planejamento, sem execução contra dataset. Os limiares não
foram escolhidos após consulta à Validação ou ao Holdout. A estratégia não
depende de datas, eventos ou preços absolutos.

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa somente campos fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto.
Não há resultado financeiro oficial; validar somente após revisão do conselho.
"""

COMPRESSAO_LOOKBACK = 4
RANGE_COMPRIMIDO_MAX_ATR50 = 0.75
RANGE_EXPANSAO_MIN_ATR50 = 1.25
EXPANSAO_SOBRE_BASE_MIN = 1.50
CORPO_MINIMO_FRACAO = 0.55
FECHAMENTO_EXTREMO_FRACAO = 0.75


def _candles_anteriores_do_pregao(row):
    """Retorna os quatro candles anteriores, sem atravessar a sessão."""
    ohlc = row.get("ohlc_recentes") or ()
    dt_atual = row.get("dt")
    if dt_atual is None or len(ohlc) < COMPRESSAO_LOOKBACK + 1:
        return ()

    data_atual = dt_atual.date()
    anteriores = []
    for candle in ohlc[:-1]:
        dt_candle = candle.get("dt")
        if dt_candle is not None and dt_candle.date() == data_atual:
            anteriores.append(candle)
    return tuple(anteriores[-COMPRESSAO_LOOKBACK:])


def _avaliar(row):
    tendencia = int(row["trend"])
    if tendencia not in (-1, 1):
        return 0, "Tendência neutra."

    atr_media50 = float(row["atr_media50"])
    if atr_media50 <= 0.0:
        return 0, "ATR médio inválido."

    anteriores = _candles_anteriores_do_pregao(row)
    if len(anteriores) != COMPRESSAO_LOOKBACK:
        return 0, "Ainda não há quatro candles anteriores do mesmo pregão."

    ranges_anteriores = [
        float(candle["Maximo"]) - float(candle["Minimo"])
        for candle in anteriores
    ]
    if any(range_candle < 0.0 for range_candle in ranges_anteriores):
        return 0, "Janela anterior inválida."

    limite_compressao = RANGE_COMPRIMIDO_MAX_ATR50 * atr_media50
    if not all(range_candle <= limite_compressao for range_candle in ranges_anteriores):
        return 0, "A base anterior ainda não está comprimida."

    abertura = float(row["Abertura"])
    maxima = float(row["Maximo"])
    minima = float(row["Minimo"])
    fechamento = float(row["Fechamento"])
    amplitude = maxima - minima
    if amplitude <= 0.0:
        return 0, "Candle de expansão sem amplitude válida."

    maior_range_base = max(ranges_anteriores)
    expansao_valida = (
        amplitude >= RANGE_EXPANSAO_MIN_ATR50 * atr_media50
        and amplitude >= EXPANSAO_SOBRE_BASE_MIN * maior_range_base
    )
    if not expansao_valida:
        return 0, "O candle atual ainda não confirmou expansão."

    corpo = abs(fechamento - abertura)
    if corpo < CORPO_MINIMO_FRACAO * amplitude:
        return 0, "Corpo direcional insuficiente para o rompimento."

    topo_base = max(float(candle["Maximo"]) for candle in anteriores)
    fundo_base = min(float(candle["Minimo"]) for candle in anteriores)
    posicao_fechamento = (fechamento - minima) / amplitude

    if (
        tendencia == 1
        and fechamento > topo_base
        and fechamento > abertura
        and posicao_fechamento >= FECHAMENTO_EXTREMO_FRACAO
    ):
        return 1, "Compra: compressão, expansão e rompimento superior confirmados."

    if (
        tendencia == -1
        and fechamento < fundo_base
        and fechamento < abertura
        and posicao_fechamento <= 1.0 - FECHAMENTO_EXTREMO_FRACAO
    ):
        return -1, "Venda: compressão, expansão e rompimento inferior confirmados."

    return 0, "Expansão sem rompimento direcional confirmado."


def gerar_sinal(row) -> int:
    sinal, _ = _avaliar(row)
    return sinal


def diagnosticar_oportunidades(row):
    sinal, explicacao = _avaliar(row)
    confirmadas = 1 if sinal in (-1, 1) else 0
    return [{
        "estrategia": "Compressão e Expansão",
        "sinal": sinal,
        "confirmadas": confirmadas,
        "total": 1,
        "progresso": float(confirmadas),
        "faltantes": [] if confirmadas else [explicacao],
        "prioridade": 1,
    }]


def diagnosticar_sinal(row):
    sinal, explicacao = _avaliar(row)
    return {
        "porta": 1,
        "total_portas": 1,
        "estrategia": "Compressão e Expansão",
        "lado": "COMPRA" if sinal == 1 else "VENDA" if sinal == -1 else "NEUTRA",
        "progresso": 1.0 if sinal else 0.0,
        "confirmadas": 1 if sinal else 0,
        "total": 1,
        "faltantes": [] if sinal else [explicacao],
        "explicacao": explicacao,
    }


__all__ = ["gerar_sinal", "diagnosticar_oportunidades", "diagnosticar_sinal"]
