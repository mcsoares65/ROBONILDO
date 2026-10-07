"""ROBONILDO - integridade_historico.py (V498)

Integridade da base de dados, em funcoes puras (sem Profit/Windows/voz) para serem
testaveis em qualquer maquina. O principal.py chama estas pecas, imprime e narra.

Tres pecas:

1. analisar_historico(): acha buracos de PREGAO nos ultimos candles do historico
   (inclusive o "buraco de cauda", entre o ultimo candle salvo e o mercado agora) e
   diz quantos candles de bloqueio de nova entrada ainda restam por causa deles.
2. RecuperadorCSV: de tempos em tempos, procura no export mais recente do Profit os
   candles que faltam e devolve so os que preenchem buraco. Assim o dono exporta o
   historico com o robo rodando e a entrada e liberada SEM reiniciar.
3. VigiaLeituraDDE: transforma "a leitura do DDE falhou de novo" em avisos falados
   (com prazo curto, com taxa limitada) e avisa quando a leitura volta.

Origem (06/10/2026): a planilha DDE ficou parada enquanto outra planilha era usada, o
robo nao disse nada, e na hora da entrada o dia estava bloqueado por buraco. Ver
conselho/2026-10-07-AI.txt.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional

from construtor_candle import candles_faltando, inicio_do_periodo

JANELA_CANDLES_PADRAO = 60   # MA50 + folga: so buraco dentro desta janela afeta indicadores


# ---------------------------------------------------------------------------
# 1. Analise de continuidade
# ---------------------------------------------------------------------------
@dataclass
class Buraco:
    depois_de: datetime        # ultimo candle conhecido antes do buraco
    antes_de: datetime         # primeiro candle conhecido depois (ou o candle em formacao)
    faltam: int                # candles de pregao que faltam entre os dois
    candles_depois: int = 0    # quantos candles do historico existem a partir de antes_de


@dataclass
class Analise:
    buracos: list = field(default_factory=list)
    faltam_total: int = 0
    restantes: int = 0         # candles de bloqueio de nova entrada que ainda restam
    ultimo_candle: Optional[datetime] = None
    n_candles: int = 0

    @property
    def integro(self) -> bool:
        return self.faltam_total == 0


def analisar_historico(candles, referencia_tempo: datetime, minutos: int,
                       primeiro: str, ultimo_rotulo: str, feriados=(),
                       janela: int = JANELA_CANDLES_PADRAO,
                       aquecimento: int = 50) -> Analise:
    """Buracos de pregao nos ultimos `janela` candles e ate o candle em formacao em
    `referencia_tempo`. Fim de semana, feriado e noite nao contam (candles_faltando).

    `restantes`: para cada buraco, aquecimento - candles ja fechados depois dele.
    Buraco com `aquecimento` candles ou mais depois dele nao bloqueia mais nada
    (a MA50 ja foi renovada); por isso reiniciar o robo nao re-bloqueia um buraco velho."""
    horarios = sorted({c.horario for c in candles})
    analise = Analise(n_candles=len(horarios))
    if not horarios:
        return analise
    analise.ultimo_candle = horarios[-1]
    recorte = horarios[-janela:]

    pares = list(zip(recorte[:-1], recorte[1:]))
    em_formacao = inicio_do_periodo(referencia_tempo, minutos)
    if em_formacao > horarios[-1]:
        pares.append((horarios[-1], em_formacao))

    for a, b in pares:
        n = candles_faltando(a, b, minutos, primeiro, ultimo_rotulo, feriados)
        if n <= 0:
            continue
        depois = sum(1 for h in horarios if h >= b)
        analise.buracos.append(Buraco(a, b, n, depois))
        analise.faltam_total += n
        analise.restantes = max(analise.restantes, aquecimento - depois)
    analise.restantes = max(0, analise.restantes)
    return analise


def descrever_buracos(analise: Analise, limite: int = 3) -> str:
    """Texto curto, para console e voz."""
    partes = []
    for b in analise.buracos[:limite]:
        partes.append(f"{b.faltam} candle(s) entre {b.depois_de.strftime('%d/%m %H:%M')} "
                      f"e {b.antes_de.strftime('%d/%m %H:%M')}")
    if len(analise.buracos) > limite:
        partes.append(f"e mais {len(analise.buracos) - limite} trecho(s)")
    return "; ".join(partes)


# ---------------------------------------------------------------------------
# 2. Recuperacao pelo CSV do Profit
# ---------------------------------------------------------------------------
def candles_para_preencher(historico, candles_arquivo, referencia_tempo: datetime,
                           minutos: int, janela: int = JANELA_CANDLES_PADRAO) -> list:
    """Candles do arquivo que NAO estao no historico, dentro da janela recente e ja
    fechados em `referencia_tempo`. Nunca substitui candle existente (o candle montado
    pelo DDE e o que o robo viu ao vivo) e nunca traz candle do futuro."""
    existentes = {c.horario for c in historico}
    if not existentes:
        return []
    horarios = sorted(existentes)
    inicio_janela = horarios[-janela] if len(horarios) >= janela else horarios[0]
    duracao = timedelta(minutes=minutos)
    return sorted(
        (c for c in candles_arquivo
         if c.horario >= inicio_janela
         and c.horario not in existentes
         and c.horario + duracao <= referencia_tempo),
        key=lambda c: c.horario,
    )


class RecuperadorCSV:
    """Reabre o export do Profit quando ele muda e devolve candles que preenchem buraco.

    resolver_caminho(): devolve o Path do export mais recente (ou levanta se nao houver).
    ler_candles(path): lista de Candle.
    So le o arquivo se (data de modificacao, tamanho) mudou desde a ultima leitura bem
    sucedida, e no maximo a cada `intervalo_segundos`."""

    def __init__(self, resolver_caminho: Callable, ler_candles: Callable,
                 intervalo_segundos: float = 30.0):
        self._resolver = resolver_caminho
        self._ler = ler_candles
        self.intervalo = intervalo_segundos
        self._ultima_tentativa: Optional[datetime] = None
        self._assinatura = None
        self.ultimo_erro: Optional[str] = None
        self.ultimo_arquivo = None

    def tentar(self, historico, referencia_tempo: datetime, agora_real: datetime,
               minutos: int, janela: int = JANELA_CANDLES_PADRAO,
               forcar: bool = False) -> list:
        if (not forcar and self._ultima_tentativa is not None and
                (agora_real - self._ultima_tentativa).total_seconds() < self.intervalo):
            return []
        self._ultima_tentativa = agora_real
        try:
            caminho = self._resolver()
            estado = os.stat(caminho)
            assinatura = (str(caminho), estado.st_mtime, estado.st_size)
            if assinatura == self._assinatura and not forcar:
                return []
            candles_arquivo = self._ler(caminho)
        except (OSError, ValueError) as e:
            self.ultimo_erro = str(e)
            return []
        self._assinatura = assinatura
        self.ultimo_erro = None
        self.ultimo_arquivo = caminho
        return candles_para_preencher(historico, candles_arquivo, referencia_tempo,
                                      minutos, janela)


# ---------------------------------------------------------------------------
# 3. Vigia da leitura do DDE
# ---------------------------------------------------------------------------
class VigiaLeituraDDE:
    """Conta falhas CONSECUTIVAS de leitura do DDE e devolve o texto a narrar (ou None).

    Usa o relogio REAL (na falha nao ha horario de mercado para consultar).
    - Sem posicao: primeiro aviso apos `limite_segundos` de falha, repete a cada
      `repetir_segundos`.
    - Com posicao aberta: prazo e repeticao menores e o texto e de urgencia.
    - Ao voltar a ler: um aviso de retorno (so se o aviso de falha chegou a ser dado,
      ou se a queda durou mais que `limite_segundos`)."""

    def __init__(self, limite_segundos: float = 20.0, repetir_segundos: float = 120.0,
                 limite_posicao_segundos: float = 8.0, repetir_posicao_segundos: float = 30.0):
        self.limite = limite_segundos
        self.repetir = repetir_segundos
        self.limite_pos = limite_posicao_segundos
        self.repetir_pos = repetir_posicao_segundos
        self._inicio: Optional[datetime] = None
        self._ultimo_aviso: Optional[datetime] = None
        self._avisou = False
        self.ultima_duracao: float = 0.0
        self.quedas = 0

    @property
    def em_falha(self) -> bool:
        return self._inicio is not None

    def falha(self, agora_real: datetime, posicao_aberta: bool = False,
              erro: Optional[str] = None) -> Optional[str]:
        if self._inicio is None:
            self._inicio = agora_real
            self._ultimo_aviso = None
            self._avisou = False
            self.quedas += 1
        duracao = (agora_real - self._inicio).total_seconds()
        limite = self.limite_pos if posicao_aberta else self.limite
        repetir = self.repetir_pos if posicao_aberta else self.repetir
        if duracao < limite:
            return None
        if self._ultimo_aviso is not None and \
                (agora_real - self._ultimo_aviso).total_seconds() < repetir:
            return None
        self._ultimo_aviso = agora_real
        self._avisou = True
        causa = ("o Excel está ocupado ou em edição" if erro and ("-2147418111" in erro or "rejeit" in erro.lower() or "reject" in erro.lower())
                 else "a planilha do DDE não respondeu")
        if posicao_aberta:
            return (f"ATENÇÃO. Posição aberta e sem leitura de preço há {duracao:.0f} segundos: "
                    f"{causa}. O stop e o alvo do robô NÃO estão sendo monitorados. "
                    f"Pare de mexer nas planilhas e acompanhe a posição pela tela do Profit.")
        return (f"Atenção. Perdi a leitura do preço há {duracao:.0f} segundos: {causa}. "
                f"Não mexa na planilha do DDE. Cada candle que passar sem leitura pode "
                f"abrir buraco nos dados.")

    def sucesso(self, agora_real: datetime) -> Optional[str]:
        if self._inicio is None:
            return None
        duracao = (agora_real - self._inicio).total_seconds()
        avisou = self._avisou
        self.ultima_duracao = duracao
        self._inicio = None
        self._ultimo_aviso = None
        self._avisou = False
        if not avisou and duracao < self.limite:
            return None
        return (f"Leitura do Profit restabelecida depois de {duracao:.0f} segundos sem dados. "
                f"Vou conferir se a queda abriu buraco no histórico.")


__all__ = ["Analise", "Buraco", "RecuperadorCSV", "VigiaLeituraDDE",
           "analisar_historico", "candles_para_preencher", "descrever_buracos",
           "JANELA_CANDLES_PADRAO"]
