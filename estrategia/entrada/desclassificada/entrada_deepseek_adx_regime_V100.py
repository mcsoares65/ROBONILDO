"""
entrada_deepseek_adx_regime_V100.py

Autor: DeepSeek (IA), revisado por humano antes da submissão.
Numeração V100 = própria do autor; NÃO é a VERSAO do projeto.

Mudanças em relação à V99 (que deu negativo):
  1. ADX não precisa mais SUBIR todo candle. Exige apenas
     adx_atual >= ADX_MIN e adx_atual >= adx_anterior - 1.0
     (tolera o ADX respirando perto do topo, sem exigir subida contínua).
  2. Rompimento com filtro de extensão: preço não pode estar mais de
     1.5 ATR acima da máxima rompida (evita entrar esticado).
  3. Range mínimo exigido para o rompimento: (max(20) - min(20)) >= 2 ATR.
  4. Confirmação por RSI mantida, mas limiar ajustado para 52/48.

Contrato (motor.py V486):
  gerar_sinal(row) -> 1 (compra) | -1 (venda) | 0 (nada)

Campos de `row` usados (todos vêm de motor.construir_row):
  Abertura, Maximo, Minimo, Fechamento,
  atr, atr_relativo, rsi, ohlc_recentes.

Sem I/O. Sem import de módulo do projeto. Sem estado global.
"""

ADX_PERIODO = 14
ADX_MIN = 25.0
TOLERANCIA_QUEDA_ADX = 1.0    # aceita adx_atual >= adx_anterior - 1.0
JANELA_ROMPIMENTO = 20
ATR_MIN_REL = 0.85
ATR_MAX_REL = 1.80
EXTENSAO_MAX_ATR = 1.5        # preço não pode estar > 1.5 ATR acima da máxima rompida
RANGE_MIN_ATR = 2.0           # range mínimo entre máx e mín da janela
RSI_COMPRA_MIN = 52.0
RSI_VENDA_MAX = 48.0

_MIN_CANDLES_ADX = 3 * ADX_PERIODO + 5


def _true_range(c, anterior):
    hl = c["Maximo"] - c["Minimo"]
    hc = abs(c["Maximo"] - anterior["Fechamento"])
    lc = abs(c["Minimo"] - anterior["Fechamento"])
    return max(hl, hc, lc)


def _wilder_smooth(serie, n_per):
    if len(serie) < n_per:
        return []
    suav = [sum(serie[:n_per])]
    for v in serie[n_per:]:
        suav.append(suav[-1] - (suav[-1] / n_per) + v)
    return suav


def _adx_wilder(ohlc):
    n = len(ohlc)
    if n < _MIN_CANDLES_ADX:
        return None, None, None, None
    tr_list, dmp_list, dmm_list = [], [], []
    for i in range(1, n):
        c, p = ohlc[i], ohlc[i - 1]
        up = c["Maximo"] - p["Maximo"]
        dn = p["Minimo"] - c["Minimo"]
        plus = up if (up > dn and up > 0) else 0.0
        minus = dn if (dn > up and dn > 0) else 0.0
        tr_list.append(_true_range(c, p))
        dmp_list.append(plus)
        dmm_list.append(minus)

    str_list = _wilder_smooth(tr_list, ADX_PERIODO)
    sdm_plus = _wilder_smooth(dmp_list, ADX_PERIODO)
    sdm_minus = _wilder_smooth(dmm_list, ADX_PERIODO)
    if not str_list:
        return None, None, None, None

    di_plus, di_minus = [], []
    for s_tr, s_dp, s_dm in zip(str_list, sdm_plus, sdm_minus):
        if s_tr == 0:
            di_plus.append(0.0); di_minus.append(0.0)
        else:
            di_plus.append(100.0 * s_dp / s_tr)
            di_minus.append(100.0 * s_dm / s_tr)

    dx = []
    for dp, dm in zip(di_plus, di_minus):
        s = dp + dm
        dx.append(0.0 if s == 0 else 100.0 * abs(dp - dm) / s)

    adx_serie = _wilder_smooth(dx, ADX_PERIODO)
    if len(adx_serie) < 2:
        return None, None, None, None
    return adx_serie[-1], adx_serie[-2], di_plus[-1], di_minus[-1]


def _rompimento(ohlc, n):
    if len(ohlc) < n + 1:
        return None, None
    janela = ohlc[-n - 1:-1]
    return (
        max(float(c["Maximo"]) for c in janela),
        min(float(c["Minimo"]) for c in janela),
    )


def gerar_sinal(row: dict) -> int:
    try:
        ohlc = row.get("ohlc_recentes")
        atr = row.get("atr")
        atr_rel = row.get("atr_relativo")
        rsi = row.get("rsi")
        fech = float(row["Fechamento"])
    except Exception:
        return 0

    if not ohlc or len(ohlc) < _MIN_CANDLES_ADX:
        return 0
    if atr is None or atr <= 0:
        return 0
    if atr_rel is None or atr_rel < ATR_MIN_REL or atr_rel > ATR_MAX_REL:
        return 0
    if rsi is None:
        return 0

    adx_atual, adx_anterior, di_mais, di_menos = _adx_wilder(ohlc)
    if adx_atual is None:
        return 0

    # CORREÇÃO 1: ADX com tolerância de respiro
    if adx_atual < ADX_MIN:
        return 0
    if adx_atual < adx_anterior - TOLERANCIA_QUEDA_ADX:
        return 0

    max_n, min_n = _rompimento(ohlc, JANELA_ROMPIMENTO)
    if max_n is None:
        return 0

    # CORREÇÃO 3: range mínimo entre máx e mín da janela
    if (max_n - min_n) < RANGE_MIN_ATR * float(atr):
        return 0

    # CORREÇÃO 2: filtro de extensão do rompimento
    if di_mais > di_menos and fech >= max_n and rsi >= RSI_COMPRA_MIN:
        extensao = fech - max_n
        if extensao <= EXTENSAO_MAX_ATR * float(atr):
            return 1
    if di_menos > di_mais and fech <= min_n and rsi <= RSI_VENDA_MAX:
        extensao = min_n - fech
        if extensao <= EXTENSAO_MAX_ATR * float(atr):
            return -1
    return 0