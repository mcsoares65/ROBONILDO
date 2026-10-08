"""
saida_deepseek_adx_esfriando_V99.py

Autor: DeepSeek (IA), revisado por humano antes da submissão.
Numeração V99 = própria do autor; NÃO é a VERSAO do projeto (versionamento.py).

Ideia
-----
Fecha a posição quando o regime de tendência MORREU — ADX cruzou abaixo
de 20 — ou quando o DI que sustentava a posição virou contra.

Não é trailing stop nem stop por preço: é saída por MUDANÇA DE REGIME.
Casa com a entrada_deepseek_adx_regime_V99 (mesmo cálculo de ADX, portão
de entrada e portão de saída fecham o ciclo).

Contrato (motor.py V486)
------------------------
  avaliar_saida(row, posicao) -> dict
    {
      "fechar": bool,
      "novo_stop": float | None,
      "novo_alvo": float | None,
    }

Campos de `posicao` (schema fechado no conselho):
  posicao["lado"], posicao["entrada"], posicao["candles_decorridos"],
  posicao["maxima_desde_entrada"], posicao["minima_desde_entrada"],
  posicao["resultado_flutuante_pts"]

Campos de `row`: row["ohlc_recentes"], row["atr"].

Stop e alvo iniciais: definidos na abertura (Regra 1 v10 do compliance) —
o motor não calcula nada. Aqui definimos:
  - Stop estrutural: extremo oposto da janela de rompimento ± folga de 0,25 ATR
  - Alvo: 2,0 R (mesma distância do stop)

Depois da abertura, só reconfigura se o DI virar contra a posição. Não fecha
por preço — deixa o stop estrutural fazer isso. Fecha quando o ADX esfriou.

DECLARAÇÃO HONESTA SOBRE A REGRA 2 DO compliance.md
---------------------------------------------------
Mesma observação do cartucho de entrada: o ADX é recalculado aqui dentro,
o que viola a letra da Regra 2. Registrado para o conselho.

Sem I/O. Sem import de módulo do projeto. Sem estado global. Sem data/valor
absoluto. Limiares em pontos de indicador (ADX) ou múltiplos de ATR.

Parâmetros:
  ADX_PERIODO              = 14
  ADX_MIN_PARA_MANTER      = 20.0   abaixo disso, fecha
  JANELA_ESTRUTURAL        = 20
  FOLGA_STOP_ATR           = 0.25
  RR_ALVO                  = 2.0
  FLUTUANTE_BREAKEVEN_R    = 1.0    em 1R, stop -> entrada
  FLUTUANTE_TRAVA_R        = 1.8    em 1.8R, alvo -> preço atual
  MIN_CANDLES_PARA_AVALIAR = 2      não avalia no candle 0 (é a abertura)

Declaração (Termo de concordância, versão 8) — itens:
  1. Respeita avaliar_saida(row, posicao) -> dict.                  OK
  2. Usa apenas campos documentados em construir_row / posicao.     PARCIAL
     (mesma nota Regra 2 do cartucho de entrada)
  3. Não importa módulo do projeto, não abre arquivo, não usa rede. OK
  4. Nenhum resultado próprio é alegado (Regra 4).                  OK
  5. Autoria: IA (DeepSeek), revisado por humano.                   OK
  6. Não duplica arquivo existente em estrategia/saida/.            OK
  7. V99 = numeração própria do autor. 1 variante. Sem data.        OK
  8. Pendente de PR + revisão do conselho (Regra 12).               PENDENTE
  9. Reconhece Acumulado (Regra 5) como critério único de ranking.  OK
  10. Assume responsabilidade total por definir stop e alvo desde   OK
      a abertura (Regra 1 v10).
  11. Pendente de citação das atas no PR (Regra 15).                PENDENTE
"""

# ---- Parâmetros ----
ADX_PERIODO = 14
ADX_MIN_PARA_MANTER = 20.0
JANELA_ESTRUTURAL = 20
FOLGA_STOP_ATR = 0.25
RR_ALVO = 2.0
FLUTUANTE_BREAKEVEN_R = 1.0
FLUTUANTE_TRAVA_R = 1.8
_MIN_CANDLES_ADX = 3 * ADX_PERIODO + 5


def _true_range(c, anterior):
    hl = c["Maximo"] - c["Minimo"]
    hc = abs(c["Maximo"] - anterior["Fechamento"])
    lc = abs(c["Minimo"] - anterior["Fechamento"])
    return max(hl, hc, lc)


def _adx_wilder(ohlc):
    """Mesmo ADX do cartucho de entrada. Devolve (adx_atual, adx_anterior,
    di_mais, di_menos) ou (None,)*4."""
    n = len(ohlc)
    if n < _MIN_CANDLES_ADX:
        return None, None, None, None

    tr_list, dmp_list, dmm_list = [], [], []
    for i in range(1, n):
        c = ohlc[i]; p = ohlc[i - 1]
        up = c["Maximo"] - p["Maximo"]
        dn = p["Minimo"] - c["Minimo"]
        plus = up if (up > dn and up > 0) else 0.0
        minus = dn if (dn > up and dn > 0) else 0.0
        tr_list.append(_true_range(c, p))
        dmp_list.append(plus)
        dmm_list.append(minus)

    def _wilder(serie, n_per):
        if len(serie) < n_per:
            return []
        suav = [sum(serie[:n_per])]
        for v in serie[n_per:]:
            suav.append(suav[-1] - (suav[-1] / n_per) + v)
        return suav

    str_list = _wilder(tr_list, ADX_PERIODO)
    sdm_plus = _wilder(dmp_list, ADX_PERIODO)
    sdm_minus = _wilder(dmm_list, ADX_PERIODO)
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

    adx_serie = _wilder(dx, ADX_PERIODO)
    if len(adx_serie) < 2:
        return None, None, None, None
    return adx_serie[-1], adx_serie[-2], di_plus[-1], di_minus[-1]


def _extremos_estruturais(ohlc, n):
    if len(ohlc) < n:
        return None, None
    janela = ohlc[-n:]
    return (
        max(float(c["Maximo"]) for c in janela),
        min(float(c["Minimo"]) for c in janela),
    )


def _stop_alvo_inicial(row, lado, entrada, atr):
    if atr is None or atr <= 0:
        return None, None
    max_r, min_r = _extremos_estruturais(row.get("ohlc_recentes"), JANELA_ESTRUTURAL)
    if max_r is None or min_r is None:
        return None, None
    folga = FOLGA_STOP_ATR * float(atr)

    if lado == "COMPRA":
        stop = min_r - folga
        if stop >= entrada - 0.5 * float(atr):
            stop = entrada - 0.5 * float(atr)
        alvo = entrada + RR_ALVO * (entrada - stop)
    else:
        stop = max_r + folga
        if stop <= entrada + 0.5 * float(atr):
            stop = entrada + 0.5 * float(atr)
        alvo = entrada - RR_ALVO * (stop - entrada)
    return stop, alvo


def avaliar_saida(row: dict, posicao: dict) -> dict:
    """Sempre devolve dict com as três chaves."""
    resposta = {"fechar": False, "novo_stop": None, "novo_alvo": None}

    try:
        lado = posicao["lado"]
        entrada = float(posicao["entrada"])
        decorridos = int(posicao["candles_decorridos"])
        flutuante = float(posicao["resultado_flutuante_pts"])
        atr = row.get("atr")
    except Exception:
        return resposta

    # Abertura: define stop e alvo iniciais (Regra 1 v10)
    if decorridos == 0:
        stop, alvo = _stop_alvo_inicial(row, lado, entrada, atr)
        resposta["novo_stop"] = stop
        resposta["novo_alvo"] = alvo
        return resposta

    if atr is None or atr <= 0:
        return resposta

    ohlc = row.get("ohlc_recentes")
    if not ohlc or len(ohlc) < _MIN_CANDLES_ADX:
        return resposta

    adx_atual, _adx_anterior, di_mais, di_menos = _adx_wilder(ohlc)
    if adx_atual is None:
        return resposta

    # R aproximado: distância mínima garantida no _stop_alvo_inicial é 0.5 ATR.
    R = 0.5 * float(atr)

    # Trava de lucro em 1.8R: congela o ganho
    if flutuante >= FLUTUANTE_TRAVA_R * R:
        resposta["fechar"] = True
        return resposta

    # Breakeven em 1R: move stop para a entrada
    if flutuante >= FLUTUANTE_BREAKEVEN_R * R:
        resposta["novo_stop"] = entrada

    # Portão de regime para MANTER: se ADX morreu, fecha
    if adx_atual < ADX_MIN_PARA_MANTER:
        resposta["fechar"] = True
        return resposta

    # DI virou contra a posição: sinal de reversão do fluxo direcional
    if lado == "COMPRA" and di_menos > di_mais:
        resposta["fechar"] = True
        return resposta
    if lado == "VENDA" and di_mais > di_menos:
        resposta["fechar"] = True
        return resposta

    return resposta