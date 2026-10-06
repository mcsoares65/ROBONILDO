"""Entrada Fim de Tarde Rompimento — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: FIM DE TARDE (a partir das 16:30).
Ideia única: no fim da tarde, com mercado calmo e tendência definida, o
rompimento da máxima (ou mínima) dos 8 candles anteriores a favor da tendência
tende a seguir a deriva até o fechamento. Compra quando: tendência de alta
(MA21 > MA50), fechamento acima da MA21 e acima da máxima dos 8 candles
anteriores, RSI entre 55 e 75 (força sem exaustão) e ATR relativo < 1,25
(sem agitação). Venda é o espelho. Só vale entre 16:30 e 17:45.

Premissa (não medida): sem agitação, quem rompe no fim do dia a favor da
tendência encontra pouca oferta contrária até o encerramento.
Origem: ideia nova do autor; não extrai nenhum cartucho existente (a entrada
titular bloqueia 15:00–16:59 e usa retomada/estocástico, não rompimento de
8 candles) — Regra 6.
Variações testadas antes desta versão (Regra 11.2): nenhuma. Limiares fixados
a priori (8 candles; RSI 55–75; ATR relativo 1,25), sem ajuste a histórico.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""

HORA_INICIO = "16:30"
HORA_FIM = "17:45"
CANDLES_ROMPIMENTO = 8
RSI_ALTA = (55.0, 75.0)
RSI_BAIXA = (25.0, 45.0)
ATR_RELATIVO_MAX = 1.25


def gerar_sinal(row) -> int:
    hora = row["dt"].strftime("%H:%M")
    if not (HORA_INICIO <= hora <= HORA_FIM):
        return 0
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    atr_rel = row.get("atr_relativo")
    rsi = row.get("rsi")
    if atr_rel is None or rsi is None or atr_rel >= ATR_RELATIVO_MAX:
        return 0

    janela = (row.get("ohlc_recentes") or ())
    if len(janela) < CANDLES_ROMPIMENTO + 1:
        return 0
    anteriores = janela[-(CANDLES_ROMPIMENTO + 1):-1]
    fechamento = row["Fechamento"]

    if tendencia == 1 and fechamento > row["MA21"]:
        if (fechamento > max(float(c["Maximo"]) for c in anteriores)
                and RSI_ALTA[0] <= rsi <= RSI_ALTA[1]):
            return 1
    if tendencia == -1 and fechamento < row["MA21"]:
        if (fechamento < min(float(c["Minimo"]) for c in anteriores)
                and RSI_BAIXA[0] <= rsi <= RSI_BAIXA[1]):
            return -1
    return 0
