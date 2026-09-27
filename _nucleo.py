"""
ROBONILDO_V2 - estrategias_producao/_nucleo.py

Pecas compartilhadas por QUALQUER estrategia de producao - dataclasses e
funcoes de indicador reaproveitaveis, para nao duplicar codigo entre
estrategias diferentes.

Prefixo "_" no nome do arquivo: o principal.py (e qualquer descoberta futura
de estrategias) ignora arquivos comecando com "_" - nao e uma estrategia em
si, so a base compartilhada.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

import configuracao as cfg


@dataclass
class Candle:
    horario: datetime
    abertura: float
    maxima: float
    minima: float
    fechamento: float


@dataclass
class Sinal:
    horario: datetime
    lado: str              # "COMPRA" ou "VENDA"
    entrada: float
    stop: float
    alvo: float
    distancia_ma21: float
    motivo: str


def media_movel(candles: List[Candle], periodo: int) -> Optional[float]:
    """Media aritmetica simples dos ultimos `periodo` fechamentos."""
    if len(candles) < periodo:
        return None
    fechamentos = [c.fechamento for c in candles[-periodo:]]
    return sum(fechamentos) / periodo


def estocastico_lento(candles: List[Candle], periodo: int = 8, suavizacao: int = 3) -> Optional[float]:
    """
    Estocastico Lento, suavizacao EXPONENCIAL (EMA) - confirmado como o calculo
    real que o Profit usa (nao a media simples), validado comparando contra a
    tela do Profit durante os testes.

    IMPORTANTE: a EMA e calculada sobre a serie INTEIRA de %K bruto disponivel
    (desde o primeiro candle valido), nao so os ultimos candles - EMA de
    poucos pontos "esquenta" com um valor um pouco diferente da EMA de
    verdade (que carrega o historico inteiro), e isso pode mudar o resultado
    exatamente na fronteira de um cruzamento de zona (20/80). Bug encontrado
    e corrigido ao adaptar a CLAUDE_HIBRIDA_3_PORTAS_v2, que depende dessa
    precisao para detectar cruzamento - a ma_stoch_direcao_v1 nunca notou
    porque so usava a DIRECAO (subindo/descendo), nao um limiar exato.
    """
    if len(candles) < periodo + suavizacao:
        return None

    valores_raw_k = []
    for i in range(periodo, len(candles) + 1):
        janela = candles[i - periodo:i]
        maxima = max(c.maxima for c in janela)
        minima = min(c.minima for c in janela)
        if maxima == minima:
            valores_raw_k.append(50.0)
        else:
            raw_k = 100 * (janela[-1].fechamento - minima) / (maxima - minima)
            valores_raw_k.append(raw_k)

    alpha = 2 / (suavizacao + 1)
    ema = valores_raw_k[0]
    for v in valores_raw_k[1:]:
        ema = alpha * v + (1 - alpha) * ema
    return ema


def dentro_de_janela_bloqueada(horario: datetime) -> bool:
    hm = horario.strftime("%H:%M")
    for inicio, fim in cfg.JANELAS_BLOQUEADAS:
        if inicio <= hm <= fim:
            return True
    return False


def macd_linha(candles: List[Candle], rapida: int = 12, lenta: int = 26, sinal: int = 9):
    """
    MACD classico: EMA rapida - EMA lenta, e a linha de sinal (EMA da
    diferenca). Recalcula sobre TODO o historico disponivel a cada chamada
    (mesmo padrao do estocastico_lento) - EMA precisa da serie completa
    para "esquentar" corretamente, nao so uma janela fixa.

    Devolve (macd, sinal_da_linha) ou (None, None) se nao houver candles
    suficientes.
    """
    if len(candles) < lenta + sinal:
        return None, None

    fechamentos = [c.fechamento for c in candles]

    def ema_serie(valores, periodo):
        alpha = 2 / (periodo + 1)
        serie = [valores[0]]
        for v in valores[1:]:
            serie.append(alpha * v + (1 - alpha) * serie[-1])
        return serie

    ema_rapida = ema_serie(fechamentos, rapida)
    ema_lenta = ema_serie(fechamentos, lenta)
    linha_macd = [r - l for r, l in zip(ema_rapida, ema_lenta)]
    linha_sinal = ema_serie(linha_macd, sinal)

    return linha_macd[-1], linha_sinal[-1]


def macd_cruzamento(candles: List[Candle]):
    """
    Detecta cruzamento do MACD com a linha de sinal, comparando o candle
    atual com o anterior. Devolve ('cima', 'baixo' ou None).
    """
    macd_atual, sinal_atual = macd_linha(candles)
    macd_anterior, sinal_anterior = macd_linha(candles[:-1]) if len(candles) > 1 else (None, None)
    if None in (macd_atual, sinal_atual, macd_anterior, sinal_anterior):
        return None
    if macd_anterior <= sinal_anterior and macd_atual > sinal_atual:
        return "cima"
    if macd_anterior >= sinal_anterior and macd_atual < sinal_atual:
        return "baixo"
    return None


def estocastico_cruzamento_zona(candles: List[Candle], periodo: int = 8, suavizacao: int = 3):
    """
    Detecta o estocastico SUAVIZADO (o mesmo estocastico_lento usado na
    direcao geral - NAO o %K bruto) cruzando para FORA de uma zona extrema:
    saindo de <=20 para >20 ("cima", tipico de compra) ou saindo de >=80
    para <80 ("baixo", tipico de venda). Devolve ('cima', 'baixo' ou None).

    IMPORTANTE: no laboratorio, stoch_cross_up_20/stoch_cross_down_80 sao
    calculados em cima de df['stoch'] (a serie suavizada), nao do %K bruto -
    usar %K bruto aqui gera falsos positivos/negativos (ja aconteceu, bug
    encontrado e corrigido durante a adaptacao desta estrategia).
    """
    stoch_atual = estocastico_lento(candles, periodo, suavizacao)
    stoch_anterior = estocastico_lento(candles[:-1], periodo, suavizacao) if len(candles) > 1 else None
    if stoch_atual is None or stoch_anterior is None:
        return None
    if stoch_anterior <= 20 and stoch_atual > 20:
        return "cima"
    if stoch_anterior >= 80 and stoch_atual < 80:
        return "baixo"
    return None


def corpo_relativo(candle: Candle) -> Optional[float]:
    """Proporcao do corpo do candle sobre a amplitude total (maxima-minima) -
    usado para rejeitar candle de exaustao/marubozu em portas de rompimento."""
    amplitude = candle.maxima - candle.minima
    if amplitude <= 0:
        return None
    return abs(candle.fechamento - candle.abertura) / amplitude


def construir_row(candles: List[Candle]) -> Optional[dict]:
    """
    PONTE GENERICA laboratorio -> producao: monta um dicionario com TODAS as
    colunas que laboratorio_estrategias/indicadores.py calcula, a partir do
    historico de candles do robo - permite rodar QUALQUER estrategia escrita
    no formato do laboratorio (gerar_sinal(row) -> int) diretamente em
    producao, SEM TRADUCAO MANUAL, reaproveitando o mesmo codigo que os
    colegas/outras IAs ja validaram la.

    Isso existe porque traduzir estrategia por estrategia a mao (como foi
    feito para a CLAUDE_HIBRIDA_3_PORTAS_v2) e lento e arriscado - ja
    aconteceu de a traducao manual introduzir um bug sutil de precisao,
    encontrado so depois de comparar sinal a sinal contra o laboratorio.
    Com essa ponte, o MESMO codigo roda nos dois lados - nao ha mais "duas
    implementacoes para manter sincronizadas".

    LIMITACAO CONHECIDA: nao inclui Quantidade/volume_media_21 - o Candle de
    producao ainda nao guarda volume (precisaria mudar construtor_candle.py
    e leitor_dde.py tambem). Estrategias que dependem de volume (ex:
    ma_stoch_volume_v1) ainda NAO podem rodar em producao via esta ponte.

    Devolve None se nao houver candles suficientes para os indicadores mais
    exigentes (MACD precisa de 26+9=35).
    """
    if len(candles) < max(50, 35) + 1:
        return None

    atual = candles[-1]

    ma21 = media_movel(candles, 21)
    ma50 = media_movel(candles, 50)
    if ma21 is None or ma50 is None:
        return None
    trend = 1 if ma21 > ma50 else (-1 if ma21 < ma50 else 0)
    distancia_ma21 = abs(atual.fechamento - ma21)
    toque_ma21 = (distancia_ma21 <= 40) and (trend != 0)

    stoch = estocastico_lento(candles)
    stoch_prev = estocastico_lento(candles[:-1]) if len(candles) > 1 else None
    if stoch is None or stoch_prev is None:
        return None
    stoch_subindo = stoch > stoch_prev
    stoch_descendo = stoch < stoch_prev
    stoch_cross_up_20 = (stoch_prev <= 20) and (stoch > 20)
    stoch_cross_down_80 = (stoch_prev >= 80) and (stoch < 80)

    macd, macd_signal = macd_linha(candles)
    macd_ant, macd_signal_ant = macd_linha(candles[:-1]) if len(candles) > 1 else (None, None)
    macd_cross_up = macd_cross_down = False
    if None not in (macd, macd_signal, macd_ant, macd_signal_ant):
        macd_cross_up = (macd_ant <= macd_signal_ant) and (macd > macd_signal)
        macd_cross_down = (macd_ant >= macd_signal_ant) and (macd < macd_signal)

    return {
        "dt": atual.horario,
        "Abertura": atual.abertura, "Maximo": atual.maxima,
        "Minimo": atual.minima, "Fechamento": atual.fechamento,
        "MA21": ma21, "MA50": ma50, "trend": trend,
        "distancia_ma21": distancia_ma21, "toque_ma21": toque_ma21,
        "stoch": stoch, "stoch_prev": stoch_prev,
        "stoch_subindo": stoch_subindo, "stoch_descendo": stoch_descendo,
        "stoch_cross_up_20": stoch_cross_up_20, "stoch_cross_down_80": stoch_cross_down_80,
        "macd": macd, "macd_signal": macd_signal,
        "macd_cross_up": macd_cross_up, "macd_cross_down": macd_cross_down,
    }


def avaliar_candle_via_gerar_sinal(candles: List[Candle], gerar_sinal) -> Optional[Sinal]:
    """
    Adaptador generico: recebe uma funcao gerar_sinal(row) -> int, no
    formato EXATO do laboratorio_estrategias (sem nenhuma mudanca), e devolve
    um Sinal no formato que o robo de producao espera - aplicando o mesmo
    bloqueio de horario BASE que o motor do laboratorio aplica (abertura,
    NY), que nao faz parte de gerar_sinal() em si.

    Validado: reproduz EXATAMENTE o resultado do laboratorio (mesmo N,
    mesmo PF) quando testado com a CLAUDE_HIBRIDA_3_PORTAS_v2 original, sem
    nenhuma edicao no arquivo da estrategia.
    """
    row = construir_row(candles)
    if row is None:
        return None
    if dentro_de_janela_bloqueada(row["dt"]):
        return None

    sinal_bruto = gerar_sinal(row)
    if sinal_bruto == 0:
        return None

    resultado = calcular_stop_alvo(candles, candles[-1].fechamento, row["trend"])
    if resultado is None:
        return None
    stop, alvo, lado = resultado

    return Sinal(
        horario=candles[-1].horario, lado=lado, entrada=candles[-1].fechamento,
        stop=stop, alvo=alvo, distancia_ma21=row["distancia_ma21"],
        motivo="estrategia do laboratorio, via ponte generica (gerar_sinal)",
    )


def calcular_stop_alvo(candles: List[Candle], entrada: float, tendencia: int):
    """
    Stop estrutural (fundo/topo dos ultimos SWING_LOOKBACK_CANDLES) e alvo em
    RELACAO_RISCO_RETORNO x o risco - regra compartilhada por todas as
    estrategias de producao (a parte de GESTAO DE RISCO da operacao nao muda
    entre estrategias, so a regra de ENTRADA muda).

    Devolve (stop, alvo, lado) ou None se o risco calculado for invalido.
    """
    janela_stop = candles[-cfg.SWING_LOOKBACK_CANDLES - 1:]
    if tendencia == 1:
        stop = min(c.minima for c in janela_stop)
        risco = entrada - stop
        if risco <= 0:
            return None
        alvo = entrada + cfg.RELACAO_RISCO_RETORNO * risco
        return stop, alvo, "COMPRA"
    else:
        stop = max(c.maxima for c in janela_stop)
        risco = stop - entrada
        if risco <= 0:
            return None
        alvo = entrada - cfg.RELACAO_RISCO_RETORNO * risco
        return stop, alvo, "VENDA"
