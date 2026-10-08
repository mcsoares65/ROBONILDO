"""
saida_deepseek_adx_esfriando_V100.py

Autor: DeepSeek (IA), revisado por humano antes da submissão.
Numeração V100 = própria do autor; NÃO é a VERSAO do projeto.

Mudanças em relação à V99:
  1. Stop inicial 0.75 ATR (era extremo oposto do range de 20 candles,
     tipicamente 2–4 ATR no WIN — stop largo demais).
  2. Alvo inicial 1.55 R (era 2.0 R).
  3. Breakeven em 1 R, trava de lucro em 1.5 R (antes 1.8 R).
  4. Saída por ADX esfriando mantida, mas limiar em 22 (era 20) para
     fechar um pouco antes, quando o regime enfraquece.
  5. DI contra a posição também fecha (mantido).

Contrato (motor.py V486):
  avaliar_saida(row, posicao) -> dict
"""

ADX_PERIODO = 14
ADX_MIN_PARA_MANTER = 22.0
FOLGA_STOP_ATR = 0.75
RR_ALVO = 1.55
FLUTUANTE_BREAKEVEN_R = 1.0
FLUTUANTE_TRAVA_R = 1.5
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


def avaliar_saida(row: dict, posicao: dict) -> dict:
    resposta = {"fechar": False, "novo_stop": None, "novo_alvo": None}
    try:
        lado = posicao["lado"]
        entrada = float(posicao["entrada"])
        decorridos = int(posicao["candles_decorridos"])
        flutuante = float(posicao["resultado_flutuante_pts"])
        atr = row.get("atr")
    except Exception:
        return resposta

    # Abertura: stop 0.75 ATR, alvo 1.55 R
    if decorridos == 0:
        if atr is None or atr <= 0:
            return resposta
        folga = FOLGA_STOP_ATR * float(atr)
        if lado == "COMPRA":
            stop = entrada - folga
            alvo = entrada + RR_ALVO * folga
        else:
            stop = entrada + folga
            alvo = entrada - RR_ALVO * folga
        resposta["novo_stop"] = stop
        resposta["novo_alvo"] = alvo
        return resposta

    if atr is None or atr <= 0:
        return resposta

    ohlc = row.get("ohlc_recentes")
    if not ohlc or len(ohlc) < _MIN_CANDLES_ADX:
        return resposta

    adx_atual, _, di_mais, di_menos = _adx_wilder(ohlc)
    if adx_atual is None:
        return resposta

    R = FOLGA_STOP_ATR * float(atr)

    if flutuante >= FLUTUANTE_TRAVA_R * R:
        resposta["fechar"] = True
        return resposta
    if flutuante >= FLUTUANTE_BREAKEVEN_R * R:
        resposta["novo_stop"] = entrada

    if adx_atual < ADX_MIN_PARA_MANTER:
        resposta["fechar"] = True
        return resposta
    if lado == "COMPRA" and di_menos > di_mais:
        resposta["fechar"] = True
        return resposta
    if lado == "VENDA" and di_mais > di_menos:
        resposta["fechar"] = True
        return resposta

    return resposta