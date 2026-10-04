"""Entrada Reversão no Range — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Cenário de origem: LATERAL (preço vai e volta sem sair do lugar: eficiência
<= 0,20 nos últimos 12 fechamentos; aqui exigida <= 0,30 para tolerar a borda).
Ideia única: operar contra a borda de um intervalo lateral. Define o range
pelos 11 candles anteriores (mesmo dia): largura entre 1,5 e 4 ATR. Compra
quando o fechamento está no 20% inferior do range (sem ter rompido mais de
0,25 ATR abaixo dele), o estocástico está <= 30 e subindo e o candle é de alta.
Venda é o espelho na borda superior. Só opera com ATR relativo < 1,25.

Premissa (não medida): em mercado sem direção, as bordas do range seguram e o
preço volta para o meio. Se o range romper, o stop da saída limita a perda.
Origem: ideia nova do autor; difere de entrada_macd_estocastico_claude_v1 (que
só combina MACD e estocástico, sem noção de range) e de
entrada_saida_extremo_claude_v1 (a favor da tendência, sem noção de range) —
Regra 6. Como usa 12 candles do mesmo dia, só opera a partir de 11:45.
Variações testadas antes desta versão (Regra 11.2): 1 (limiares do rascunho
inicial: eficiência 0,25, borda 15%, estocástico 25/75) só geravam 16 sinais
em 183 pregões; relaxados para os valores abaixo olhando APENAS a frequência
de sinais, nunca o resultado financeiro.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""

JANELA = 12
EFICIENCIA_MAX = 0.30
LARGURA_MIN_ATR = 1.5
LARGURA_MAX_ATR = 4.0
ZONA_BORDA = 0.20
ROMPIMENTO_TOLERADO_ATR = 0.25
STOCH_COMPRA = 30.0
STOCH_VENDA = 70.0
ATR_RELATIVO_MAX = 1.25


def _eficiencia(fechamentos):
    percurso = sum(abs(b - a) for a, b in zip(fechamentos, fechamentos[1:]))
    return abs(fechamentos[-1] - fechamentos[0]) / percurso if percurso > 0 else 0.0


def gerar_sinal(row) -> int:
    atr = row.get("atr")
    atr_rel = row.get("atr_relativo")
    if not atr or atr <= 0 or atr_rel is None or atr_rel >= ATR_RELATIVO_MAX:
        return 0
    janela = row.get("ohlc_recentes") or ()
    if len(janela) < JANELA:
        return 0
    janela = janela[-JANELA:]
    dia = janela[-1]["dt"].date()
    if any(c["dt"].date() != dia for c in janela):
        return 0
    if _eficiencia([float(c["Fechamento"]) for c in janela]) > EFICIENCIA_MAX:
        return 0

    anteriores = janela[:-1]
    topo = max(float(c["Maximo"]) for c in anteriores)
    fundo = min(float(c["Minimo"]) for c in anteriores)
    largura = topo - fundo
    if not (LARGURA_MIN_ATR * atr <= largura <= LARGURA_MAX_ATR * atr):
        return 0

    fechamento, abertura = row["Fechamento"], row["Abertura"]
    stoch = row["stoch"]
    tolerancia = ROMPIMENTO_TOLERADO_ATR * atr

    if (fundo - tolerancia <= fechamento <= fundo + ZONA_BORDA * largura
            and stoch <= STOCH_COMPRA and row["stoch_subindo"] and fechamento > abertura):
        return 1
    if (topo - ZONA_BORDA * largura <= fechamento <= topo + tolerancia
            and stoch >= STOCH_VENDA and row["stoch_descendo"] and fechamento < abertura):
        return -1
    return 0
