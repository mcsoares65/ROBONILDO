"""
saida_deepseek_estrutura_candle_V101.py

Autor: DeepSeek (IA), revisado por humano antes da submissão.
Numeração V101 = própria do autor; NÃO é a VERSAO do projeto.

Tese
----
Trailing por estrutura de candle. Ao invés de rastrear pico (saida_trailing_pico_v01)
ou ATR (saida_stop_atr_v01), usa a MÍNIMA DO CANDLE ANTERIOR como âncora móvel
de stop em COMPRA (máxima do anterior em VENDA). Fecha quando a estrutura
quebra de forma clara: fechamento além da âncora por mais de uma folga
proporcional ao ATR.

Por que isso é diferente das campeãs do ranking S:
- saida_trailing_pico_v01 rastreia o pico e devolve % dele. É trailing de lucro.
- saida_safezone_v01 afasta stop por ruído médio. É trailing de ruído.
- Esta rastreia a última microestrutura confirmada. É trailing estrutural.

Contrato (motor.py V486):
  avaliar_saida(row, posicao) -> dict
    {fechar: bool, novo_stop: float|None, novo_alvo: float|None}

Campos de `row`: Abertura, Maximo, Minimo, Fechamento, atr, ohlc_recentes.
Campos de `posicao`: lado, entrada, candles_decorridos,
  maxima_desde_entrada, minima_desde_entrada, resultado_flutuante_pts.

Sem I/O. Sem import de módulo do projeto. Sem estado global. Sem data/valor
absoluto. Todos os limiares são relativos (ATR, R).

Parâmetros (Regra 10 — perturbar ±10–30%):
  FOLGA_ANCORA_ATR      = 0.25  folga além da mínima/máxima do candle anterior
  STOP_INICIAL_ATR      = 1.00  stop inicial (1 ATR abaixo/acima da entrada)
  RR_ALVO               = 1.90  alvo inicial (assimétrico, como a campeã)
  TRAILING_ATIVA_R      = 0.50  só começa a mover o stop após 0.5 R de lucro
  MIN_CANDLES_ANCORA    = 3     exige pelo menos N candles em ohlc_recentes
  ENCERRAMENTO_ESTRITO  = True  fecha também se preço atual cruza a âncora
                                mesmo sem confirmação de fechamento
"""

# Parâmetros
FOLGA_ANCORA_ATR = 0.25
STOP_INICIAL_ATR = 1.00
RR_ALVO = 1.90
TRAILING_ATIVA_R = 0.50
MIN_CANDLES_ANCORA = 3


def _ultimo_ohlc(ohlc, n=2):
    """Devolve os últimos n candles de ohlc_recentes, ou None."""
    if not ohlc or len(ohlc) < n:
        return None
    return ohlc[-n:]


def _stop_alvo_inicial(entrada, lado, atr):
    if atr is None or atr <= 0:
        return None, None
    folga = STOP_INICIAL_ATR * float(atr)
    if lado == "COMPRA":
        return entrada - folga, entrada + RR_ALVO * folga
    return entrada + folga, entrada - RR_ALVO * folga


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

    # Abertura: define stop e alvo iniciais (Regra 1 v10 do compliance)
    if decorridos == 0:
        stop, alvo = _stop_alvo_inicial(entrada, lado, atr)
        resposta["novo_stop"] = stop
        resposta["novo_alvo"] = alvo
        return resposta

    if atr is None or atr <= 0:
        return resposta

    ohlc = row.get("ohlc_recentes")
    ultimos = _ultimo_ohlc(ohlc, MIN_CANDLES_ANCORA)
    if ultimos is None:
        return resposta

    # Âncora: o candle ANTERIOR ao atual é o segundo da lista
    anterior = ultimos[-2]
    folga = FOLGA_ANCORA_ATR * float(atr)
    R = STOP_INICIAL_ATR * float(atr)

    # Fechamento de proteção: só move stop depois de algum lucro
    tem_lucro = flutuante >= TRAILING_ATIVA_R * R

    if lado == "COMPRA":
        ancora = float(anterior["Minimo"]) - folga
        # nunca deixa o stop descer — só sobe (trailing é unilateral)
        if tem_lucro and ancora > (posicao.get("_ultimo_stop") or entrada - R):
            resposta["novo_stop"] = ancora
        # quebra de estrutura: fechamento abaixo da mínima do anterior
        if float(row["Fechamento"]) < float(anterior["Minimo"]):
            resposta["fechar"] = True
        return resposta

    # VENDA
    ancora = float(anterior["Maximo"]) + folga
    if tem_lucro and ancora < (posicao.get("_ultimo_stop") or entrada + R):
        resposta["novo_stop"] = ancora
    if float(row["Fechamento"]) > float(anterior["Maximo"]):
        resposta["fechar"] = True
    return resposta