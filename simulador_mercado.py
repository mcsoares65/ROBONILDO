"""Simulador de mercado WINFUT 15min para o laboratório (classificacao.py).

Gera um histórico FICTÍCIO, reprodutível por semente, para testar as estratégias
em cenários que o histórico real não cobre. Não faz parte do robô ao vivo e não
é um cartucho de estratégia.

Dois modos:

  reamostragem  Sorteia pregões REAIS (com reposição) e os encadeia numa ordem
                nova. Cada pregão sorteado mantém sua estrutura intradiária
                real; o gap de abertura vem de gaps reais. Opcionalmente espelha
                o pregão (compra vira venda) para neutralizar a deriva da amostra.
                É o modo mais próximo do mercado real.

  regimes       Gera os candles por regimes explícitos (tendência de alta,
                tendência de baixa, lateral, volátil), calibrados na volatilidade
                do histórico real. Os regimes mudam entre pregões e, às vezes,
                no meio do pregão. Cada candle recebe o rótulo do regime que o
                gerou (verdade conhecida), útil para testar reconhecedores de
                cenário.

Limitação: o simulador só reproduz o que está nas suas premissas. Serve para
estressar e comparar comportamento, não para estimar lucro futuro.
"""

from __future__ import annotations

import csv
import math
import random
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from motor import Candle

TICK = 5.0                      # variação mínima do WINFUT
DATA_INICIAL_PADRAO = date(2035, 1, 3)   # claramente fictícia: não colide com dados reais
MODOS = ("reamostragem", "regimes")

# Regimes do modo "regimes": (deriva por candle em sigmas, autocorrelação,
# multiplicador de volatilidade). Autocorrelação negativa = tende a reverter.
REGIMES = {
    "tendencia_alta":  (+0.35, +0.20, 1.00),
    "tendencia_baixa": (-0.35, +0.20, 1.00),
    "lateral":         (0.00, -0.35, 0.65),
    "volatil":         (0.00, 0.00, 1.70),
}
PROB_MANTER_REGIME = 0.55       # chance de o regime do pregão repetir o anterior
PROB_TROCA_NO_PREGAO = 0.25     # chance de haver troca de regime no meio do pregão


def _arredonda(valor: float) -> float:
    return round(valor / TICK) * TICK


def _dias_reais(candles: list[Candle]) -> list[list[Candle]]:
    por_dia = defaultdict(list)
    for c in candles:
        por_dia[c.horario.date()].append(c)
    dias = [sorted(v, key=lambda c: c.horario) for _, v in sorted(por_dia.items())]
    return dias


def _grade_horaria(dias: list[list[Candle]]) -> list[tuple[int, int]]:
    """Grade de horários do pregão completo mais comum no histórico real."""
    contagem = Counter(tuple((c.horario.hour, c.horario.minute) for c in d) for d in dias)
    return list(contagem.most_common(1)[0][0])


def _proximo_dia_util(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _montar_candle(dia: date, hm: tuple[int, int], o: float, h: float, l: float, c: float) -> Candle:
    h = max(h, o, c)
    l = min(l, o, c)
    return Candle(datetime(dia.year, dia.month, dia.day, hm[0], hm[1]),
                  _arredonda(o), _arredonda(h), _arredonda(l), _arredonda(c))


def _gerar_reamostragem(dias, n_dias, rng, escala_vol, espelhar, inicio, preco_inicial):
    completos = [d for d in dias if len(d) >= 30] or dias
    gaps = [
        dias[i][0].abertura - dias[i - 1][-1].fechamento
        for i in range(1, len(dias))
    ] or [0.0]
    candles: list[Candle] = []
    rotulos: dict[datetime, str] = {}
    dia = inicio
    ultimo_fechamento = preco_inicial
    for k in range(n_dias):
        origem = rng.choice(completos)
        sinal = -1.0 if (espelhar and rng.random() < 0.5) else 1.0
        base = origem[0].abertura
        abertura_dia = ultimo_fechamento + (0.0 if k == 0 else rng.choice(gaps) * escala_vol * sinal)
        for c in origem:
            o = abertura_dia + (c.abertura - base) * sinal * escala_vol
            h = abertura_dia + (c.maxima - base) * sinal * escala_vol
            l = abertura_dia + (c.minima - base) * sinal * escala_vol
            f = abertura_dia + (c.fechamento - base) * sinal * escala_vol
            if sinal < 0:
                h, l = l, h
            novo = _montar_candle(dia, (c.horario.hour, c.horario.minute), o, h, l, f)
            candles.append(novo)
            rotulos[novo.horario] = (
                f"real:{origem[0].horario.date().isoformat()}" + ("(espelhado)" if sinal < 0 else "")
            )
        ultimo_fechamento = candles[-1].fechamento
        dia = _proximo_dia_util(dia)
    return candles, rotulos


def _sigma_candle(dias) -> float:
    """Desvio típico (robusto) da variação fechamento-a-fechamento de um candle."""
    variacoes = []
    for d in dias:
        for a, b in zip(d, d[1:]):
            variacoes.append(b.fechamento - a.fechamento)
    if not variacoes:
        return 100.0
    centro = sorted(variacoes)[len(variacoes) // 2]
    desvios = sorted(abs(v - centro) for v in variacoes)
    return max(1.4826 * desvios[len(desvios) // 2], TICK)


def _gerar_regimes(dias, n_dias, rng, escala_vol, inicio, preco_inicial):
    # Calibra a volatilidade para o candle simulado ter a mesma amplitude mediana
    # (maxima - minima) do histórico real; a escala_vol do usuário vem por cima.
    alvo = _mediana([c.maxima - c.minima for d in dias for c in d])
    sigma = _sigma_candle(dias)
    for _ in range(3):
        teste, _r = _gerar_regimes_com_sigma(dias, 40, random.Random(12345), sigma, inicio, preco_inicial)
        obtido = _mediana([c.maxima - c.minima for c in teste])
        if obtido > 0:
            sigma *= alvo / obtido
    return _gerar_regimes_com_sigma(dias, n_dias, rng, sigma * escala_vol, inicio, preco_inicial)


def _mediana(valores):
    v = sorted(valores)
    return v[len(v) // 2] if v else 0.0


def _gerar_regimes_com_sigma(dias, n_dias, rng, sigma, inicio, preco_inicial):
    grade = _grade_horaria(dias)
    nomes = list(REGIMES)
    gaps = [abs(dias[i][0].abertura - dias[i - 1][-1].fechamento) for i in range(1, len(dias))] or [0.0]
    gap_tipico = sorted(gaps)[len(gaps) // 2]

    candles: list[Candle] = []
    rotulos: dict[datetime, str] = {}
    dia = inicio
    preco = preco_inicial
    regime = rng.choice(nomes)
    for k in range(n_dias):
        if k > 0 and rng.random() > PROB_MANTER_REGIME:
            regime = rng.choice(nomes)
        troca_em = rng.randrange(8, len(grade) - 6) if rng.random() < PROB_TROCA_NO_PREGAO else None
        regime_candle = regime
        if k > 0:
            sinal_gap = 1.0 if rng.random() < 0.5 else -1.0
            preco += sinal_gap * abs(rng.gauss(0, gap_tipico))
        r_ant = 0.0
        for i, hm in enumerate(grade):
            if troca_em is not None and i == troca_em:
                regime_candle = rng.choice([n for n in nomes if n != regime])
            deriva, phi, mult = REGIMES[regime_candle]
            # t de Student (df=5): caudas mais pesadas que a normal
            z = rng.gauss(0, 1) / math.sqrt(sum(rng.gauss(0, 1) ** 2 for _ in range(5)) / 5)
            r = deriva * sigma + phi * r_ant + mult * sigma * z * 0.8
            r_ant = r
            o = preco
            f = o + r
            pavio = abs(rng.gauss(0, 0.45 * mult * sigma))
            h = max(o, f) + abs(rng.gauss(0, 0.45 * mult * sigma))
            l = min(o, f) - pavio
            novo = _montar_candle(dia, hm, o, h, l, f)
            candles.append(novo)
            rotulos[novo.horario] = regime_candle
            preco = novo.fechamento
        dia = _proximo_dia_util(dia)
    return candles, rotulos


def gerar_candles(
    candles_reais: list[Candle],
    n_dias: int = 120,
    semente: Optional[int] = None,
    modo: str = "reamostragem",
    escala_vol: float = 1.0,
    espelhar: bool = True,
    inicio: date = DATA_INICIAL_PADRAO,
) -> tuple[list[Candle], dict, int]:
    """Gera candles fictícios. Retorna (candles, rotulos_por_horario, semente_usada).

    A mesma semente com os mesmos parâmetros e o mesmo histórico real reproduz o
    mesmo resultado, candle a candle.
    """
    if modo not in MODOS:
        raise ValueError(f"modo inválido '{modo}'; use um de {MODOS}")
    if n_dias < 3:
        raise ValueError("a simulação precisa de pelo menos 3 pregões")
    dias = _dias_reais(candles_reais)
    if len(dias) < 5:
        raise ValueError("histórico real insuficiente (mínimo 5 pregões) para calibrar o simulador")
    if semente is None:
        semente = random.SystemRandom().randrange(1, 10**6)
    rng = random.Random(semente)
    preco_inicial = _arredonda(dias[-1][-1].fechamento)
    if modo == "reamostragem":
        candles, rotulos = _gerar_reamostragem(
            dias, n_dias, rng, escala_vol, espelhar, inicio, preco_inicial)
    else:
        candles, rotulos = _gerar_regimes(dias, n_dias, rng, escala_vol, inicio, preco_inicial)
    return candles, rotulos, semente


def salvar_csv(candles: list[Candle], caminho: Path, ativo: str = "WINFUT") -> Path:
    """Grava no mesmo formato do export do Profit (mais novo primeiro), para que o
    mesmo CSV possa ser relido pelo classificacao.py e auditado depois."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    def num(v: float) -> str:
        return f"{v:.2f}".replace(".", ",")

    with caminho.open("w", newline="", encoding="latin1") as f:
        w = csv.writer(f, delimiter=";")
        for c in sorted(candles, key=lambda x: x.horario, reverse=True):
            w.writerow([ativo, c.horario.strftime("%d/%m/%Y"), c.horario.strftime("%H:%M:%S"),
                        num(c.abertura), num(c.maxima), num(c.minima), num(c.fechamento),
                        num(0), 0])
    return caminho


def salvar_rotulos(rotulos: dict, caminho: Path) -> Path:
    caminho = Path(caminho)
    with caminho.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["horario", "origem_ou_regime"])
        for h in sorted(rotulos):
            w.writerow([h.strftime("%d/%m/%Y %H:%M:%S"), rotulos[h]])
    return caminho
