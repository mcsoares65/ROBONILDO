"""Entrada Abertura Continuação — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: ABERTURA (primeiros candles do pregão).
Ideia única: quando os três primeiros candles do dia (09:00, 09:15, 09:30)
formam um arranque direcional forte, o fechamento do candle das 09:30 (decisão
às 09:45) entra a favor do arranque. Exige: deslocamento líquido da abertura do
dia até o fechamento >= 1,0 ATR; o candle das 09:30 na mesma direção e fechando
no terço final do seu próprio intervalo; e o preço do lado certo da MA21.
É a única ideia de entrada desenhada para a abertura: os candles 09:00 e 09:15
são bloqueados pelo motor (JANELAS_BLOQUEADAS), então só o candle das 09:30
pode gerar sinal, no máximo um por dia.

Premissa (não medida): arranque forte na abertura tende a continuar por mais
alguns candles em vez de devolver tudo de imediato.
Origem: ideia nova do autor (continuação do arranque de abertura); não é
extração de nenhum cartucho existente e não repete a lógica de nenhum deles
(Regra 6: nenhum outro cartucho usa o arranque dos três primeiros candles).
Variações testadas antes desta versão (Regra 11.2): nenhuma. Limiares fixados
a priori (1,0 ATR; 70% do intervalo do candle), sem ajuste a histórico.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""

DESLOCAMENTO_MIN_ATR = 1.0
FECHAMENTO_NO_EXTREMO_MIN = 0.70    # posição do fechamento dentro do candle das 09:30
HORA_INICIO = "09:30"
HORA_FIM = "09:44"
CANDLES_ABERTURA = 3


def gerar_sinal(row) -> int:
    hora = row["dt"].strftime("%H:%M")
    if not (HORA_INICIO <= hora <= HORA_FIM):
        return 0
    atr = row.get("atr")
    if not atr or atr <= 0:
        return 0

    dia = row["dt"].date()
    janela = [c for c in (row.get("ohlc_recentes") or ()) if c["dt"].date() == dia]
    if len(janela) != CANDLES_ABERTURA:
        return 0

    abertura_dia = float(janela[0]["Abertura"])
    ultimo = janela[-1]
    deslocamento = float(ultimo["Fechamento"]) - abertura_dia
    if abs(deslocamento) < DESLOCAMENTO_MIN_ATR * atr:
        return 0

    alta, baixa = float(ultimo["Maximo"]), float(ultimo["Minimo"])
    amplitude = alta - baixa
    if amplitude <= 0:
        return 0
    posicao_fechamento = (float(ultimo["Fechamento"]) - baixa) / amplitude
    ma21 = row["MA21"]
    fechamento = float(ultimo["Fechamento"])

    if (deslocamento > 0 and float(ultimo["Fechamento"]) > float(ultimo["Abertura"])
            and posicao_fechamento >= FECHAMENTO_NO_EXTREMO_MIN and fechamento > ma21):
        return 1
    if (deslocamento < 0 and float(ultimo["Fechamento"]) < float(ultimo["Abertura"])
            and posicao_fechamento <= 1.0 - FECHAMENTO_NO_EXTREMO_MIN and fechamento < ma21):
        return -1
    return 0
