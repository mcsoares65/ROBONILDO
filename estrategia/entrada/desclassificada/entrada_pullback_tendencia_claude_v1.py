"""Entrada Pullback de Tendência — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: TENDÊNCIA (preço andando em linha: eficiência >= 0,45 nos
últimos 12 fechamentos).
Ideia única: recuo proporcional dentro de uma perna forte. Numa janela de 12
candles do mesmo dia, em que o preço andou em linha (eficiência de Kaufman >=
0,45), mede a perna entre a mínima e a máxima (alta) e exige: perna >= 2 ATR;
recuo posterior de 25% a 62% da perna; e candle atual que fecha acima da máxima
do candle anterior (retomada). Venda é o espelho. A tendência da MA21/MA50
precisa concordar com a direção.

Premissa (não medida): em tendência eficiente, um recuo raso a moderado seguido
de retomada é melhor ponto de entrada que o fechamento em qualquer ponto da
perna. Não mede distância até a MA21, ao contrário da retomada do titular.
Origem: ideia nova do autor; difere de entrada_retomada_ma21_claude_v1 (que
espera o preço encostar na MA21 com estocástico) — Regra 6. Como usa 12 candles
do mesmo dia, só opera a partir de 11:45.
Variações testadas antes desta versão (Regra 11.2): nenhuma. Limiares fixados
a priori (0,45; 2 ATR; 25%–62%), sem ajuste a histórico.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""

JANELA = 12
EFICIENCIA_MIN = 0.45
PERNA_MIN_ATR = 2.0
RECUO_MIN = 0.25
RECUO_MAX = 0.62


def _eficiencia(fechamentos):
    percurso = sum(abs(b - a) for a, b in zip(fechamentos, fechamentos[1:]))
    return abs(fechamentos[-1] - fechamentos[0]) / percurso if percurso > 0 else 0.0


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    atr = row.get("atr")
    if tendencia == 0 or not atr or atr <= 0:
        return 0
    janela = row.get("ohlc_recentes") or ()
    if len(janela) < JANELA:
        return 0
    janela = janela[-JANELA:]
    dia = janela[-1]["dt"].date()
    if any(c["dt"].date() != dia for c in janela):
        return 0

    fechamentos = [float(c["Fechamento"]) for c in janela]
    if _eficiencia(fechamentos) < EFICIENCIA_MIN:
        return 0
    direcao = 1 if fechamentos[-1] > fechamentos[0] else -1
    if direcao != tendencia:
        return 0
    altas = [float(c["Maximo"]) for c in janela]
    baixas = [float(c["Minimo"]) for c in janela]
    atual, anterior = janela[-1], janela[-2]

    if direcao == 1:
        topo = max(range(len(altas)), key=lambda i: (altas[i], i))
        if topo > len(janela) - 3:                 # precisa de ao menos 2 candles após o topo
            return 0
        fundo = min(baixas[:topo + 1])
        perna = altas[topo] - fundo
        if perna < PERNA_MIN_ATR * atr:
            return 0
        recuo = (altas[topo] - min(baixas[topo + 1:-1])) / perna
        if RECUO_MIN <= recuo <= RECUO_MAX and float(atual["Fechamento"]) > float(anterior["Maximo"]):
            return 1
        return 0

    fundo_i = min(range(len(baixas)), key=lambda i: (baixas[i], -i))
    if fundo_i > len(janela) - 3:
        return 0
    topo_v = max(altas[:fundo_i + 1])
    perna = topo_v - baixas[fundo_i]
    if perna < PERNA_MIN_ATR * atr:
        return 0
    recuo = (max(altas[fundo_i + 1:-1]) - baixas[fundo_i]) / perna
    if RECUO_MIN <= recuo <= RECUO_MAX and float(atual["Fechamento"]) < float(anterior["Minimo"]):
        return -1
    return 0
