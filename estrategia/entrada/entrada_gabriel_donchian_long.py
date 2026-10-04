"""Candidata independente: rompimento de canal Donchian para compra.

Origem e autoria: Gabriel (fonte do ZIP ``donchian_long.py``), com adaptação
Manus para o contrato funcional V465. Variações testadas: 0. Revisão humana
pendente; este arquivo não é titular, não é validação de rentabilidade e não
foi executado na classificação oficial nem em histórico oficial.

A adaptação preserva ``channel=20``, filtro de expansão por amplitude/volume,
``volume_ratio=1.00`` e a supressão causal de sinais long consecutivos da
fonte. Assunção de quantidade por candle: ``gabriel_barras[*]["Quantidade"]``
é a mesma unidade de quantidade/volume por candle usada por ``Bar.volume`` na
fonte original; não se usa volume financeiro e ``None`` nunca é convertido em
zero. Como a hipótese depende desse campo, qualquer quantidade indispensável
ao cálculo atual ou à reconstrução causal do candle anterior faz a função
retornar 0.

Não há estado entre chamadas, I/O, rede, imports do projeto, execução dinâmica
ou acesso a arquivos. Stop/alvo não são definidos aqui: a fonte original usa a
mesma fórmula já coberta por ``saida_daytrader_rr2_v1``; portanto uma saída
Gabriel duplicada foi deliberadamente omitida.
"""

from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")
UM = Decimal("1")
JANELA = 20
RAZAO_VOLUME = Decimal("1.00")
FATOR_EXPANSAO_RANGE = Decimal("1.15")
FATOR_EXPANSAO_VOLUME = Decimal("1.10")


def _decimal(valor):
    """Converte um campo numérico sem aceitar valores não finitos."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return numero if numero.is_finite() else None


def _candle(candle):
    """Extrai apenas os campos que ``DonchianLongStrategy`` realmente usa."""
    if not isinstance(candle, dict):
        return None

    maxima = _decimal(candle.get("Maximo"))
    minima = _decimal(candle.get("Minimo"))
    fechamento = _decimal(candle.get("Fechamento"))
    quantidade_bruta = candle.get("Quantidade")
    if quantidade_bruta is None:
        return None
    quantidade = _decimal(quantidade_bruta)

    # Quantidade é documentada como não negativa. Não transformar ausência em
    # zero também impede que o fallback de média de volume da fonte seja
    # acionado indevidamente por dado desconhecido.
    if (
        maxima is None
        or minima is None
        or fechamento is None
        or quantidade is None
        or quantidade < ZERO
    ):
        return None

    return maxima, minima, fechamento, quantidade


def _sinal_bruto(barras):
    """Reproduz ``_signal`` da fonte para 20 candles anteriores e o atual."""
    anteriores = barras[:-1]
    atual = barras[-1]
    recentes = anteriores[-JANELA:]

    amplitudes = [maxima - minima for maxima, minima, _, _ in recentes]
    media_amplitude = sum(amplitudes, ZERO) / Decimal(JANELA)
    media_quantidade = sum(
        (quantidade for _, _, _, quantidade in recentes), ZERO
    ) / Decimal(JANELA)

    if media_quantidade > ZERO:
        volume_relativo = atual[3] / media_quantidade
    else:
        # É o fallback explícito da fonte para média de volume igual a zero;
        # ele só ocorre quando os valores presentes são zeros, nunca por None.
        volume_relativo = UM

    amplitude_atual = atual[0] - atual[1]
    expansao = (
        amplitude_atual >= media_amplitude * FATOR_EXPANSAO_RANGE
        or volume_relativo >= FATOR_EXPANSAO_VOLUME
    )
    if not expansao:
        return 0

    maior_maxima = max(maxima for maxima, _, _, _ in recentes)
    if atual[2] > maior_maxima and volume_relativo >= RAZAO_VOLUME:
        return 1
    return 0


def gerar_sinal(row) -> int:
    """Retorna 1 no rompimento confirmado, ou 0 sem dados/sinal suficiente."""
    if not isinstance(row, dict):
        return 0

    historico = row.get("gabriel_barras")
    if not isinstance(historico, (tuple, list)) or len(historico) < JANELA + 2:
        # São necessários 22 candles: 20 anteriores para o candle atual e o
        # candle imediatamente anterior para reconstituir _last_direction.
        return 0

    # O motor fornece até 96 candles; somente a janela causal final é usada.
    barras = [_candle(candle) for candle in historico[-(JANELA + 2):]]
    if any(candle is None for candle in barras):
        return 0

    atual = _sinal_bruto(barras[-(JANELA + 1):])
    if atual == 0:
        return 0

    # Na fonte, _last_direction é limpo quando o candle anterior não gera
    # sinal. Comparar os dois sinais brutos reproduz essa memória sem global.
    anterior = _sinal_bruto(barras[-(JANELA + 2):-1])
    return 0 if anterior == atual else atual


__all__ = ["gerar_sinal"]
