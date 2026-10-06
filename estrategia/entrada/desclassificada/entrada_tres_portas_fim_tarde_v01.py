# DESCLASSIFICADA pela Regra 16 (V490): agregador de ideias por OU. Fora do ranking.
# Ver conselho/2026-10-05-AE.txt. Mantida so como referencia/paridade; nao alterada.
"""Entrada Composta (três portas Grok + rompimento de fim de tarde) — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Agregador de quatro portas, em ordem de prioridade (a primeira que sinalizar
decide; só uma posição por vez, então não há conflito):
  1. Retomada MA21           — entrada_retomada_ma21_v01 / porta 1 da grok_3
  2. MACD + Estocástico      — entrada_macd_estocastico_v01 / porta 2
  3. Saída de Extremo        — entrada_saida_extremo_claude_v1 / porta 3
  4. Rompimento fim de tarde — entrada_fim_tarde_rompimento_v01

As portas 1–3 reproduzem literalmente a entrada titular entrada_tres_portas_v01
(mesmos limiares e prioridade); a 4ª só atua quando as anteriores não
sinalizam. Nenhum limiar novo foi criado.

Por que só quatro: em janeiro–junho/2026, para toda outra entrada que dá
resultado positivo (chatgpt_v19/v21, deepseek_v5, gemini_V20, grok_32/4/v6,
manus_v1/v2, claude_v1) o "grok_3 OU ela" é igual ao grok_3 sozinho: tudo que
elas sinalizam a grok_3 já sinaliza. A única que acrescenta sinais é a de fim de
tarde (+9 operações, +122 de acumulado no período de desenho — dentro do ruído).

Variações testadas antes desta versão (Regra 11.2): 15 uniões "grok_3 OU X"
(só no período de desenho, jan–jun/2026); a 4ª porta foi a única com ganho.
Resultado (saída titular chatgpt_v4, motor V467, acumulado = resultado − |dd|):
  desenho jan–jun/2026: 10.394 (grok_3: 10.273), 135 ops contra 126
  holdout jul–out/2026:  4.016 (grok_3:  4.057),  70 ops contra  61  ← não supera
  2023–24 (já visto antes): −660 (grok_3: −2.418), 563 ops contra 482
Leitura honesta: empate no holdout de 2026; a vantagem em 2023–24 é uma
evidência a favor, mas de período já conhecido e ainda negativo no total.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3): as constantes abaixo são cópias.
"""

# Porta 4 (entrada_fim_tarde_rompimento_v01)
FT_HORA_INICIO = "16:30"
FT_HORA_FIM = "17:45"
FT_CANDLES_ROMPIMENTO = 8
FT_RSI_ALTA = (55.0, 75.0)
FT_RSI_BAIXA = (25.0, 45.0)
FT_ATR_RELATIVO_MAX = 1.25


def _porta_retomada_ma21(row, tendencia, hora, direcao_stoch):
    separacao = abs(row["MA21"] - row["MA50"])
    liberado = (
        tendencia != 0
        and not (row["dt"].weekday() == 3 or "12:00" <= hora <= "13:15"
                 or "15:00" <= hora <= "16:59")
        and not (75.0 <= separacao <= 175.0)
        and row["atr_relativo"] <= 1.40
    )
    if liberado and (row["distancia_ma21"] <= 90.0
                     and 16.5 <= row["stoch"] <= 83.5 and direcao_stoch):
        return tendencia
    return 0


def _porta_macd_estocastico(row, tendencia, hora, amplitude, direcao_stoch):
    variacao_stoch = abs(row["stoch"] - row["stoch_prev"])
    cruzamento_macd = (row["macd_cross_up"] if tendencia == 1
                       else row["macd_cross_down"] if tendencia == -1 else False)
    liberado = (
        tendencia != 0
        and not ("11:45" <= hora <= "12:30")
        and not (240.0 <= amplitude <= 340.0)
    )
    if liberado and (row["distancia_ma21"] > 200.0 and variacao_stoch >= 4.5
                     and direcao_stoch and cruzamento_macd):
        return tendencia
    return 0


def _porta_saida_extremo(row, tendencia, hora, amplitude):
    corpo = abs(row["Fechamento"] - row["Abertura"])
    cruzamento_extremo = (row["stoch_cross_up_20"] if tendencia == 1
                          else row["stoch_cross_down_80"] if tendencia == -1 else False)
    liberado = (
        tendencia != 0
        and not ("12:30" <= hora <= "13:15")
        and not (279.0 <= amplitude <= 360.0)
    )
    if liberado and (amplitude > 0 and corpo <= 0.70 * amplitude and cruzamento_extremo):
        return tendencia
    return 0


def _porta_fim_tarde(row, tendencia, hora):
    if not (FT_HORA_INICIO <= hora <= FT_HORA_FIM) or tendencia == 0:
        return 0
    atr_rel = row.get("atr_relativo")
    rsi = row.get("rsi")
    if atr_rel is None or rsi is None or atr_rel >= FT_ATR_RELATIVO_MAX:
        return 0
    janela = row.get("ohlc_recentes") or ()
    if len(janela) < FT_CANDLES_ROMPIMENTO + 1:
        return 0
    anteriores = janela[-(FT_CANDLES_ROMPIMENTO + 1):-1]
    fechamento = row["Fechamento"]
    if tendencia == 1 and fechamento > row["MA21"]:
        if (fechamento > max(float(c["Maximo"]) for c in anteriores)
                and FT_RSI_ALTA[0] <= rsi <= FT_RSI_ALTA[1]):
            return 1
    if tendencia == -1 and fechamento < row["MA21"]:
        if (fechamento < min(float(c["Minimo"]) for c in anteriores)
                and FT_RSI_BAIXA[0] <= rsi <= FT_RSI_BAIXA[1]):
            return -1
    return 0


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    hora = row["dt"].strftime("%H:%M")
    amplitude = row["Maximo"] - row["Minimo"]
    direcao_stoch = (row["stoch_subindo"] if tendencia == 1
                     else row["stoch_descendo"] if tendencia == -1 else False)
    for sinal in (
        _porta_retomada_ma21(row, tendencia, hora, direcao_stoch),
        _porta_macd_estocastico(row, tendencia, hora, amplitude, direcao_stoch),
        _porta_saida_extremo(row, tendencia, hora, amplitude),
    ):
        if sinal in (-1, 1):
            return sinal
    return _porta_fim_tarde(row, tendencia, hora)
