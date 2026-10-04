"""Entrada Retorno à Média — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: ESTICADO (preço a 2 ATR ou mais da MA21).
Ideia única: contra-tendência de exaustão. Quando o preço está esticado a 2 ATR
ou mais da MA21, o RSI está em extremo (<= 25 ou >= 75) e já virou, e o candle
confirma a virada (fecha na direção contrária ao esticamento e além do
fechamento anterior), entra apostando no retorno em direção à média.
Compra: fechamento <= MA21 - 2 ATR, RSI <= 25 e subindo, candle de alta que
fecha acima do fechamento anterior. Venda é o espelho.

Premissa (não medida): esticamento extremo com exaustão confirmada tende a
devolver parte do movimento antes de continuar. É deliberadamente CONTRÁRIA à
tendência: se a premissa for falsa, o stop da saída limita a perda.
Origem: ideia nova do autor; difere de entrada_saida_extremo_claude_v1 (que
entra A FAVOR da tendência quando o estocástico sai do extremo) e de
entrada_deepseek_v1 (continuação por RSI): aqui a entrada é CONTRA o
esticamento e exige 2 ATR de distância da média — Regra 6.
Variações testadas antes desta versão (Regra 11.2): nenhuma. Limiares fixados
a priori (2 ATR; RSI 25/75), sem ajuste a histórico.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""

ESTICAMENTO_MIN_ATR = 2.0
RSI_SOBREVENDIDO = 25.0
RSI_SOBRECOMPRADO = 75.0


def gerar_sinal(row) -> int:
    atr = row.get("atr")
    rsi = row.get("rsi")
    if not atr or atr <= 0 or rsi is None:
        return 0
    janela = row.get("ohlc_recentes") or ()
    if len(janela) < 2:
        return 0
    anterior = janela[-2]
    fechamento, abertura = row["Fechamento"], row["Abertura"]
    ma21 = row["MA21"]

    if (fechamento <= ma21 - ESTICAMENTO_MIN_ATR * atr
            and rsi <= RSI_SOBREVENDIDO and row["rsi_subindo"]
            and fechamento > abertura and fechamento > float(anterior["Fechamento"])):
        return 1
    if (fechamento >= ma21 + ESTICAMENTO_MIN_ATR * atr
            and rsi >= RSI_SOBRECOMPRADO and row["rsi_descendo"]
            and fechamento < abertura and fechamento < float(anterior["Fechamento"])):
        return -1
    return 0
