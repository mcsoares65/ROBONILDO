"""Entrada Manus V5 — três portas da titular com veto uniforme pós-almoço.

Autoria: gerada por Manus AI em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente (Regras 6 e 8). A numeração v5 é a
contagem própria do Manus para candidatas de entrada, não a VERSAO do projeto.

Origem: cópia integral da titular ``titular/entrada_grok_3_v1.py`` (commit
ed639293) com uma única mudança: nenhuma porta abre operação em candle rotulado
entre 13:00 e 13:59. Todos os limiares, a prioridade das portas e o radar
continuam iguais; o veto entra como mais uma condição de elegibilidade.

Hipótese pré-declarada: a titular já bloqueia partes do horário de almoço, mas
em janelas diferentes por porta (P1 12:00-13:15, P2 11:45-12:30, P3
12:30-13:15). A hora seguinte, quando a liquidez volta, ainda produz
cruzamentos e retomadas que não se sustentam. Um veto único para essa hora
completa os bloqueios existentes sem cortar o restante da tarde.

Pesquisa (Regra 11.2) — feita somente no bloco de Desenvolvimento
2025-09-15 a 2025-12-30 (74 pregões, anterior à Validação 2026-01-02 a
2026-09-25). Nenhuma variação rodou na Validação nem no Holdout. Foram cerca
de 30 variações de entrada: retirar a P2 ou a P3, filtrar a P3 por RSI ou pela
separação das médias, e 8 janelas de veto entre 12:45 e 14:30, cada uma com
duas saídas. As janelas foram escolhidas depois do diagnóstico por hora da
campeã, que mostrou a hora das 13h negativa em 13 operações.

Resultado de Desenvolvimento, com a saída titular: acumulado +350 para
``entrada_grok_3_v1`` e +418 na média de seis entradas de topo, positivo nas
duas metades e em todas as entradas testadas. O drawdown piora um pouco
(-333 -> -358). Robustez (Regra 10): janelas 12:45-13:59, 13:00-13:59,
13:15-13:59 e 13:00-14:14 dão +392 a +418; 13:30-13:59 dá +226. Veto de
13:00 a 14:30 já fica negativo (-221), então o efeito não é um corte genérico
da tarde. Fragilidade declarada: apenas 13 operações sustentam a hipótese, e
sem as 3 maiores diferenças o ganho cai para cerca de +100. Na janela
13:00-13:44 a primeira metade fica negativa.

Regra 11.3: usa apenas horário do pregão, sem datas, eventos ou preços
absolutos. Contrato: gerar_sinal(row) -> 1, -1 ou 0; stateless, sem I/O e
sem imports do projeto. Não há alegação de que supere a titular antes do
ranking.
"""

VETO_POS_ALMOCO_INICIO = "13:00"
VETO_POS_ALMOCO_FIM = "13:59"


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
    fora_pos_almoco = not (VETO_POS_ALMOCO_INICIO <= hora <= VETO_POS_ALMOCO_FIM)

    e1_itens = [
        (tendencia != 0, "definição de tendência"),
        (not (row["dt"].weekday() == 3 or "12:00" <= hora <= "13:15" or "15:00" <= hora <= "16:59"), "horário permitido"),
        (fora_pos_almoco, "fora da retomada pós-almoço"),
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
        (fora_pos_almoco, "fora da retomada pós-almoço"),
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
        (fora_pos_almoco, "fora da retomada pós-almoço"),
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
    # Telemetria opcional para o painel; não participa de gerar_sinal().
    for oportunidade in oportunidades:
        faltante = oportunidade["faltantes"][0] if oportunidade["faltantes"] else "nenhuma"
        detalhe = faltante
        if faltante == "aproximação da MA21":
            detalhe = f"dist. MA21 {row['distancia_ma21']:.0f} (máx. 90)"
        elif faltante == "estocástico fora dos extremos":
            detalhe = f"estoc. {row['stoch']:.1f} (16,5-83,5)"
        elif faltante == "afastamento superior a 200 pontos":
            detalhe = f"afastamento {row['distancia_ma21']:.0f}/200 pts"
        elif faltante == "variação mínima do estocástico":
            detalhe = f"var. estoc. {variacao_stoch:.1f}/4,5"
        elif faltante == "corpo sem exaustão":
            proporcao_corpo = (corpo / amplitude * 100.0) if amplitude > 0 else 0.0
            detalhe = f"corpo {proporcao_corpo:.0f}% (máx. 70%)"
        elif faltante == "fora da retomada pós-almoço":
            detalhe = f"veto {VETO_POS_ALMOCO_INICIO}-{VETO_POS_ALMOCO_FIM}"
        oportunidade["detalhe"] = detalhe
    return sorted(oportunidades, key=lambda item: (-item["progresso"], item["prioridade"]))


def gerar_sinal(row) -> int:
    # Mesma prioridade explícita da titular: P1 -> P2 -> P3.
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
        "porta": oportunidade["prioridade"],
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
