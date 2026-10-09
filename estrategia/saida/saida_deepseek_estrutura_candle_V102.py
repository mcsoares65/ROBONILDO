"""
saida_deepseek_estrutura_candle_V101.py

Autor: DeepSeek (IA), revisado por humano antes da submissão.
Numeração V101 = própria do autor; NÃO é a VERSAO do projeto.

Tese
----
Trailing por estrutura de candle. A âncora do stop é a mínima do candle
anterior (COMPRA) ou máxima do anterior (VENDA), recuada por uma folga
proporcional ao ATR. O cartucho NÃO guarda estado — a cada chamada
recalcula o stop a partir do ohlc_recentes, que já traz os candles
fechados. O motor aplica o `novo_stop` proposto, e como o motor nunca
deixa o stop descer por conta própria, a unilateralidade é garantida
pelo próprio motor.

Fecha a posição quando o fechamento do candle cruza a mínima (COMPRA)
ou a máxima (VENDA) do candle anterior — quebra de microestrutura.

Contrato (motor.py V486):
  avaliar_saida(row, posicao) -> dict
    {fechar: bool, novo_stop: float|None, novo_alvo: float|None}

Campos de `row`: Abertura, Maximo, Minimo, Fechamento, atr, ohlc_recentes.
Campos de `posicao`: lado, entrada, candles_decorridos,
  maxima_desde_entrada, minima_desde_entrada, resultado_flutuante_pts.

Sem I/O. Sem import de módulo do projeto. Sem estado global. Sem data/valor
absoluto.

Parâmetros (Regra 10 — perturbar ±10–30%):
  FOLGA_ANCORA_ATR      = 0.25
  STOP_INICIAL_ATR      = 1.00
  RR_ALVO               = 1.90
  TRAILING_ATIVA_R      = 0.50
  MIN_CANDLES_ANCORA    = 3
"""

FOLGA_ANCORA_ATR = 0.25
STOP_INICIAL_ATR = 1.00
RR_ALVO = 1.90
TRAILING_ATIVA_R = 0.50
MIN_CANDLES_ANCORA = 3


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
        ohlc = row.get("ohlc_recentes")
        fech = float(row["Fechamento"])
    except Exception:
        return resposta

    # Abertura: stop 1 ATR, alvo 1.90 R (assimétrico)
    if decorridos == 0:
        stop, alvo = _stop_alvo_inicial(entrada, lado, atr)
        resposta["novo_stop"] = stop
        resposta["novo_alvo"] = alvo
        return resposta

    if atr is None or atr <= 0:
        return resposta
    if not ohlc or len(ohlc) < MIN_CANDLES_ANCORA:
        return resposta

    anterior = ohlc[-2]
    folga = FOLGA_ANCORA_ATR * float(atr)
    R = STOP_INICIAL_ATR * float(atr)
    tem_lucro = flutuante >= TRAILING_ATIVA_R * R

    if lado == "COMPRA":
        # Trailing só armado depois de 0.5R de lucro
        if tem_lucro:
            ancora = float(anterior["Minimo"]) - folga
            resposta["novo_stop"] = ancora
        # Quebra de estrutura
        if fech < float(anterior["Minimo"]):
            resposta["fechar"] = True
        return resposta

    # VENDA
    if tem_lucro:
        ancora = float(anterior["Maximo"]) + folga
        resposta["novo_stop"] = ancora
    if fech > float(anterior["Maximo"]):
        resposta["fechar"] = True
    return resposta