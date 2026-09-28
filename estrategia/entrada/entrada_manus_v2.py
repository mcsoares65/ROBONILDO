"""Entrada Manus V2 — retomada confirmada pelo lado estrutural da MA21.

Autoria: gerada por Manus AI em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v2 é a contagem própria
do Manus para candidatas de entrada, não a VERSAO do projeto.

Hipótese desta versão: a Porta 1 representa uma retomada somente quando o
fechamento permanece no lado da MA21 coerente com a tendência. Em tendência
de alta, o fechamento precisa estar sobre ou na MA21; em tendência de baixa,
sob ou na MA21. As demais regras e a prioridade 1 -> 2 -> 3 são preservadas.
A quarta porta de rompimento da V1 foi removida porque criava sinais próprios
e podia alterar a sequência de ocupação da posição.

Variações relevantes testadas nesta rodada: nenhuma no dataset oficial. Esta é
uma única hipótese estrutural pré-declarada, sem busca de parâmetros, datas ou
eventos do histórico. O resultado financeiro ainda precisa ser medido pelo
motor oficial após revisão do conselho.

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto.
"""


MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.5
ATR_RELATIVO_MAX_PORTA_1 = 1.40


def _direcao(row):
    tendencia = int(row["trend"])
    return "COMPRA" if tendencia == 1 else "VENDA" if tendencia == -1 else "NEUTRA"


def _resultado(nome, prioridade, row, elegivel, bloqueios, condicoes, descricoes, sinal):
    total = len(condicoes)
    confirmadas = sum(bool(valor) for valor in condicoes) if elegivel else 0
    faltantes = (
        [texto for valor, texto in zip(condicoes, descricoes) if not valor]
        if elegivel
        else bloqueios
    )
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
    tendencia = int(row["trend"])
    hora = row["dt"].strftime("%H:%M")
    amplitude = float(row["Maximo"]) - float(row["Minimo"])
    corpo = abs(float(row["Fechamento"]) - float(row["Abertura"]))
    separacao = abs(float(row["MA21"]) - float(row["MA50"]))
    variacao_stoch = abs(float(row["stoch"]) - float(row["stoch_prev"]))

    direcao_stoch = (
        bool(row["stoch_subindo"])
        if tendencia == 1
        else bool(row["stoch_descendo"])
        if tendencia == -1
        else False
    )
    cruzamento_macd = (
        bool(row["macd_cross_up"])
        if tendencia == 1
        else bool(row["macd_cross_down"])
        if tendencia == -1
        else False
    )
    cruzamento_extremo = (
        bool(row["stoch_cross_up_20"])
        if tendencia == 1
        else bool(row["stoch_cross_down_80"])
        if tendencia == -1
        else False
    )
    fechamento_lado_ma21 = (
        float(row["Fechamento"]) >= float(row["MA21"])
        if tendencia == 1
        else float(row["Fechamento"]) <= float(row["MA21"])
        if tendencia == -1
        else False
    )

    elegibilidade_1 = [
        (tendencia != 0, "definição de tendência"),
        (
            not (
                row["dt"].weekday() == 3
                or "12:00" <= hora <= "13:15"
                or "15:00" <= hora <= "16:59"
            ),
            "horário permitido",
        ),
        (not (75.0 <= separacao <= 175.0), "separação saudável das médias"),
        (
            float(row["atr_relativo"]) <= ATR_RELATIVO_MAX_PORTA_1,
            "volatilidade aceitável",
        ),
    ]
    condicoes_1 = [
        float(row["distancia_ma21"]) <= MAX_DISTANCIA_MA21,
        STOCH_MIN <= float(row["stoch"]) <= STOCH_MAX,
        direcao_stoch,
        fechamento_lado_ma21,
    ]

    elegibilidade_2 = [
        (tendencia != 0, "definição de tendência"),
        (not ("11:45" <= hora <= "12:30"), "horário permitido"),
        (not (240.0 <= amplitude <= 340.0), "amplitude fora da faixa fraca"),
    ]
    condicoes_2 = [
        float(row["distancia_ma21"]) > 200.0,
        variacao_stoch >= VARIACAO_MINIMA_ESTOCASTICO_MACD,
        direcao_stoch,
        cruzamento_macd,
    ]

    elegibilidade_3 = [
        (tendencia != 0, "definição de tendência"),
        (not ("12:30" <= hora <= "13:15"), "horário permitido"),
        (not (279.0 <= amplitude <= 360.0), "amplitude fora da faixa fraca"),
    ]
    condicoes_3 = [
        amplitude > 0.0,
        amplitude > 0.0 and corpo <= 0.70 * amplitude,
        cruzamento_extremo,
    ]

    e1 = all(valor for valor, _ in elegibilidade_1)
    e2 = all(valor for valor, _ in elegibilidade_2)
    e3 = all(valor for valor, _ in elegibilidade_3)
    sinal_direcional = 1 if tendencia == 1 else -1 if tendencia == -1 else 0

    oportunidades = [
        _resultado(
            "Retomada MA21 confirmada",
            1,
            row,
            e1,
            [texto for valor, texto in elegibilidade_1 if not valor],
            condicoes_1,
            [
                "aproximação da MA21",
                "estocástico fora dos extremos",
                "estocástico na direção da tendência",
                "fechamento no lado estrutural da MA21",
            ],
            sinal_direcional if e1 and all(condicoes_1) else 0,
        ),
        _resultado(
            "MACD + Estocástico",
            2,
            row,
            e2,
            [texto for valor, texto in elegibilidade_2 if not valor],
            condicoes_2,
            [
                "afastamento superior a 200 pontos",
                "variação mínima do estocástico",
                "estocástico na direção da tendência",
                "cruzamento do MACD",
            ],
            sinal_direcional if e2 and all(condicoes_2) else 0,
        ),
        _resultado(
            "Saída de Extremo",
            3,
            row,
            e3,
            [texto for valor, texto in elegibilidade_3 if not valor],
            condicoes_3,
            [
                "amplitude válida",
                "corpo sem exaustão",
                "saída da zona extrema do estocástico",
            ],
            sinal_direcional if e3 and all(condicoes_3) else 0,
        ),
    ]
    return sorted(oportunidades, key=lambda item: (-item["progresso"], item["prioridade"]))


def gerar_sinal(row) -> int:
    oportunidades = sorted(
        diagnosticar_oportunidades(row), key=lambda item: item["prioridade"]
    )
    for oportunidade in oportunidades:
        if oportunidade["sinal"] in (-1, 1):
            return oportunidade["sinal"]
    return 0


def diagnosticar_sinal(row):
    oportunidades = diagnosticar_oportunidades(row)
    confirmadas = [item for item in oportunidades if item["sinal"] in (-1, 1)]
    oportunidade = (
        min(confirmadas, key=lambda item: item["prioridade"])
        if confirmadas
        else oportunidades[0]
    )
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


__all__ = ["gerar_sinal", "diagnosticar_sinal", "diagnosticar_oportunidades"]
