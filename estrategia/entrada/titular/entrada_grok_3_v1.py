"""Agregador compatível das três estratégias Grok desmembradas na V448.

`gerar_sinal` preserva os limiares e a prioridade histórica das antigas
portas: retomada MA21 -> MACD/estocástico -> saída de extremo.
`diagnosticar_oportunidades` expõe o progresso de todas ao radar.
"""


def _direcao(row):
    return "COMPRA" if row["trend"] == 1 else "VENDA" if row["trend"] == -1 else "NEUTRA"


def _resultado(nome, prioridade, row, elegivel, bloqueios, condicoes, descricoes, sinal):
    total = len(condicoes)
    confirmadas = sum(bool(valor) for valor in condicoes) if elegivel else 0
    faltantes = ([texto for valor, texto in zip(condicoes, descricoes) if not valor]
                 if elegivel else bloqueios)
    return {
        "estrategia": nome,
        "prioridade": prioridade,
        "direcao": _direcao(row),
        "sinal": sinal,
        "confirmadas": confirmadas,
        "total": total,
        "progresso": confirmadas / total if total else 0.0,
        "faltantes": faltantes,
    }


def diagnosticar_oportunidades(row):
    tendencia = row["trend"]
    hora = row["dt"].strftime("%H:%M")
    amplitude = row["Maximo"] - row["Minimo"]
    corpo = abs(row["Fechamento"] - row["Abertura"])
    separacao = abs(row["MA21"] - row["MA50"])
    variacao_stoch = abs(row["stoch"] - row["stoch_prev"])
    direcao_stoch = (row["stoch_subindo"] if tendencia == 1
                      else row["stoch_descendo"] if tendencia == -1 else False)
    cruzamento_macd = (row["macd_cross_up"] if tendencia == 1
                       else row["macd_cross_down"] if tendencia == -1 else False)
    cruzamento_extremo = (row["stoch_cross_up_20"] if tendencia == 1
                          else row["stoch_cross_down_80"] if tendencia == -1 else False)

    e1_itens = [
        (tendencia != 0, "definição de tendência"),
        (not (row["dt"].weekday() == 3 or "12:00" <= hora <= "13:15" or "15:00" <= hora <= "16:59"), "horário permitido"),
        (not (75.0 <= separacao <= 175.0), "separação saudável das médias"),
        (row["atr_relativo"] <= 1.40, "volatilidade aceitável"),
    ]
    c1 = [
        row["distancia_ma21"] <= 90.0,
        16.5 <= row["stoch"] <= 83.5,
        direcao_stoch,
    ]
    e2_itens = [
        (tendencia != 0, "definição de tendência"),
        (not ("11:45" <= hora <= "12:30"), "horário permitido"),
        (not (240.0 <= amplitude <= 340.0), "amplitude fora da faixa fraca"),
    ]
    c2 = [
        row["distancia_ma21"] > 200.0,
        variacao_stoch >= 4.5,
        direcao_stoch,
        cruzamento_macd,
    ]
    e3_itens = [
        (tendencia != 0, "definição de tendência"),
        (not ("12:30" <= hora <= "13:15"), "horário permitido"),
        (not (279.0 <= amplitude <= 360.0), "amplitude fora da faixa fraca"),
    ]
    c3 = [
        amplitude > 0,
        amplitude > 0 and corpo <= 0.70 * amplitude,
        cruzamento_extremo,
    ]
    e1 = all(valor for valor, _ in e1_itens)
    e2 = all(valor for valor, _ in e2_itens)
    e3 = all(valor for valor, _ in e3_itens)
    direcao = 1 if tendencia == 1 else -1 if tendencia == -1 else 0
    oportunidades = [
        _resultado("Retomada MA21", 1, row, e1,
            [texto for valor, texto in e1_itens if not valor], c1, [
            "aproximação da MA21", "estocástico fora dos extremos",
            "estocástico na direção da tendência",
        ], direcao if e1 and all(c1) else 0),
        _resultado("MACD + Estocástico", 2, row, e2,
            [texto for valor, texto in e2_itens if not valor], c2, [
            "afastamento superior a 200 pontos", "variação mínima do estocástico",
            "estocástico na direção da tendência", "cruzamento do MACD",
        ], direcao if e2 and all(c2) else 0),
        _resultado("Saída de Extremo", 3, row, e3,
            [texto for valor, texto in e3_itens if not valor], c3, [
            "amplitude válida", "corpo sem exaustão", "saída da zona extrema do estocástico",
        ], direcao if e3 and all(c3) else 0),
    ]
    return sorted(oportunidades, key=lambda item: (-item["progresso"], item["prioridade"]))


def gerar_sinal(row) -> int:
    # Prioridade explícita: reprodução integral do comportamento anterior.
    radar = sorted(diagnosticar_oportunidades(row), key=lambda item: item["prioridade"])
    for oportunidade in radar:
        if oportunidade["sinal"] in (-1, 1):
            return oportunidade["sinal"]
    return 0


def diagnosticar_sinal(row):
    radar = diagnosticar_oportunidades(row)
    confirmadas = [item for item in radar if item["sinal"] in (-1, 1)]
    oportunidade = min(confirmadas, key=lambda item: item["prioridade"]) if confirmadas else radar[0]
    faltante = oportunidade["faltantes"][0] if oportunidade["faltantes"] else "nenhuma"
    return {
        "porta": oportunidade["prioridade"],  # compatibilidade de tela com V447
        "total_portas": 3,
        "estrategia": oportunidade["estrategia"],
        "lado": oportunidade["direcao"],
        "progresso": oportunidade["progresso"],
        "confirmadas": oportunidade["confirmadas"],
        "total": oportunidade["total"],
        "faltantes": oportunidade["faltantes"],
        "explicacao": (
            f"A estratégia {oportunidade['estrategia']} está com "
            f"{oportunidade['confirmadas']} de {oportunidade['total']} confirmações. "
            f"Próxima condição: {faltante}."
        ),
    }
