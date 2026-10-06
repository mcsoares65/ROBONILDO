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

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
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
