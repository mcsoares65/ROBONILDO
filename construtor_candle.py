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
from math import isfinite

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
    quantidade: Optional[float] = None


class ConstrutorCandle:
    def __init__(self, minutos: int = 15):
        self.minutos = minutos
        self._atual: Optional[_CandleEmFormacao] = None

    def nova_leitura(self, preco: float, horario: datetime,
                    quantidade_incremento: Optional[float] = None) -> Optional[Candle]:
        """
        Registra uma leitura de preco. Se essa leitura pertence a um novo periodo
        de 15 min (o periodo anterior encerrou), devolve o Candle fechado do
        periodo anterior. Caso contrario, devolve None. Quantidade é opcional:
        somente incrementos válidos em TODAS as leituras compõem o candle.
        A origem DDE e a unidade ainda exigem confirmação; não inferir zero.
        """
        periodo = inicio_do_periodo(horario, self.minutos)
        q = (float(quantidade_incremento)
             if quantidade_incremento is not None and isfinite(quantidade_incremento)
             and quantidade_incremento >= 0 else None)

        if self._atual is None:
            self._atual = _CandleEmFormacao(periodo, preco, preco, preco, preco, q)
            return None

        if periodo == self._atual.inicio:
            # mesma vela em formacao - so atualiza maxima/minima/fechamento
            self._atual.maxima = max(self._atual.maxima, preco)
            self._atual.minima = min(self._atual.minima, preco)
            self._atual.fechamento = preco
            self._atual.quantidade = (self._atual.quantidade + q
                                      if self._atual.quantidade is not None and q is not None
                                      else None)
            return None

        # periodo novo comecou -> a vela anterior fechou
        candle_fechado = Candle(
            horario=self._atual.inicio,
            abertura=self._atual.abertura,
            maxima=self._atual.maxima,
            minima=self._atual.minima,
            fechamento=self._atual.fechamento,
            quantidade=self._atual.quantidade,
        )
        self._atual = _CandleEmFormacao(periodo, preco, preco, preco, preco, q)
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
            quantidade=self._atual.quantidade,
        )



def candles_faltando(ultimo, novo, minutos, primeiro="09:00", ultimo_rotulo="18:15", feriados=()):
    """V461: quantos candles de pregao regular FALTAM entre `ultimo` e `novo`
    (ambos horarios de abertura de candle, exclusivos). Fim de semana, feriado
    e a noite nao contam: sexta 18:15 -> segunda 09:00 devolve 0, mas
    segunda 18:15 -> quinta 10:00 devolve 3 pregoes + manha inteira."""
    from datetime import datetime, timedelta
    h0, m0 = (int(x) for x in primeiro.split(":"))
    h1, m1 = (int(x) for x in ultimo_rotulo.split(":"))
    faltam = 0
    dia = ultimo.date()
    while dia <= novo.date():
        if dia.weekday() < 5 and dia.isoformat() not in feriados:
            t = datetime(dia.year, dia.month, dia.day, h0, m0)
            fim = datetime(dia.year, dia.month, dia.day, h1, m1)
            while t <= fim:
                if ultimo < t < novo:
                    faltam += 1
                t += timedelta(minutes=minutos)
        dia += timedelta(days=1)
    return faltam
