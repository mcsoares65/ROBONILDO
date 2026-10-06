"""Entrada Compressão de Amplitude — v02 (v01 corrigida).

Autoria: a ideia e os parâmetros são da v01 (DeepSeek, em sessão operada por Marcio
Soares; ver desclassificada/entrada_compressao_amplitude_v01.py). A correção de uma
falha que impedia qualquer sinal é de Claude (Anthropic), a pedido do dono. Revisão
humana antes do teste oficial: pendente. O `v02` é a versão da estratégia, não a VERSAO
do projeto.

Ideia: depois de um encolhimento das amplitudes (as 4 últimas velas com amplitude média
menos de 75% da média das 8 anteriores), entra a favor da tendência (MA21 vs MA50) quando
o fechamento rompe o máximo (compra) ou o mínimo (venda) das 12 velas anteriores por pelo
menos 0,05 ATR, com RSI a favor (>= 50 na compra, <= 50 na venda), ATR relativo entre 0,85
e 1,60 e corpo do candle de no máximo 85% da amplitude.

Correção (única mudança em relação à v01): na v01 o máximo e o mínimo da compressão eram
calculados com as últimas 12 velas INCLUINDO o candle atual (ohlc_recentes[-1]). Como o
fechamento nunca passa do máximo do próprio candle, a v01 jamais emitia sinal. Na v02 o
intervalo rompido são as 12 velas anteriores ao candle atual. Nenhum limiar foi alterado.

Variações testadas antes desta versão (Regra 11.2): 2, ambas sobre 2020-2026 e ambas
declaradas aqui: A (esta: só o intervalo rompido exclui o candle atual) e B (A, e a medida
de compressão também usa só velas anteriores). A foi fixada como a correção mínima antes
de ver os resultados; B só foi medida para comparação. Nenhum limiar foi ajustado.
Medição (saída titular, preços reescalados à volatilidade de 2026, custo R$ 0,50 por
operação, sem slippage; acumulado = resultado - |drawdown|):
              2020    2021    2022    2023    2024    2025 |  2026   2020-25: ops  R$/op    t
  v02 (A)    -1846    -301    2726     377    1777     861 |  -274              211   37,7  3,01
  B          -226    -1180    2503     203    2320      19 | -1622              279   29,7  2,92
Sobreposição com a compressão por faixa em ATR (entrada_compressao_faixa_v01): 2 a 9
entradas por ano coincidem; não é a mesma regra.
Leitura honesta: o t de 3,0 em 2020-25 se destaca entre as hipóteses já medidas (o máximo
esperado ao acaso entre 15 a 20 testes fica em torno de 1,8), mas 2020-2025 já foi visto em
rankings agregados, 2026 é negativo (-274) e há poucas operações por ano. Pede Regra 10
(perturbação de ±10 a 30%) e acompanhamento à frente antes de qualquer promoção.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3): as constantes abaixo são cópias.
"""

JANELA_COMPRESSAO = 12
RAZAO_COMPRESSAO_MAX = 0.75
ATR_REL_MIN = 0.85
ATR_REL_MAX = 1.60
RSI_COMPRA_MIN = 50.0
RSI_VENDA_MAX = 50.0
CORPO_MAX = 0.85
FOLGA_ATR_ROMPIMENTO = 0.05

_N_RECENTE = 4
_N_ANTERIOR = 8


def _amplitude(candle) -> float:
    return float(candle["Maximo"]) - float(candle["Minimo"])


def _media_amplitudes(candles) -> float:
    if not candles:
        return 0.0
    return sum(_amplitude(c) for c in candles) / len(candles)


def _ha_compressao(ohlc) -> bool:
    janela = ohlc[-JANELA_COMPRESSAO:]
    recentes = janela[-_N_RECENTE:]
    anteriores = janela[:-_N_RECENTE][-_N_ANTERIOR:]
    if not anteriores:
        return False
    media_anterior = _media_amplitudes(anteriores)
    if media_anterior <= 0:
        return False
    return (_media_amplitudes(recentes) / media_anterior) < RAZAO_COMPRESSAO_MAX


def _corpo_relativo(row) -> float:
    amplitude = float(row["Maximo"]) - float(row["Minimo"])
    if amplitude <= 0:
        return 1.0
    return abs(float(row["Fechamento"]) - float(row["Abertura"])) / amplitude


def gerar_sinal(row) -> int:
    try:
        tendencia = int(row.get("trend", 0))
        atr = row.get("atr")
        atr_rel = row.get("atr_relativo")
        rsi = row.get("rsi")
        ohlc = row.get("ohlc_recentes")
    except Exception:
        return 0

    if tendencia == 0:
        return 0
    if atr is None or atr <= 0:
        return 0
    if atr_rel is None or atr_rel < ATR_REL_MIN or atr_rel > ATR_REL_MAX:
        return 0
    if rsi is None:
        return 0
    # 12 velas anteriores + o candle atual
    if not ohlc or len(ohlc) < JANELA_COMPRESSAO + 1:
        return 0
    if _corpo_relativo(row) > CORPO_MAX:
        return 0
    if not _ha_compressao(ohlc):
        return 0

    anteriores = ohlc[-(JANELA_COMPRESSAO + 1):-1]  # correção v02: exclui o candle atual
    maximo = max(float(c["Maximo"]) for c in anteriores)
    minimo = min(float(c["Minimo"]) for c in anteriores)
    fechamento = float(row["Fechamento"])
    folga = FOLGA_ATR_ROMPIMENTO * float(atr)

    if tendencia == 1 and fechamento >= maximo + folga and rsi >= RSI_COMPRA_MIN:
        return 1
    if tendencia == -1 and fechamento <= minimo - folga and rsi <= RSI_VENDA_MAX:
        return -1
    return 0
