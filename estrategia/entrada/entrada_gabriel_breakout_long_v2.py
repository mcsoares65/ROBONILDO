"""Candidata independente de entrada: ``breakout_long_v2``.

Autoria: Gabriel, a partir do ZIP original; adaptação Manus.
Variações testadas: 0.
Revisão humana: pendente.
A hipótese original usa ``Bar.volume``; a adaptação assume que
``row["gabriel_barras"][i]["Quantidade"]`` é a quantidade por candle na mesma
unidade. Como essa equivalência ainda não foi confirmada, qualquer Quantidade
necessária ausente faz a função retornar 0, sem substituição por zero.

A fila e o ``_last_direction`` do original são reconstruídos causalmente a
partir da janela pública. A janela usada é limitada aos 22 candles finais,
porque apenas o candle atual e o anterior precisam ser reavaliados para
reproduzir a supressão de sinais consecutivos; não há estado entre chamadas.
A proteção original (stop de 1,25 vezes a amplitude média, piso de 20 e alvo
2R) não gera um arquivo de saída aqui: ela é tecnicamente a mesma regra já
presente em ``saida_daytrader_rr2_v1`` e não deve ser clonada.

Não há alegação de validação ou de resultado. O candle final é tratado como a
observação recebida; a confirmação de fechamento permanece responsabilidade
do motor que fornece ``row``.
"""

from decimal import Decimal, InvalidOperation


_ZERO = Decimal("0")
_JANELA = 20
_JANELA_CURTA = 5
_COMPRESSAO = Decimal("0.85")
_EXPANSAO = Decimal("1.20")
_VOLUME = Decimal("1.10")
_EXPANSAO_REGIME = Decimal("1.15")
_MAX_BARRAS_RELEVANTES = _JANELA + 2


def _decimal(valor):
    """Converte um número da linha sem fabricar dados."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not numero.is_finite():
        return None
    return numero


def _barras_relevantes(row):
    """Lê apenas a janela causal necessária, exigindo Quantidade real."""
    if not isinstance(row, dict):
        return ()
    historico = row.get("gabriel_barras")
    if not historico:
        return ()

    try:
        brutas = list(historico[-_MAX_BARRAS_RELEVANTES:])
    except (TypeError, IndexError):
        return ()
    if len(brutas) < _JANELA + 1:
        return ()

    barras = []
    for candle in brutas:
        if not isinstance(candle, dict):
            return ()
        maxima = _decimal(candle.get("Maximo"))
        minima = _decimal(candle.get("Minimo"))
        fechamento = _decimal(candle.get("Fechamento"))
        quantidade = candle.get("Quantidade")
        if maxima is None or minima is None or fechamento is None:
            return ()
        # None significa dado indisponível; não é volume zero.
        if quantidade is None:
            return ()
        quantidade = _decimal(quantidade)
        if quantidade is None or quantidade < _ZERO:
            return ()
        barras.append((maxima, minima, fechamento, quantidade))
    return tuple(barras)


def _sinal_bruto(candle, anteriores):
    """Implementa ``BreakoutLongV2Strategy._signal`` sem memória global."""
    if len(anteriores) < _JANELA:
        return 0

    recentes20 = anteriores[-_JANELA:]
    recentes5 = anteriores[-_JANELA_CURTA:]
    amplitudes = [maxima - minima for maxima, minima, _, _ in recentes20]
    media_amplitude = sum(amplitudes, _ZERO) / Decimal(_JANELA)
    volumes = [quantidade for _, _, _, quantidade in recentes20]
    media_volume = sum(volumes, _ZERO) / Decimal(_JANELA)

    _, _, fechamento, quantidade = candle
    relacao_volume = (
        quantidade / media_volume if media_volume > _ZERO else Decimal("1")
    )
    amplitude_atual = candle[0] - candle[1]

    expansao_regime = (
        amplitude_atual >= media_amplitude * _EXPANSAO_REGIME
        or relacao_volume >= _VOLUME
    )
    if not expansao_regime:
        return 0

    amplitude_curta = sum(
        (maxima - minima for maxima, minima, _, _ in recentes5),
        _ZERO,
    ) / Decimal(_JANELA_CURTA)
    comprimido = amplitude_curta <= media_amplitude * _COMPRESSAO
    expandido = amplitude_atual >= media_amplitude * _EXPANSAO
    rompeu_para_cima = fechamento > max(maxima for maxima, _, _, _ in recentes20)

    if comprimido and expandido and relacao_volume >= _VOLUME and rompeu_para_cima:
        return 1
    return 0


def gerar_sinal(row) -> int:
    """Retorna 1 para breakout comprador, ou 0 quando não há confirmação."""
    barras = _barras_relevantes(row)
    if len(barras) < _JANELA + 1:
        return 0

    atual = _sinal_bruto(barras[-1], barras[-(_JANELA + 1):-1])
    if atual == 0:
        return 0

    # No original, um sinal igual ao do candle imediatamente anterior é
    # suprimido enquanto _last_direction permanece BUY. Recalcular o candle
    # anterior reproduz essa memória sem carregar estado entre chamadas.
    if len(barras) >= _JANELA + 2:
        anterior = _sinal_bruto(barras[-2], barras[-(_JANELA + 2):-2])
        if anterior == atual:
            return 0
    return atual


__all__ = ["gerar_sinal"]
