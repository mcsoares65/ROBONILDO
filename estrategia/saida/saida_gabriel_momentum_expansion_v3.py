"""Saída da candidata Gabriel Momentum Expansion v3 — compra.

Autoria: Gabriel (fonte original do ZIP) / adaptação Manus; revisão humana
pendente. Esta é uma candidata independente, não titular, e ``v3`` é a
numeração própria da hipótese, não a VERSAO do projeto. Variações testadas
antes desta versão: 0. Resultado oficial ainda não medido.

A regra é portada de ``gen3/momentum_expansion_v3.py``: na abertura, o stop
em pontos é a distância do fechamento atual ao menor entre a mínima atual e as
mínimas dos três candles anteriores, menos 5 pontos, arredondada para cima no
tick de 5; o alvo é 2R, também arredondado para cima no tick de 5. O orçamento
original (R$20,00 / R$0,20 por ponto) impõe máximo de 100 pontos. Os níveis
retornados são preços absolutos relativos a ``posicao['entrada']``.

A fonte é long-only (``Side.BUY``). Para satisfazer o cruzamento S001 da
V465, VENDA de outras entradas recebe um espelho estrutural de quatro
candles com gate de 100 pontos; essa proteção de venda é adaptação Manus,
NÃO regra validada de Gabriel. Quantidade não é necessária para stop/alvo. A entrada
parceira, que depende da Quantidade como volume, devolve 0 quando esse dado
necessário está ausente e nunca o troca por zero.

Sem I/O, rede, arquivo, estado global acumulado, imports do projeto,
``exec`` ou ``eval``. Contrato: ``avaliar_saida(row, posicao) -> dict | bool``.
Na abertura define ambos os níveis; depois não fecha nem reconfigura.
"""

from decimal import Decimal, InvalidOperation, ROUND_CEILING
from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_gabriel_momentum_expansion_v3"
TICK = Decimal("5")
REWARD_RISK = Decimal("2")
MAX_STOP_POINTS = Decimal("100")


def _numero(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Valor numérico inválido: {value!r}")
    if not number.is_finite():
        raise ValueError(f"Valor numérico não finito: {value!r}")
    return number


def _barras(row):
    if not isinstance(row, dict):
        raise TypeError("row precisa ser um dicionário.")
    bruto = row.get("gabriel_barras")
    if not bruto or len(bruto) < 4:
        raise ValueError("São necessários o candle atual e os três anteriores.")
    return bruto


def _stop_alvo_pontos(row, posicao, lado):
    barras = _barras(row)
    atual = barras[-1]
    anteriores = barras[-4:-1]
    minima_atual = _numero(atual["Minimo"])
    minimas_anteriores = [_numero(candle["Minimo"]) for candle in anteriores]
    fechamento_atual = _numero(atual["Fechamento"])
    if lado == "COMPRA":
        stop_level = min(minima_atual, *minimas_anteriores) - TICK
        distancia = fechamento_atual - stop_level
    else:
        maxima_atual = _numero(atual["Maximo"])
        maximas_anteriores = [_numero(candle["Maximo"]) for candle in anteriores]
        stop_level = max(maxima_atual, *maximas_anteriores) + TICK
        distancia = stop_level - fechamento_atual
    if distancia <= Decimal("0"):
        raise ValueError("Stop estrutural inválido.")
    # Compra pareada Gabriel já passou no gate de 100 pontos na entrada;
    # outras combinações cruzadas recebem o teto para manter proteção S001.
    stop_points = min(_round_up_tick(distancia), MAX_STOP_POINTS)
    alvo_points = _round_up_tick(stop_points * REWARD_RISK)
    return stop_points, alvo_points


def _round_up_tick(points):
    if points <= Decimal("0"):
        return TICK
    units = (points / TICK).to_integral_value(rounding=ROUND_CEILING)
    return units * TICK


def _protecao_inicial(row, posicao):
    lado = str(posicao.get("lado", "")).upper()
    if lado not in ("COMPRA", "VENDA"):
        raise ValueError("Lado inválido.")
    entrada = _numero(posicao["entrada"])
    stop_points, alvo_points = _stop_alvo_pontos(row, posicao, lado)
    sentido = Decimal("1") if lado == "COMPRA" else Decimal("-1")
    stop = entrada - sentido * stop_points
    alvo = entrada + sentido * alvo_points
    if not isfinite(float(stop)) or not isfinite(float(alvo)):
        raise ValueError("Proteção inicial não finita.")
    return float(stop), float(alvo)


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(posicao, dict):
        raise TypeError("posicao precisa ser um dicionário.")
    try:
        candles = int(posicao.get("candles_decorridos", 0))
    except (TypeError, ValueError) as erro:
        raise ValueError("candles_decorridos inválido.") from erro
    if candles < 0:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {"fechar": False, "novo_stop": None, "novo_alvo": None}


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida"]
