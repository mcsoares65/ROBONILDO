"""
ROBONILDO - construtor_candle.py

Recebe leituras continuas de preco (do DDE, uma a cada poucos segundos) e monta
candles de 15 minutos, emitindo um Candle fechado exatamente quando o periodo termina.

Convencao: o horario do Candle e o INICIO do periodo (candle "16:00" cobre 16:00-16:15),
igual a convencao que usamos em toda a analise manual e no backtest.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from motor import Candle


def inicio_do_periodo(horario: datetime, minutos: int = 15) -> datetime:
    """Trunca o horario para o inicio do bloco de N minutos em que ele cai."""
    bloco = (horario.minute // minutos) * minutos
    return horario.replace(minute=bloco, second=0, microsecond=0)


@dataclass
class _CandleEmFormacao:
    inicio: datetime
    abertura: float
    maxima: float
    minima: float
    fechamento: float


class ConstrutorCandle:
    def __init__(self, minutos: int = 15):
        self.minutos = minutos
        self._atual: Optional[_CandleEmFormacao] = None

    def nova_leitura(self, preco: float, horario: datetime) -> Optional[Candle]:
        """
        Registra uma leitura de preco. Se essa leitura pertence a um novo periodo
        de 15 min (o periodo anterior encerrou), devolve o Candle fechado do
        periodo anterior. Caso contrario, devolve None.
        """
        periodo = inicio_do_periodo(horario, self.minutos)

        if self._atual is None:
            self._atual = _CandleEmFormacao(periodo, preco, preco, preco, preco)
            return None

        if periodo == self._atual.inicio:
            # mesma vela em formacao - so atualiza maxima/minima/fechamento
            self._atual.maxima = max(self._atual.maxima, preco)
            self._atual.minima = min(self._atual.minima, preco)
            self._atual.fechamento = preco
            return None

        # periodo novo comecou -> a vela anterior fechou
        candle_fechado = Candle(
            horario=self._atual.inicio,
            abertura=self._atual.abertura,
            maxima=self._atual.maxima,
            minima=self._atual.minima,
            fechamento=self._atual.fechamento,
        )
        self._atual = _CandleEmFormacao(periodo, preco, preco, preco, preco)
        return candle_fechado

    def candle_em_formacao(self) -> Optional[Candle]:
        """Devolve o estado atual da vela ainda nao fechada (util para monitorar sem esperar o fechamento)."""
        if self._atual is None:
            return None
        return Candle(
            horario=self._atual.inicio,
            abertura=self._atual.abertura,
            maxima=self._atual.maxima,
            minima=self._atual.minima,
            fechamento=self._atual.fechamento,
        )
