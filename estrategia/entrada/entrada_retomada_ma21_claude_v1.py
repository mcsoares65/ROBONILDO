"""Entrada Retomada MA21 — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Compra ou vende a favor da tendência quando o preço volta até perto da média
móvel de 21 candles (retomada) com o estocástico fora dos extremos e a favor.

Origem: Porta 1 de estrategia/entrada/titular/entrada_grok_3_v1.py. Extração LITERAL: nenhum limiar, horário ou condição foi
alterado. Isola uma única ideia que hoje só existe combinada com outras num
agregador; não duplica nenhum arquivo existente (Regra 6) porque, sozinha, ela
produz sinais diferentes dos do agregador.
Variações testadas antes desta versão (Regra 11.2): nenhuma.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""


MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
ATR_RELATIVO_MAX = 1.40
SEPARACAO_FRACA_MIN = 75.0
SEPARACAO_FRACA_MAX = 175.0


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    hora = row["dt"].strftime("%H:%M")
    separacao = abs(row["MA21"] - row["MA50"])
    bloqueado = (
        row["dt"].weekday() == 3
        or "12:00" <= hora <= "13:15"
        or "15:00" <= hora <= "16:59"
    )
    if bloqueado or (SEPARACAO_FRACA_MIN <= separacao <= SEPARACAO_FRACA_MAX):
        return 0
    if row["atr_relativo"] > ATR_RELATIVO_MAX:
        return 0
    direcao_stoch = (row["stoch_subindo"] if tendencia == 1
                     else row["stoch_descendo"] if tendencia == -1 else False)
    if (row["distancia_ma21"] <= MAX_DISTANCIA_MA21
            and STOCH_MIN <= row["stoch"] <= STOCH_MAX
            and direcao_stoch):
        return 1 if tendencia == 1 else -1
    return 0
