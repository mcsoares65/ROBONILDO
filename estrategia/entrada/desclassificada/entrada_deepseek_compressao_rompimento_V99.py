# DESCLASSIFICADA (V493): nunca emite sinal. O maximo/minimo da "compressao" inclui o candle atual
# (ohlc_recentes[-1]), entao o fechamento nunca supera o maximo + folga. Ver CHANGELOG V493.
"""
entrada_deepseek_compressao_rompimento_V99.py

Autor: DeepSeek (IA), revisado por humano antes da submissão.
Numeração V99 = própria do autor; NÃO é a VERSAO do projeto (versionamento.py).

Ideia
-----
Compressão de volatilidade + rompimento confirmado, com filtro de regime.

Tese (compliance Regra 11.3 — nada depende de data, evento ou preço absoluto):
  Quando a amplitude recente ENCOLHE de forma significativa (mercado "comprimido")
  e o preço rompe o range dessa compressão NA DIREÇÃO da tendência estrutural
  (MA21 vs MA50), a probabilidade histórica de continuação é maior do que a de
  reversão — desde que o regime de volatilidade seja saudável (nem morto, nem
  caótico) e o candle de rompimento não seja um marubozu já esticado.

Contrato (motor.py V486)
------------------------
  gerar_sinal(row) -> 1 (compra) | -1 (venda) | 0 (nada)

Campos de `row` usados (todos vêm de motor.construir_row — nenhum inventado):
  row["Abertura"], row["Maximo"], row["Minimo"], row["Fechamento"]
  row["MA21"], row["MA50"], row["trend"]
  row["atr"], row["atr_relativo"]
  row["rsi"]
  row["ohlc_recentes"]   (tupla imutável com até 96 candles fechados)

Sem I/O. Sem import de módulo do projeto. Sem estado global. Sem data/valor absoluto.

Parâmetros (relativos — a Regra 10 pode perturbá-los em ±10–30% sem quebrar a tese):
  JANELA_COMPRESSAO     = 12   candles usados para medir a compressão
  RAZAO_COMPRESSAO_MAX  = 0.75 amplitude recente / amplitude anterior < 0.75
  ATR_REL_MIN          = 0.85  regime nem morto (evita lateral rasteira)
  ATR_REL_MAX          = 1.60  regime nem caótico
  RSI_COMPRA_MIN       = 50.0  RSI a favor da compra
  RSI_VENDA_MAX        = 50.0  RSI a favor da venda
  CORPO_MAX            = 0.85  |Fech-Aber| / (Max-Min) — evita marubozu esticado
  FOLGA_ATR_ROMPIMENTO = 0.05  rompimento tem que superar o range por 0.05 ATR

Declaração (Termo de concordância, versão 8) — itens:
  1. Respeita o contrato gerar_sinal(row) -> int sem exceções.         OK
  2. Usa apenas campos documentados em motor.construir_row().         OK
  3. Não importa módulo do projeto, não abre arquivo, não usa rede.    OK
  4. Nenhuma validação é alegada sem ter rodado o motor oficial; este  OK
     arquivo NÃO afirma resultado próprio (Regra 4).
  5. Autoria: IA (DeepSeek), revisado por humano.                     OK
  6. Não duplica arquivo existente em estrategia/entrada/.            OK
  7. V99 = numeração própria do autor. Declaração de variações: 1     OK
     variante (esta). Sem data/estrutura específica do dataset.
  8. Pendente de PR + revisão do conselho (Regra 12).                 PENDENTE
  9. Reconhece Acumulado (Regra 5) como critério único de ranking.    OK
  10. Não aplicável (é cartucho de entrada, não de saída).            N/A
  11. Pendente de citação das atas no PR (Regra 15).                  PENDENTE
"""

# ---- Parâmetros do autor (Regra 3: valores relativos, sem cópia de config) ----
JANELA_COMPRESSAO = 12
RAZAO_COMPRESSAO_MAX = 0.75
ATR_REL_MIN = 0.85
ATR_REL_MAX = 1.60
RSI_COMPRA_MIN = 50.0
RSI_VENDA_MAX = 50.0
CORPO_MAX = 0.85
FOLGA_ATR_ROMPIMENTO = 0.05

# Janelas internas (sub-janelas da compressão)
_N_RECENTE = 4
_N_ANTERIOR = 8


def _amplitude(candle: dict) -> float:
    return float(candle["Maximo"]) - float(candle["Minimo"])


def _media_amplitudes(candles) -> float:
    if not candles:
        return 0.0
    return sum(_amplitude(c) for c in candles) / len(candles)


def _ha_compressao(ohlc, n_total: int) -> bool:
    """True se a média de amplitude das últimas _N_RECENTE velas for
    significativamente menor que a das _N_ANTERIOR velas anteriores a elas.
    Precisa de n_total candles; usa exatamente os últimos n_total."""
    if len(ohlc) < n_total:
        return False
    janela = ohlc[-n_total:]
    recentes = janela[-_N_RECENTE:]
    anteriores = janela[:-_N_RECENTE][-_N_ANTERIOR:]
    if not anteriores:
        return False
    med_ant = _media_amplitudes(anteriores)
    if med_ant <= 0:
        return False
    med_rec = _media_amplitudes(recentes)
    return (med_rec / med_ant) < RAZAO_COMPRESSAO_MAX


def _extremos_da_compressao(ohlc, n_total: int):
    """Máxima e mínima do range comprimido (últimos n_total candles)."""
    janela = ohlc[-n_total:]
    return (
        max(float(c["Maximo"]) for c in janela),
        min(float(c["Minimo"]) for c in janela),
    )


def _corpo_relativo(row: dict) -> float:
    amplitude = float(row["Maximo"]) - float(row["Minimo"])
    if amplitude <= 0:
        return 1.0
    return abs(float(row["Fechamento"]) - float(row["Abertura"])) / amplitude


def gerar_sinal(row: dict) -> int:
    """Devolve 1 (compra), -1 (venda) ou 0 (nada). Nunca levanta exceção por
    causa de campo ausente — apenas devolve 0 se o row estiver incompleto."""
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
    if not ohlc or len(ohlc) < JANELA_COMPRESSAO:
        return 0

    # Candle de rompimento não pode ser marubozu esticado
    if _corpo_relativo(row) > CORPO_MAX:
        return 0

    # Compressão recente?
    if not _ha_compressao(ohlc, JANELA_COMPRESSAO):
        return 0

    max_comp, min_comp = _extremos_da_compressao(ohlc, JANELA_COMPRESSAO)
    fech = float(row["Fechamento"])
    folga = FOLGA_ATR_ROMPIMENTO * float(atr)

    # Rompimento para CIMA + tendência de alta + RSI a favor
    if (
        tendencia == 1
        and fech >= max_comp + folga
        and rsi >= RSI_COMPRA_MIN
    ):
        return 1

    # Rompimento para BAIXO + tendência de baixa + RSI a favor
    if (
        tendencia == -1
        and fech <= min_comp - folga
        and rsi <= RSI_VENDA_MAX
    ):
        return -1

    return 0