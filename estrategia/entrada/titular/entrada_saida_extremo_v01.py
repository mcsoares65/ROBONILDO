"""Entrada Saída de Extremo — v01.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. Renomeada na V492 para o padrão
`entrada_<estrategia>_v<NN>.py` (antes: entrada_saida_extremo_claude_v1); o
conteúdo não mudou. O `v01` é a versão da estratégia, não a VERSAO do projeto.

Entra a favor da tendência quando o estocástico sai da zona extrema (cruza 20
para cima na alta, 80 para baixo na baixa) num candle sem exaustão de corpo.

Origem: Porta 3 de estrategia/entrada/titular/entrada_tres_portas_v01.py. Extração LITERAL: nenhum limiar, horário ou condição foi
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


CORPO_MAXIMO_PROPORCAO = 0.70


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    hora = row["dt"].strftime("%H:%M")
    amplitude = row["Maximo"] - row["Minimo"]
    corpo = abs(row["Fechamento"] - row["Abertura"])
    if "12:30" <= hora <= "13:15" or (279.0 <= amplitude <= 360.0):
        return 0
    cruzamento_extremo = (row["stoch_cross_up_20"] if tendencia == 1
                          else row["stoch_cross_down_80"] if tendencia == -1 else False)
    if (amplitude > 0
            and corpo <= CORPO_MAXIMO_PROPORCAO * amplitude
            and cruzamento_extremo):
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

def diagnosticar_oportunidades(row):
    tendencia = row["trend"]
    hora = row["dt"].strftime("%H:%M")
    amplitude = row["Maximo"] - row["Minimo"]
    corpo = abs(row["Fechamento"] - row["Abertura"])
    cruzamento_extremo = (row["stoch_cross_up_20"] if tendencia == 1
                          else row["stoch_cross_down_80"] if tendencia == -1 else False)
    elegibilidade = [
        (tendencia != 0, "definição de tendência"),
        (not ("12:30" <= hora <= "13:15"), "horário permitido"),
        (not (279.0 <= amplitude <= 360.0), "amplitude fora da faixa fraca"),
    ]
    condicoes = [
        (amplitude > 0, "amplitude válida"),
        (amplitude > 0 and corpo <= CORPO_MAXIMO_PROPORCAO * amplitude, "corpo sem exaustão"),
        (bool(cruzamento_extremo), "saída da zona extrema do estocástico"),
    ]
    elegivel = all(ok for ok, _ in elegibilidade)
    # V515: proximidade fina de cada condicao (so painel; gerar_sinal nao usa)
    proporcao = (corpo / amplitude) if amplitude > 0 else 1.0
    nivel_extremo = 20.0 if tendencia == 1 else 80.0
    scores = [
        1.0 if amplitude > 0 else 0.0,
        _fino(amplitude > 0 and corpo <= CORPO_MAXIMO_PROPORCAO * amplitude,
              1.0 - (proporcao - CORPO_MAXIMO_PROPORCAO) / (1.0 - CORPO_MAXIMO_PROPORCAO)),
        _fino(bool(cruzamento_extremo), 1.0 - abs(row["stoch"] - nivel_extremo) / 80.0),
    ]
    confirmadas = sum(bool(ok) for ok, _ in condicoes) if elegivel else 0
    progresso_fino = sum(scores) / len(scores) if elegivel else 0.0
    faltantes = ([t for ok, t in condicoes if not ok] if elegivel
                 else [t for ok, t in elegibilidade if not ok])
    sinal = (1 if tendencia == 1 else -1) if elegivel and all(ok for ok, _ in condicoes) else 0
    faltante = faltantes[0] if faltantes else "nenhuma"
    detalhe = faltante
    bloqueio_horario = faltante == "horário permitido"
    if bloqueio_horario:
        detalhe = "BLOQUEADA ATÉ 13:30"
    elif faltante == "corpo sem exaustão":
        proporcao_corpo = (corpo / amplitude * 100.0) if amplitude > 0 else 0.0
        detalhe = f"corpo {proporcao_corpo:.0f}% (máx. 70%)"
    return [{
        "estrategia": "Saída de Extremo",
        "prioridade": 3,
        "direcao": "COMPRA" if tendencia == 1 else "VENDA" if tendencia == -1 else "NEUTRA",
        "sinal": sinal,
        "confirmadas": confirmadas,
        "total": len(condicoes),
        "progresso": progresso_fino,
        "faltantes": faltantes,
        "detalhe": detalhe,
        "bloqueio_horario": bloqueio_horario,
    }]
