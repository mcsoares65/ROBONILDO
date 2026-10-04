"""Entrada Pausa Após Impulso — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: VOLÁTIL (ATR >= 1,25x a média de 50 candles).
Ideia única: em mercado agitado, um candle de impulso seguido de um candle de
pausa curto que segura acima do meio do impulso indica que o movimento só
respirou; entra no fechamento da pausa, a favor do impulso.
Impulso (candle anterior): amplitude >= 1,2 ATR, corpo >= 60% da amplitude e
fechamento no quarto final do candle (alta) ou inicial (baixa). Pausa (candle
atual): amplitude <= 0,8 ATR e sem devolver mais da metade do impulso (mínima
da pausa >= meio do impulso na alta; máxima <= meio na baixa). Só opera com
ATR relativo >= 1,25.

Premissa (não medida): em regime agitado, impulso forte com pausa rasa tende a
continuar antes de reverter.
Origem: ideia nova do autor; nenhum cartucho existente usa o par impulso+pausa
(Regra 6).
Variações testadas antes desta versão (Regra 11.2): 1 (limiares do rascunho
inicial: impulso 1,5 ATR, fechamento no 1/5 final e pausa 0,7 ATR) só geravam
8 sinais em 183 pregões; relaxados para os valores abaixo olhando APENAS a
frequência de sinais, nunca o resultado financeiro.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""

ATR_RELATIVO_MIN = 1.25
IMPULSO_AMPLITUDE_MIN_ATR = 1.2
IMPULSO_CORPO_MIN = 0.60
IMPULSO_FECHAMENTO_EXTREMO = 0.75      # fechamento no 1/4 final do candle
PAUSA_AMPLITUDE_MAX_ATR = 0.8


def gerar_sinal(row) -> int:
    atr = row.get("atr")
    atr_rel = row.get("atr_relativo")
    if not atr or atr <= 0 or atr_rel is None or atr_rel < ATR_RELATIVO_MIN:
        return 0
    janela = row.get("ohlc_recentes") or ()
    if len(janela) < 2:
        return 0
    impulso, pausa = janela[-2], janela[-1]
    if impulso["dt"].date() != pausa["dt"].date():
        return 0

    i_alta, i_baixa = float(impulso["Maximo"]), float(impulso["Minimo"])
    i_abertura, i_fechamento = float(impulso["Abertura"]), float(impulso["Fechamento"])
    amplitude = i_alta - i_baixa
    if amplitude < IMPULSO_AMPLITUDE_MIN_ATR * atr:
        return 0
    if abs(i_fechamento - i_abertura) < IMPULSO_CORPO_MIN * amplitude:
        return 0

    p_alta, p_baixa = float(pausa["Maximo"]), float(pausa["Minimo"])
    if p_alta - p_baixa > PAUSA_AMPLITUDE_MAX_ATR * atr:
        return 0
    meio = (i_alta + i_baixa) / 2.0
    posicao = (i_fechamento - i_baixa) / amplitude

    if i_fechamento > i_abertura and posicao >= IMPULSO_FECHAMENTO_EXTREMO and p_baixa >= meio:
        return 1
    if i_fechamento < i_abertura and posicao <= 1.0 - IMPULSO_FECHAMENTO_EXTREMO and p_alta <= meio:
        return -1
    return 0
