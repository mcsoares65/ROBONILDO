"""Entrada MACD + Estocástico — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Entra a favor da tendência quando o preço já está afastado da média de 21
(mais de 200 pontos), o estocástico varia o bastante a favor e o MACD cruza
na mesma direção.

V510 (pedido do dono, 08/10/2026): removido o bloqueio de horário 11:45–12:30, para não perder
oportunidades. Demais condições e limiares inalterados.

Origem: Porta 2 de estrategia/entrada/titular/entrada_tres_portas_v01.py. Extração LITERAL: nenhum limiar, horário ou condição foi
alterado. Isola uma única ideia que hoje só existe combinada com outras num
agregador; não duplica nenhum arquivo existente (Regra 6) porque, sozinha, ela
produz sinais diferentes dos do agregador.
Variações testadas antes desta versão (Regra 11.2): nenhuma.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0 (opcional, V502: diagnosticar_oportunidades(row) -> radar,
sem efeito no sinal). Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""


MIN_DISTANCIA_MA21 = 200.0
VARIACAO_MINIMA_ESTOCASTICO = 4.5


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    amplitude = row["Maximo"] - row["Minimo"]
    if 240.0 <= amplitude <= 340.0:
        return 0
    variacao_stoch = abs(row["stoch"] - row["stoch_prev"])
    direcao_stoch = (row["stoch_subindo"] if tendencia == 1
                     else row["stoch_descendo"] if tendencia == -1 else False)
    cruzamento_macd = (row["macd_cross_up"] if tendencia == 1
                       else row["macd_cross_down"] if tendencia == -1 else False)
    if (row["distancia_ma21"] > MIN_DISTANCIA_MA21
            and variacao_stoch >= VARIACAO_MINIMA_ESTOCASTICO
            and direcao_stoch
            and cruzamento_macd):
        return 1 if tendencia == 1 else -1
    return 0


# ---------------------------------------------------------------------------
# Radar (V502). Mostra no terminal quantas condições já estão confirmadas e a
# próxima que falta. NÃO participa de gerar_sinal() e não altera nenhum limiar:
# é a cópia, para este arquivo, do radar que a porta tinha no titular antigo
# (entrada_tres_portas_v01). Sem I/O, sem estado, sem importar o projeto (Regra 3).
# ---------------------------------------------------------------------------


def _fino(ok, proximidade):
    """V515: 1.0 se a condicao esta atendida; senao a proximidade (0..0,99), para o % do painel
    andar ponto a ponto. Nunca chega a 1.0 sem a condicao atendida."""
    return 1.0 if ok else min(0.99, max(0.0, float(proximidade)))


def _prox_direcao_stoch(row, tendencia):
    """Proximidade da condicao 'estocastico na direcao da tendencia' (delta a favor > 0)."""
    delta = (row["stoch"] - row["stoch_prev"]) * tendencia
    return 1.0 / (1.0 + max(0.0, -delta) / 2.0)


ESCALA_HIST_MACD = 75.0   # pts: |MACD - sinal| tipico (mediana 2026) que da 50% de proximidade do cruzamento

def diagnosticar_oportunidades(row):
    tendencia = row["trend"]
    amplitude = row["Maximo"] - row["Minimo"]
    variacao_stoch = abs(row["stoch"] - row["stoch_prev"])
    direcao_stoch = (row["stoch_subindo"] if tendencia == 1
                     else row["stoch_descendo"] if tendencia == -1 else False)
    cruzamento_macd = (row["macd_cross_up"] if tendencia == 1
                       else row["macd_cross_down"] if tendencia == -1 else False)
    elegibilidade = [
        (tendencia != 0, "definição de tendência"),
        (not (240.0 <= amplitude <= 340.0), "amplitude fora da faixa fraca"),
    ]
    condicoes = [
        (row["distancia_ma21"] > MIN_DISTANCIA_MA21, "afastamento superior a 200 pontos"),
        (variacao_stoch >= VARIACAO_MINIMA_ESTOCASTICO, "variação mínima do estocástico"),
        (bool(direcao_stoch), "estocástico na direção da tendência"),
        (bool(cruzamento_macd), "cruzamento do MACD"),
    ]
    elegivel = all(ok for ok, _ in elegibilidade)
    # V515: proximidade fina de cada condicao (so painel; gerar_sinal nao usa)
    macd_v, sig_v = row.get("macd"), row.get("macd_signal")
    if tendencia != 0 and macd_v is not None and sig_v is not None:
        g = (macd_v - sig_v) * tendencia      # > 0: MACD ja do lado favoravel
        prox_macd = 1.0 / (1.0 + abs(g) / ESCALA_HIST_MACD) if g < 0 else 0.0
    else:
        prox_macd = 0.0
    scores = [
        _fino(row["distancia_ma21"] > MIN_DISTANCIA_MA21, row["distancia_ma21"] / MIN_DISTANCIA_MA21),
        _fino(variacao_stoch >= VARIACAO_MINIMA_ESTOCASTICO, variacao_stoch / VARIACAO_MINIMA_ESTOCASTICO),
        _fino(bool(direcao_stoch), _prox_direcao_stoch(row, tendencia)),
        _fino(bool(cruzamento_macd), prox_macd),
    ]
    confirmadas = sum(bool(ok) for ok, _ in condicoes) if elegivel else 0
    progresso_fino = sum(scores) / len(scores) if elegivel else 0.0
    faltantes = ([t for ok, t in condicoes if not ok] if elegivel
                 else [t for ok, t in elegibilidade if not ok])
    sinal = (1 if tendencia == 1 else -1) if elegivel and all(ok for ok, _ in condicoes) else 0
    faltante = faltantes[0] if faltantes else "nenhuma"
    detalhe = faltante
    bloqueio_horario = False   # V510: a estratégia não tem mais janela de horário bloqueada
    if faltante == "afastamento superior a 200 pontos":
        detalhe = f"afastamento {row['distancia_ma21']:.0f}/200 pts"
    elif faltante == "variação mínima do estocástico":
        detalhe = f"var. estoc. {variacao_stoch:.1f}/4,5"
    return [{
        "estrategia": "MACD + Estocástico",
        "prioridade": 2,
        "direcao": "COMPRA" if tendencia == 1 else "VENDA" if tendencia == -1 else "NEUTRA",
        "sinal": sinal,
        "confirmadas": confirmadas,
        "total": len(condicoes),
        "progresso": progresso_fino,
        "faltantes": faltantes,
        "detalhe": detalhe,
        "bloqueio_horario": bloqueio_horario,
    }]
