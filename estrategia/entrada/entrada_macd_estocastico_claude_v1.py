"""Entrada MACD + Estocástico — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Entra a favor da tendência quando o preço já está afastado da média de 21
(mais de 200 pontos), o estocástico varia o bastante a favor e o MACD cruza
na mesma direção.

Origem: Porta 2 de estrategia/entrada/titular/entrada_grok_3_v1.py. Extração LITERAL: nenhum limiar, horário ou condição foi
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


MIN_DISTANCIA_MA21 = 200.0
VARIACAO_MINIMA_ESTOCASTICO = 4.5


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    hora = row["dt"].strftime("%H:%M")
    amplitude = row["Maximo"] - row["Minimo"]
    if "11:45" <= hora <= "12:30" or (240.0 <= amplitude <= 340.0):
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
