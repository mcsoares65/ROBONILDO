"""Console único do Robonildo.

Este módulo concentra indicadores, interpretação do cartucho de estratégia,
stop/alvo, limites, posição e resultado. principal.py e classificacao.py apenas
fornecem eventos e consomem as decisões deste motor.
"""

from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime, date, timedelta
from pathlib import Path
import json
import queue

import configuracao as cfg


@dataclass
class Candle:
    horario: datetime
    abertura: float
    maxima: float
    minima: float
    fechamento: float
    quantidade: Optional[float] = None  # contratos por candle; None = indisponível


@dataclass
class Sinal:
    horario: datetime
    lado: str              # "COMPRA" ou "VENDA"
    entrada: float
    stop: Optional[float]  # None ate a Regra 1 v10: o motor nao calcula
    alvo: Optional[float]  # mais stop/alvo - quem define e o cartucho de
                            # saida titular, na abertura da posicao.
    distancia_ma21: float
    motivo: str


def media_movel(candles: List[Candle], periodo: int) -> Optional[float]:
    """Media aritmetica simples dos ultimos `periodo` fechamentos."""
    if len(candles) < periodo:
        return None
    fechamentos = [c.fechamento for c in candles[-periodo:]]
    return sum(fechamentos) / periodo


def wad_preco(candles: List[Candle], janela: int = 96) -> tuple[float, ...]:
    """Williams A/D sem volume, alinhado aos candles fechados da janela.

    O primeiro valor e zero arbitrario; somente diferencas sao comparadas.
    Nao representa agressao nem fluxo de ordens observado no DDE.
    """
    if janela <= 0:
        raise ValueError("A janela WAD deve ser positiva.")
    serie = candles[-janela:]
    if not serie:
        return ()
    valores = [0.0]
    acumulado = 0.0
    for anterior, atual in zip(serie, serie[1:]):
        if atual.fechamento > anterior.fechamento:
            acumulado += atual.fechamento - min(atual.minima, anterior.fechamento)
        elif atual.fechamento < anterior.fechamento:
            acumulado += atual.fechamento - max(atual.maxima, anterior.fechamento)
        valores.append(acumulado)
    return tuple(valores)


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


def atr_e_media(candles: List[Candle], periodo: int = 14, periodo_media: int = 50):
    """
    ATR (True Range suavizado por EMA) e sua media movel simples de 50
    periodos, e a razao entre os dois (atr_relativo). Mesma formula do
    indicadores.py do laboratorio (EMA span=14, adjust=False para o ATR;
    SMA 50 periodos para atr_media50).

    Devolve (atr, atr_media50, atr_relativo) ou (None, None, None) se nao
    houver candles suficientes.
    """
    if len(candles) < periodo + periodo_media:
        return None, None, None

    true_ranges = []
    for i in range(1, len(candles)):
        atual = candles[i]; anterior = candles[i - 1]
        high_low = atual.maxima - atual.minima
        high_close_prev = abs(atual.maxima - anterior.fechamento)
        low_close_prev = abs(atual.minima - anterior.fechamento)
        true_ranges.append(max(high_low, high_close_prev, low_close_prev))

    alpha = 2 / (periodo + 1)
    atr_serie = [true_ranges[0]]
    for v in true_ranges[1:]:
        atr_serie.append(alpha * v + (1 - alpha) * atr_serie[-1])

    if len(atr_serie) < periodo_media:
        return None, None, None
    atr = atr_serie[-1]
    atr_media50 = sum(atr_serie[-periodo_media:]) / periodo_media
    if atr_media50 == 0:
        return atr, atr_media50, None
    return atr, atr_media50, atr / atr_media50


def rsi_wilder(candles: List[Candle], periodo: int = 14) -> Optional[float]:
    """
    RSI classico, suavizacao de Wilder (ewm alpha=1/periodo, adjust=False) -
    mesma formula do indicadores.py do laboratorio.
    """
    if len(candles) < periodo + 1:
        return None

    fechamentos = [c.fechamento for c in candles]
    deltas = [fechamentos[i] - fechamentos[i - 1] for i in range(1, len(fechamentos))]
    ganhos = [max(d, 0.0) for d in deltas]
    perdas = [max(-d, 0.0) for d in deltas]

    alpha = 1 / periodo
    media_ganho = ganhos[0]
    media_perda = perdas[0]
    for g, p in zip(ganhos[1:], perdas[1:]):
        media_ganho = alpha * g + (1 - alpha) * media_ganho
        media_perda = alpha * p + (1 - alpha) * media_perda

    if media_perda == 0:
        return 100.0
    rs = media_ganho / media_perda
    return 100 - (100 / (1 + rs))


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
    if len(candles) < max(50, 35, 64) + 1:
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

    atr, atr_media50, atr_relativo = atr_e_media(candles)
    rsi = rsi_wilder(candles)
    rsi_prev = rsi_wilder(candles[:-1]) if len(candles) > 1 else None
    rsi_subindo = (rsi is not None and rsi_prev is not None and rsi > rsi_prev)
    rsi_descendo = (rsi is not None and rsi_prev is not None and rsi < rsi_prev)

    # Janela OHLC genérica para cartuchos que analisam padrões de vários
    # candles. Somente candles já fechados entram aqui; portanto não há
    # vazamento de informação futura. Tupla imutável e campos primitivos
    # preservam o isolamento entre o console e o cartucho.
    # V466: 96 candles cobrem ao menos o pregao atual e o anterior no WIN de
    # 15 minutos. Isso permite que cartuchos stateless usem o fechamento da
    # sessao anterior e as origens intradiarias sem consultar arquivo externo.
    # As saídas existentes continuam usando apenas a própria janela final.
    ohlc_recentes = tuple(
        {
            "dt": candle.horario,
            "Abertura": candle.abertura,
            "Maximo": candle.maxima,
            "Minimo": candle.minima,
            "Fechamento": candle.fechamento,
        }
        for candle in candles[-96:]
    )

    # Serie WAD sem volume, alinhada 1:1 a ohlc_recentes e sem look-ahead.
    wad_preco_recentes = wad_preco(candles, janela=96)

    # Janela isolada Gabriel: preserva seu próprio contrato e não fornece
    # volume quando o dado não está disponível.
    gabriel_barras = tuple(
        {
            "dt": candle.horario,
            "Abertura": candle.abertura,
            "Maximo": candle.maxima,
            "Minimo": candle.minima,
            "Fechamento": candle.fechamento,
            "Quantidade": candle.quantidade,
        }
        for candle in candles[-96:]
    )

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
        "atr": atr, "atr_media50": atr_media50, "atr_relativo": atr_relativo,
        "rsi": rsi, "rsi_prev": rsi_prev,
        "rsi_subindo": rsi_subindo, "rsi_descendo": rsi_descendo,
        "ohlc_recentes": ohlc_recentes,
        "wad_preco_recentes": wad_preco_recentes,
        "gabriel_barras": gabriel_barras,
    }


def construir_contexto_narracao(row: dict) -> str:
    """
    Monta uma frase curta, natural, com o contexto REAL do candle no momento
    do sinal - usa so valores que genuinamente existem em row (RSI, ATR
    relativo, distancia da MA21, tendencia). Nunca inventa "qual porta
    disparou" (o contrato gerar_sinal(row) -> int nao informa isso, e nao
    deve ser mudado so para narracao - ver Regra 1 das Regras do Jogo).
    """
    partes = []

    tendencia_txt = "alta" if row.get("trend") == 1 else "baixa" if row.get("trend") == -1 else None

    rsi = row.get("rsi")
    if rsi is not None and rsi == rsi:  # descarta NaN
        if tendencia_txt == "alta":
            favoravel = ", favorável à alta" if rsi >= 50 else ""
        elif tendencia_txt == "baixa":
            favoravel = ", favorável à baixa" if rsi <= 50 else ""
        else:
            favoravel = ""
        partes.append(f"RSI em {rsi:.0f}{favoravel}")

    atr_rel = row.get("atr_relativo")
    if atr_rel is not None and atr_rel == atr_rel:
        if atr_rel <= 0.9:
            partes.append("volatilidade abaixo do normal")
        elif atr_rel <= 1.3:
            partes.append("volatilidade dentro do normal")
        else:
            partes.append("volatilidade elevada")

    distancia = row.get("distancia_ma21")
    if distancia is not None and distancia == distancia:
        partes.append(f"{distancia:.0f} pontos de distância da média")

    if not partes:
        return "sinal gerado pela estratégia do laboratório, por meio da ponte genérica"
    return ", ".join(partes) + "."


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
    if sinal_bruto not in (-1, 1):
        raise ValueError(
            f"Direção de sinal inválida: {sinal_bruto!r}. Esperado 1, -1 ou 0."
        )
    lado = "COMPRA" if sinal_bruto == 1 else "VENDA"

    motivo = construir_contexto_narracao(row)

    return Sinal(
        horario=candles[-1].horario, lado=lado, entrada=candles[-1].fechamento,
        stop=None, alvo=None, distancia_ma21=row["distancia_ma21"],
        motivo=motivo,
    )


@dataclass
class Posicao:
    lado: str
    entrada: float
    stop: Optional[float]   # Regra 1 v10: None ate o cartucho de saida
    alvo: Optional[float]   # titular definir - o motor nao tem valor padrao.
    horario_entrada: str
    motivo_entrada: str
    candles_decorridos: int = 0
    maxima_desde_entrada: float = 0.0
    minima_desde_entrada: float = 0.0


class MotorRobonildo:
    """Máquina de estados usada igualmente nos jogos ao vivo e gravados."""

    def __init__(
        self,
        gerar_sinal,
        arquivo_estado: Optional[str] = cfg.CAMINHO_ESTADO_RISCO,
        horario_mercado_inicial: Optional[datetime] = None,
        avaliar_saida=None,
        diagnosticar_oportunidades=None,
    ):
        if not callable(gerar_sinal):
            raise TypeError("O cartucho precisa fornecer gerar_sinal(row).")
        if avaliar_saida is not None and not callable(avaliar_saida):
            raise TypeError("O cartucho de saída precisa fornecer avaliar_saida(row, posicao).")
        if diagnosticar_oportunidades is not None and not callable(diagnosticar_oportunidades):
            raise TypeError("O radar de entrada precisa fornecer diagnosticar_oportunidades(row).")
        self.gerar_sinal = gerar_sinal
        self.avaliar_saida = avaliar_saida
        self.diagnosticar_oportunidades = diagnosticar_oportunidades
        self.ultimo_erro_saida: Optional[str] = None  # diagnostico - se o
                                                        # cartucho de saida
                                                        # lancar excecao, fica
                                                        # registrado aqui
        self.arquivo_estado = Path(arquivo_estado) if arquivo_estado else None
        if self.arquivo_estado:
            self.arquivo_estado.parent.mkdir(parents=True, exist_ok=True)
        self.posicao_aberta: Optional[Posicao] = None
        self.operacoes_hoje = 0
        self.perdas_hoje = 0
        self.data_atual: date = (horario_mercado_inicial or datetime.now()).date()
        self.banca_atual = cfg.BANCA_ATUAL_REAIS
        self.operacoes_fechadas: list[dict] = []
        self._noticias = queue.Queue()
        self._carregar_estado()

    # ---------- Cartucho e indicadores ----------
    def construir_row(self, candles: List[Candle]) -> Optional[dict]:
        return construir_row(candles)

    def radar_oportunidades(self, row: Optional[dict]) -> list[dict]:
        """Consolida o radar opcional do cartucho sem interferir no sinal.

        A lista é ordenada por maior progresso e, no empate, pela prioridade
        histórica declarada. Cartuchos antigos continuam válidos e apenas
        retornam radar vazio.
        """
        if row is None or self.diagnosticar_oportunidades is None:
            return []
        oportunidades = self.diagnosticar_oportunidades(row)
        if not isinstance(oportunidades, (list, tuple)):
            raise TypeError("diagnosticar_oportunidades(row) precisa retornar uma lista.")
        normalizadas = []
        for item in oportunidades:
            if not isinstance(item, dict):
                raise TypeError("Cada oportunidade do radar precisa ser um dict.")
            copia = dict(item)
            copia["progresso"] = max(0.0, min(1.0, float(copia.get("progresso", 0.0))))
            copia["prioridade"] = int(copia.get("prioridade", 999))
            normalizadas.append(copia)
        return sorted(normalizadas, key=lambda item: (-item["progresso"], item["prioridade"]))

    def avaliar_candle(self, candles: List[Candle]) -> Optional[Sinal]:
        row = construir_row(candles)
        return self.avaliar_row(candles, row)

    def avaliar_row(self, candles: List[Candle], row: Optional[dict]) -> Optional[Sinal]:
        """Avalia indicadores já calculados sem duplicar a regra de decisão.

        Regra 1 v10: nao calcula mais stop/alvo aqui - o motor nao tem
        formula propria de saida. Sinal nasce com stop=None/alvo=None; e o
        cartucho de saida titular quem define os niveis, na abertura da
        posicao (ver abrir_posicao())."""
        if row is None or dentro_de_janela_bloqueada(row["dt"]):
            return None
        bruto = self.gerar_sinal(row)
        if bruto == 0:
            return None
        if bruto not in (-1, 1):
            raise ValueError(
                f"Direção de sinal inválida: {bruto!r}. Esperado 1, -1 ou 0."
            )
        lado = "COMPRA" if bruto == 1 else "VENDA"
        return Sinal(
            horario=candles[-1].horario,
            lado=lado,
            entrada=candles[-1].fechamento,
            stop=None,
            alvo=None,
            distancia_ma21=row["distancia_ma21"],
            motivo=construir_contexto_narracao(row),
        )

    # ---------- Notícias assíncronas ----------
    def registrar_noticia(self, texto: str, horario: Optional[datetime] = None) -> None:
        self._noticias.put({"horario": horario, "texto": texto})

    def consumir_noticias(self) -> list[dict]:
        eventos = []
        while True:
            try:
                eventos.append(self._noticias.get_nowait())
            except queue.Empty:
                return eventos

    # ---------- Persistência do jogo ao vivo ----------
    def _carregar_estado(self) -> None:
        if not self.arquivo_estado or not self.arquivo_estado.exists():
            return
        try:
            estado = json.loads(self.arquivo_estado.read_text(encoding="utf-8"))
            self.banca_atual = estado.get("banca_atual", cfg.BANCA_ATUAL_REAIS)
            data_salva = date.fromisoformat(estado["data"])
            if data_salva != self.data_atual:
                self._resetar_dia()
                return
            self.operacoes_hoje = estado.get("operacoes_hoje", 0)
            self.perdas_hoje = estado.get("perdas_hoje", 0)
            if estado.get("posicao"):
                self.posicao_aberta = Posicao(**estado["posicao"])
        except Exception as erro:
            print(f"[MOTOR] Erro ao carregar estado, iniciando limpo: {erro}")

    def _salvar_estado(self) -> None:
        if not self.arquivo_estado:
            return
        estado = {
            "data": self.data_atual.isoformat(),
            "operacoes_hoje": self.operacoes_hoje,
            "perdas_hoje": self.perdas_hoje,
            "posicao": asdict(self.posicao_aberta) if self.posicao_aberta else None,
            "banca_atual": self.banca_atual,
        }
        self.arquivo_estado.write_text(
            json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _resetar_dia(self) -> None:
        self.operacoes_hoje = 0
        self.perdas_hoje = 0
        self.posicao_aberta = None
        self._salvar_estado()

    def _checar_novo_dia(self, horario_mercado: datetime) -> None:
        dia_mercado = horario_mercado.date()
        if dia_mercado != self.data_atual:
            self.data_atual = dia_mercado
            self._resetar_dia()

    # ---------- Gestão única da posição ----------
    def pode_abrir_posicao(self, horario: datetime):
        self._checar_novo_dia(horario)
        if self.posicao_aberta is not None:
            return False, "Já existe posição aberta"
        # V459: o teto de CONTAGEM de operações por pregão saiu daqui. Medido
        # nos dois períodos, mordia em 3,6% e 3,9% dos pregões operados, com
        # efeito dentro da faixa de ruído e de sinal oposto nos dois. O contador
        # `operacoes_hoje` continua sendo mantido, para relatório e estado, mas
        # já não barra entrada. Quem protege capital é MAX_PERDAS_DIA, abaixo.
        if self.perdas_hoje >= cfg.MAX_PERDAS_DIA:
            return False, f"Limite diário de perdas atingido ({cfg.MAX_PERDAS_DIA})"
        if horario.strftime("%H:%M") >= cfg.HORARIO_BLOQUEIO_NOVAS_ENTRADAS:
            return False, f"Após horário limite para novas entradas ({cfg.HORARIO_BLOQUEIO_NOVAS_ENTRADAS})"
        return True, ""

    def validar_risco_inicial(self, sinal: Sinal, row: Optional[dict]):
        """V461/V462: recusa a entrada se o stop inicial proposto pelo cartucho de
        saida custar mais que cfg.RISCO_MAXIMO_PCT_BANCA da banca real.

        Pergunta ao cartucho (candles_decorridos == 0, a mesma chamada que
        abrir_posicao faz) SEM abrir nada, entao pode ser chamada ANTES de
        enviar a ordem. E usada igual no ao vivo e no backtest (paridade).

        V462: com cartucho + row, se o stop NAO puder ser verificado (excecao, sem
        novo_stop, nao numerico, NaN/inf, ou do lado errado) e
        cfg.RISCO_FALHA_FECHADA for True (padrao), a entrada e BLOQUEADA. Sem
        cartucho de saida ou sem row nao ha o que verificar e nao bloqueia."""
        pct = getattr(cfg, "RISCO_MAXIMO_PCT_BANCA", 0) or 0
        banca = getattr(cfg, "BANCA_REAL_REAIS", 0) or 0
        # V483: pct == 0 desliga SO o limite percentual; a verificacao fail-closed
        # do stop (V462) continua valendo, pois e outra protecao.
        if self.avaliar_saida is None or row is None:
            return True, ""
        fechada = bool(getattr(cfg, "RISCO_FALHA_FECHADA", False))

        def invalido(motivo):
            if not fechada:
                return True, ""
            return False, (f"Entrada bloqueada: não foi possível validar o stop inicial "
                           f"({motivo}). Risco desconhecido não é risco aceito.")

        try:
            resposta = self.avaliar_saida(row, {
                "lado": sinal.lado, "entrada": sinal.entrada, "candles_decorridos": 0,
                "maxima_desde_entrada": sinal.entrada, "minima_desde_entrada": sinal.entrada,
                "resultado_flutuante_pts": 0.0,
            })
        except Exception as e:
            return invalido(f"a saída falhou: {type(e).__name__}")
        stop = resposta.get("novo_stop") if isinstance(resposta, dict) else None
        if stop is None:
            return invalido("a saída não propôs stop")
        try:
            stop = float(stop)
            entrada = float(sinal.entrada)
        except (TypeError, ValueError):
            return invalido("stop não numérico")
        if stop != stop or stop in (float("inf"), float("-inf")):
            return invalido("stop NaN/infinito")
        lado = str(sinal.lado).upper()
        if (lado == "COMPRA" and stop >= entrada) or (lado == "VENDA" and stop <= entrada):
            return invalido("stop do lado errado do preço")
        if not pct or not banca:
            return True, ""
        pontos = abs(entrada - stop)
        risco = pontos * cfg.VALOR_PONTO_REAIS + cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
        limite = pct * banca
        if risco > limite:
            return False, (
                f"Oportunidade à frente mas a banca não irá suportar o tamanho do stop loss "
                f"(stop de {pontos:.0f} pts = R${risco:.2f} = {100 * risco / banca:.0f}% da banca "
                f"de R${banca:.2f}; limite {100 * pct:.0f}% = R${limite:.2f})")
        return True, ""

    def abrir_posicao(self, sinal: Sinal, row: Optional[dict] = None):
        """Abre a posição e, na sequência, pergunta ao cartucho de saída
        titular quais são o stop e o alvo iniciais (Regra 1 v10) - o motor
        não tem mais fórmula própria para isso. Se não houver cartucho de
        saída plugado, ou ele não definir nada, a posição nasce SEM stop
        nem alvo (só fecha por pedido explícito do cartucho ou pelo corte
        de horário) - responsabilidade inteira do arquivo em
        estrategia/saida/titular/."""
        pode, motivo = self.pode_abrir_posicao(sinal.horario)
        if not pode:
            return False, motivo
        pos = Posicao(
            lado=sinal.lado,
            entrada=sinal.entrada,
            stop=None,
            alvo=None,
            horario_entrada=sinal.horario.isoformat(),
            motivo_entrada=sinal.motivo,
            candles_decorridos=0,
            maxima_desde_entrada=sinal.entrada,
            minima_desde_entrada=sinal.entrada,
        )
        self.posicao_aberta = pos

        if self.avaliar_saida is not None and row is not None:
            posicao_publica = {
                "lado": pos.lado,
                "entrada": pos.entrada,
                "candles_decorridos": 0,
                "maxima_desde_entrada": pos.maxima_desde_entrada,
                "minima_desde_entrada": pos.minima_desde_entrada,
                "resultado_flutuante_pts": 0.0,
            }
            try:
                resposta = self.avaliar_saida(row, posicao_publica)
                self.ultimo_erro_saida = None
            except Exception as e:
                resposta = False
                self.ultimo_erro_saida = f"{type(e).__name__}: {e}"
            if isinstance(resposta, dict):
                self._aplicar_reconfiguracao(pos, resposta)
            # um bool puro na abertura não define stop/alvo - contratos
            # antigos simplesmente deixam a posição sem níveis definidos
            # até o primeiro candle seguinte chamar avaliar_saida de novo.

        self.operacoes_hoje += 1
        self._salvar_estado()
        return True, f"Posição aberta: {sinal.lado} @ {sinal.entrada}"

    def verificar_saida_continua(self, preco_atual: float):
        """Checagem tick-a-tick (fora do fechamento de candle). Regra 1 v10:
        pos.stop/pos.alvo podem ser None enquanto o cartucho de saida ainda
        nao definiu nivel nenhum - nesse caso simplesmente nao ha corte por
        preco a testar aqui (a posicao so fecharia por pedido explicito do
        cartucho ou pelo corte de horario, tratados em outro lugar)."""
        if self.posicao_aberta is None:
            return None
        pos = self.posicao_aberta
        if pos.lado == "COMPRA":
            if pos.stop is not None and preco_atual <= pos.stop:
                return "STOP", preco_atual
            if pos.alvo is not None and preco_atual >= pos.alvo:
                return "ALVO", preco_atual
        else:
            if pos.stop is not None and preco_atual >= pos.stop:
                return "STOP", preco_atual
            if pos.alvo is not None and preco_atual <= pos.alvo:
                return "ALVO", preco_atual
        return None

    def _aplicar_reconfiguracao(self, pos: "Posicao", proposta: dict) -> None:
        """Aplica novo_stop/novo_alvo propostos pelo cartucho de saída,
        SEM nenhuma validação de aperto/afrouxamento - decisão explícita do
        dono do laboratório (Regra 1 v9): a estratégia de saída é
        inteiramente do cartucho, o motor não impõe piso de segurança.

        O motor aplica exatamente o que o cartucho propuser. Um bug ou
        proposta mal desenhada no cartucho pode aumentar o risco da operação
        sem limite - risco assumido conscientemente, não uma omissão.
        """
        novo_stop = proposta.get("novo_stop")
        if novo_stop is not None:
            pos.stop = novo_stop

        novo_alvo = proposta.get("novo_alvo")
        if novo_alvo is not None:
            pos.alvo = novo_alvo

    def verificar_saida(self, maxima_candle: float, minima_candle: float, horario: datetime,
                         row: Optional[dict] = None):
        """
        Ordem de prioridade (Regra 1 v9 - autoridade total do cartucho):
          1. Consulta o cartucho de saida (se houver) - pode redefinir
             livremente o stop e/ou o alvo da posicao (dict) e/ou pedir
             fechamento imediato (fechar=True ou bool puro, para contratos
             antigos). SEM validacao: o motor nao impoe piso de seguranca
             nem impede afrouxamento - decisao explicita do dono do
             laboratorio.
          2. Stop/alvo (ja com a reconfiguracao do passo 1 aplicada, se
             houve) - testado com maximo/minimo do candle.
          3. Fechamento antecipado explicito do cartucho (fechar=True) - so
             se o passo 2 nao fechou.
          4. Corte de horario/janela bloqueada - tratado FORA deste metodo,
             pelos chamadores (verificar_corte_final ao vivo,
             ultimo_candle_do_dia no historico) - permanece inalterado.

        row (opcional): necessario para o cartucho de saida poder avaliar -
        sem ele, os passos 1 e 3 sao pulados (comportamento identico ao
        motor sem cartucho de saida plugado).
        """
        if self.posicao_aberta is None:
            return None
        pos = self.posicao_aberta

        # Atualiza o rastreamento da posicao - uma vez por candle fechado,
        # ANTES de qualquer decisao de saida, para o cartucho sempre ver o
        # estado mais atual (inclui o candle que esta sendo verificado agora).
        pos.candles_decorridos += 1
        pos.maxima_desde_entrada = max(pos.maxima_desde_entrada, maxima_candle)
        pos.minima_desde_entrada = min(pos.minima_desde_entrada, minima_candle)

        # PASSO 1: consulta o cartucho de saida - pode reconfigurar stop/alvo
        # (dict, Regra 1 v9) e/ou pedir fechamento (fechar=True ou bool puro,
        # contratos antigos).
        fechar_agora = False
        if self.avaliar_saida is not None and row is not None:
            direcao = 1 if pos.lado == "COMPRA" else -1
            resultado_flutuante_pts = (row["Fechamento"] - pos.entrada) * direcao
            # Schema publico de `posicao` fechado em conselho (rodada 3) -
            # NAO inclui motivo_entrada (removido por decisao do DeepSeek,
            # aceita: evitava acoplamento oculto entre os dois cartuchos).
            posicao_publica = {
                "lado": pos.lado,
                "entrada": pos.entrada,
                "candles_decorridos": pos.candles_decorridos,
                "maxima_desde_entrada": pos.maxima_desde_entrada,
                "minima_desde_entrada": pos.minima_desde_entrada,
                "resultado_flutuante_pts": resultado_flutuante_pts,
            }
            try:
                resposta = self.avaliar_saida(row, posicao_publica)
                self.ultimo_erro_saida = None
            except Exception as e:
                # Excecao no cartucho de saida NUNCA derruba o motor - cai no
                # comportamento padrao (nao fecha antecipado; stop/alvo
                # continuam valendo como estavam) e fica registrado para
                # quem chama poder marcar a estrategia como incompativel -
                # mesma regra ja aplicada a cartuchos de entrada que falham.
                resposta = False
                self.ultimo_erro_saida = f"{type(e).__name__}: {e}"

            if isinstance(resposta, dict):
                fechar_agora = bool(resposta.get("fechar", False))
                self._aplicar_reconfiguracao(pos, resposta)
            else:
                fechar_agora = bool(resposta)

        # PASSO 2: stop/alvo (possivelmente ja reconfigurados no passo 1).
        # Regra 1 v10: pos.stop/pos.alvo podem ser None - o motor nao tem
        # formula propria, entao ate o cartucho de saida definir um nivel a
        # posicao simplesmente nao tem esse lado de saida testado ainda.
        if pos.lado == "COMPRA":
            if pos.stop is not None and minima_candle <= pos.stop:
                return "STOP", pos.stop
            if pos.alvo is not None and maxima_candle >= pos.alvo:
                return "ALVO", pos.alvo
        else:
            if pos.stop is not None and maxima_candle >= pos.stop:
                return "STOP", pos.stop
            if pos.alvo is not None and minima_candle <= pos.alvo:
                return "ALVO", pos.alvo

        # PASSO 3: fechamento antecipado explicito do cartucho.
        if fechar_agora:
            return "SAIDA_CARTUCHO", row["Fechamento"]

        return None

    def resultado_flutuante(self, preco_atual: float) -> float:
        if self.posicao_aberta is None:
            return 0.0
        direcao = 1 if self.posicao_aberta.lado == "COMPRA" else -1
        return (preco_atual - self.posicao_aberta.entrada) * direcao

    def verificar_corte_final(self, preco_atual: float, horario: datetime):
        # cfg.HORARIO_LIMITE_ABSOLUTO e "18:20:58" (com segundos, de proposito -
        # ver comentario em configuracao.py). Comparar com strftime("%H:%M")
        # (so minuto) e um bug: "18:20" < "18:20:58" em ordem lexicografica,
        # entao o corte so disparava as 18:21:00 - quase 1 minuto e 2 segundos
        # DEPOIS do horario configurado, o oposto do que o dono do laboratorio
        # pediu ao adicionar os segundos. Corrigido para comparar tambem por
        # segundo, para o corte disparar exatamente as 18:20:58, exclusivamente.
        if self.posicao_aberta and horario.strftime("%H:%M:%S") >= cfg.HORARIO_LIMITE_ABSOLUTO:
            return "CORTE_SEGURANCA_LIMITE", preco_atual
        return None

    def fechar_posicao(self, preco_saida: float, motivo: str):
        if self.posicao_aberta is None:
            return 0.0, "Nenhuma posição aberta para fechar"
        pos = self.posicao_aberta
        direcao = 1 if pos.lado == "COMPRA" else -1
        resultado_pontos = (preco_saida - pos.entrada) * direcao
        resultado_reais = (
            resultado_pontos * cfg.VALOR_PONTO_REAIS
            - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
        )
        if resultado_pontos < 0:
            self.perdas_hoje += 1
        self.banca_atual += resultado_reais
        mensagem = (
            f"Posição fechada: {pos.lado} | Entrada={pos.entrada} Saída={preco_saida} | "
            f"Resultado={resultado_pontos:.1f}pts (R${resultado_reais:.2f}) | "
            f"Motivo={motivo} | Banca atual: R${self.banca_atual:.2f}"
        )
        self.posicao_aberta = None
        self._salvar_estado()
        return resultado_pontos, mensagem

    def status(self, horario_mercado: datetime) -> dict:
        self._checar_novo_dia(horario_mercado)
        return {
            "posicao_aberta": self.posicao_aberta is not None,
            "operacoes_hoje": self.operacoes_hoje,
            "perdas_hoje": self.perdas_hoje,
            "pode_operar": self.pode_abrir_posicao(horario_mercado)[0],
        }

    # ---------- Jogo gravado ----------
    def processar_candle_historico(
        self,
        candles: List[Candle],
        ultimo_candle_do_dia: bool,
        row: Optional[dict] = None,
    ) -> list[dict]:
        """Processa um candle pelo mesmo estado operacional usado ao vivo."""
        candle = candles[-1]
        eventos = []
        if self.posicao_aberta is not None:
            posicao = self.posicao_aberta
            saida = self.verificar_saida(candle.maxima, candle.minima, candle.horario, row=row)
            # Regra 1 v10: stop/alvo podem ser None (cartucho de saida ainda
            # nao definiu nivel nenhum) - sem os dois lados definidos nao ha
            # como o candle ser "ambiguo" entre stop e alvo.
            ambiguo = False
            if posicao.stop is not None and posicao.alvo is not None:
                if posicao.lado == "COMPRA":
                    ambiguo = candle.minima <= posicao.stop and candle.maxima >= posicao.alvo
                else:
                    ambiguo = candle.maxima >= posicao.stop and candle.minima <= posicao.alvo
            if saida is None and ultimo_candle_do_dia:
                saida = ("CORTE_15M_APROXIMADO", candle.fechamento)
            if saida is not None:
                motivo, preco_saida = saida
                direcao = 1 if posicao.lado == "COMPRA" else -1
                pontos = (preco_saida - posicao.entrada) * direcao
                reais = pontos * cfg.VALOR_PONTO_REAIS - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
                resultado_pontos, _ = self.fechar_posicao(preco_saida, motivo)
                trade = {
                    "lado": posicao.lado,
                    "entrada": posicao.entrada,
                    "stop": posicao.stop,
                    "alvo": posicao.alvo,
                    "horario_rotulo": datetime.fromisoformat(posicao.horario_entrada),
                    "horario_execucao": datetime.fromisoformat(posicao.horario_entrada)
                    + timedelta(minutes=cfg.TIMEFRAME_MINUTOS),
                    "saida_dt": candle.horario + timedelta(minutes=cfg.TIMEFRAME_MINUTOS),
                    "saida": preco_saida,
                    "motivo": motivo,
                    "resultado_pts_bruto": resultado_pontos,
                    "resultado_reais": reais,
                    "intrabar_ambiguo": ambiguo,
                }
                self.operacoes_fechadas.append(trade)
                eventos.append({"tipo": "SAIDA", "trade": trade})
            return eventos  # candle de saída nunca gera reentrada

        if ultimo_candle_do_dia:
            return eventos
        sinal = self.avaliar_row(candles, row) if row is not None else self.avaliar_candle(candles)
        if sinal is None:
            return eventos
        pode, motivo = self.pode_abrir_posicao(sinal.horario)
        if not pode:
            eventos.append({"tipo": "SINAL_BLOQUEADO", "sinal": sinal, "motivo": motivo})
            return eventos
        ok_risco, motivo_risco = self.validar_risco_inicial(sinal, row)
        if not ok_risco:
            eventos.append({"tipo": "SINAL_BLOQUEADO", "sinal": sinal, "motivo": motivo_risco})
            return eventos
        abriu, motivo = self.abrir_posicao(sinal, row=row)
        if abriu:
            eventos.append({"tipo": "ENTRADA", "sinal": sinal})
        else:
            eventos.append({"tipo": "SINAL_BLOQUEADO", "sinal": sinal, "motivo": motivo})
        return eventos
