"""Cadastro de cenários de mercado (o "técnico" olha o campo antes de escalar).

Cada cenário é uma situação do mercado reconhecível A PARTIR DO CANDLE FECHADO
(a row de motor.construir_row): nunca usa informação futura. Os cenários são
mutuamente exclusivos: vale o primeiro da lista CENARIOS (ordem = prioridade).

Todas as medidas são adimensionais (múltiplos de ATR ou razões entre 0 e 1), de
modo que os limites não dependem do nível de preço nem de um período
específico (Regra 11.3). Candle fora de qualquer cenário = 'indefinido' (zona
cinzenta entre lateral e tendência): o técnico não escala ninguém novo.
Os limites foram escolhidos pela distribuição das MEDIDAS (nunca pelo resultado
de estratégia) e conferidos contra o gabarito do simulador; não devem ser
ajustados para encaixar o lucro de um histórico.

Este módulo só RECONHECE o cenário. Quem decide qual dupla entrada x saída
joga em cada cenário é a tabela de escalação (a ser definida com evidência).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Callable, Optional

# --- limites fixos --------------------------------------------------------
FIM_ABERTURA = time(9, 45)        # candles rotulados antes disso = abertura
INICIO_FIM_DE_TARDE = time(16, 30)
ATR_REL_VOLATIL = 1.25            # ATR >= 1,25x a média de 50 candles
ESTICAMENTO_MIN = 2.00            # |fechamento - MA21| >= 2 ATR
EFICIENCIA_TENDENCIA = 0.45       # eficiência de Kaufman (12 fechamentos) >= 0,45
EFICIENCIA_LATERAL = 0.20         # ... <= 0,20 = vai e volta sem sair do lugar
CONFIRMACOES_PADRAO = 2           # candles seguidos para o técnico trocar de cenário

INDEFINIDO = "indefinido"


@dataclass(frozen=True)
class Cenario:
    nome: str
    descricao: str
    reconhece: Callable[[dict], bool]


def caracteristicas(row: dict) -> Optional[dict]:
    """Medidas normalizadas usadas pelos reconhecedores. None se a row não tem
    indicadores válidos (início do histórico)."""
    if not row:
        return None
    atr, ma21, fech = row.get("atr"), row.get("MA21"), row.get("Fechamento")
    janela = row.get("ohlc_recentes") or ()
    if None in (atr, ma21, fech) or not atr or atr <= 0 or len(janela) < 12:
        return None
    fechamentos = [c["Fechamento"] for c in janela]
    percurso = sum(abs(b - a) for a, b in zip(fechamentos, fechamentos[1:]))
    atr_rel = row.get("atr_relativo")
    return {
        "hora": row["dt"].time(),
        "esticamento": (fech - ma21) / atr,          # com sinal: + acima da MA21
        # Eficiência de Kaufman: deslocamento líquido / percurso total. 1 = linha
        # reta; perto de 0 = o preço anda, anda e não sai do lugar.
        "eficiencia": abs(fechamentos[-1] - fechamentos[0]) / percurso if percurso > 0 else 0.0,
        "direcao": 1 if fechamentos[-1] > fechamentos[0] else (-1 if fechamentos[-1] < fechamentos[0] else 0),
        "atr_rel": atr_rel if atr_rel is not None else 1.0,
    }


def _abertura(c): return c["hora"] < FIM_ABERTURA
def _fim_de_tarde(c): return c["hora"] >= INICIO_FIM_DE_TARDE
def _volatil(c): return c["atr_rel"] >= ATR_REL_VOLATIL
def _esticado(c): return abs(c["esticamento"]) >= ESTICAMENTO_MIN
def _tendencia(c): return c["eficiencia"] >= EFICIENCIA_TENDENCIA
def _lateral(c): return c["eficiencia"] <= EFICIENCIA_LATERAL


# Ordem = prioridade. O que vem antes "ganha" quando mais de um serve.
CENARIOS: tuple[Cenario, ...] = (
    Cenario("abertura", "primeiros candles do pregão (antes das 09:45)", lambda r: _abertura(r)),
    Cenario("fim_de_tarde", "a partir das 16:30, perto do corte e do fechamento", lambda r: _fim_de_tarde(r)),
    Cenario("volatil", "ATR >= 1,25x a média de 50 candles: mercado agitado", lambda r: _volatil(r)),
    Cenario("esticado", "preço a 2 ATR ou mais da MA21", lambda r: _esticado(r)),
    Cenario("tendencia", "preço andando em linha (eficiência >= 0,45 nos últimos 12 fechamentos)", lambda r: _tendencia(r)),
    Cenario("lateral", "preço vai e volta sem sair do lugar (eficiência <= 0,20)", lambda r: _lateral(r)),
)
NOMES = tuple(c.nome for c in CENARIOS) + (INDEFINIDO,)


def classificar(row: Optional[dict]) -> str:
    """Nome do cenário do candle (primeiro que reconhece), ou 'indefinido'."""
    c = caracteristicas(row)
    if c is None:
        return INDEFINIDO
    for cenario in CENARIOS:
        if cenario.reconhece(c):
            return cenario.nome
    return INDEFINIDO


class Acompanhante:
    """O técnico à beira do campo: só troca o cenário confirmado depois de
    `confirmacoes` candles seguidos no novo cenário (evita trocar a cada candle).

    atualizar(row) devolve (cenario_confirmado, mudou). Reinicie por pregão com
    novo_pregao() se quiser que cada dia comece do zero."""

    def __init__(self, confirmacoes: int = CONFIRMACOES_PADRAO):
        if confirmacoes < 1:
            raise ValueError("confirmacoes precisa ser >= 1")
        self.confirmacoes = confirmacoes
        self.atual = INDEFINIDO
        self._candidato = None
        self._contagem = 0

    def novo_pregao(self) -> None:
        self.atual, self._candidato, self._contagem = INDEFINIDO, None, 0

    def atualizar(self, row: Optional[dict]) -> tuple[str, bool]:
        visto = classificar(row)
        if visto == self.atual:
            self._candidato, self._contagem = None, 0
            return self.atual, False
        if visto == self._candidato:
            self._contagem += 1
        else:
            self._candidato, self._contagem = visto, 1
        if self._contagem >= self.confirmacoes:
            self.atual, self._candidato, self._contagem = visto, None, 0
            return self.atual, True
        return self.atual, False
