"""Candidata Gabriel: ``dual_momentum_long_v2`` — compra.

Autoria: Gabriel, a partir do ZIP original; adaptação Manus. Revisão humana:
pendente. Variações testadas: 0. A numeração ``v2`` identifica a versão da
hipótese original de Gabriel, não a VERSAO do projeto.

Portabilidade funcional e sem estado da ``DualMomentumLongV2Strategy``:
usa somente ``row["gabriel_barras"]`` e reconstrói o candle atual e o anterior
causalmente a partir da janela entregue pelo motor. A fonte usa ``Bar.volume``;
a assunção desta adaptação é que ``Quantidade`` representa a quantidade por
candle equivalente a esse campo. A unidade/equivalência ainda não foi
confirmada: ``Quantidade`` ausente (``None`` ou chave ausente) não é substituída
por zero e encerra com sinal 0, conforme o contrato Gabriel. Quantidade zero
presente é preservada e segue a semântica da fonte (média de volume zero torna
a razão relativa 1, que não atinge o filtro 1,10).

A fonte original também fixa, na abertura, stop de ``max(20, round(1,25 *
média das amplitudes dos 20 candles anteriores))`` e alvo de ``max(stop + 5,
round(2 * stop))`` pontos. Essa regra é tecnicamente a mesma já preservada por
``saida_daytrader_rr2_v1``; por isso esta candidata não cria uma saída duplicada.
O arquivo não importa módulos do projeto, não faz I/O, rede ou estado global e
não foi submetido à classificação oficial nem a histórico.
"""

from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")
JANELA = 20
JANELA_CURTA = 5
RAZAO_VOLUME = Decimal("1.10")
MULTIPLICADOR_MOMENTO_LONGO = Decimal("1.00")
RAZAO_AMPLITUDE = Decimal("1.05")
LIMIAR_TENDENCIA = Decimal("0.20")
LIMIAR_EXPANSAO = Decimal("1.15")


def _numero(valor):
    """Converte um campo OHLC/Quantidade finito, ou devolve None."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return numero if numero.is_finite() else None


def _barras(row):
    """Normaliza apenas as barras necessárias, sem fabricar volume."""
    historico = row.get("gabriel_barras") or ()
    if len(historico) < JANELA + 1:
        return None

    barras = []
    for bruto in historico[-(JANELA + 2):]:
        abertura = _numero(bruto.get("Abertura"))
        maxima = _numero(bruto.get("Maximo"))
        minima = _numero(bruto.get("Minimo"))
        fechamento = _numero(bruto.get("Fechamento"))
        quantidade = _numero(bruto.get("Quantidade"))
        if None in (abertura, maxima, minima, fechamento):
            return None
        if quantidade is not None and quantidade < ZERO:
            return None
        barras.append(
            {
                "open": abertura,
                "high": maxima,
                "low": minima,
                "close": fechamento,
                "quantity": quantidade,
            }
        )
    return barras


def _sinal_bruto(atual, anteriores):
    """Retorna o sinal da fonte para uma barra, sem a supressão de estado."""
    if len(anteriores) < JANELA:
        return 0

    recentes20 = anteriores[-JANELA:]
    recentes5 = anteriores[-JANELA_CURTA:]
    volumes = [barra["quantity"] for barra in recentes20]

    # A fonte depende de volume em todos os 20 candles anteriores e no atual.
    # Sem qualquer um deles a adaptação não inventa zero nem outra medida.
    if atual["quantity"] is None or any(volume is None for volume in volumes):
        return 0

    sma20 = sum((barra["close"] for barra in recentes20), ZERO) / Decimal(JANELA)
    sma5 = sum((barra["close"] for barra in recentes5), ZERO) / Decimal(JANELA_CURTA)
    media_amplitude = (
        sum((barra["high"] - barra["low"] for barra in recentes20), ZERO)
        / Decimal(JANELA)
    )
    media_volume = sum(volumes, ZERO) / Decimal(JANELA)

    if media_volume > ZERO:
        volume_relativo = atual["quantity"] / media_volume
    else:
        volume_relativo = Decimal("1")

    tendencia = sma5 - sma20
    amplitude_atual = atual["high"] - atual["low"]
    eh_tendencia = abs(tendencia) >= media_amplitude * LIMIAR_TENDENCIA
    eh_expansao = (
        amplitude_atual >= media_amplitude * LIMIAR_EXPANSAO
        or volume_relativo >= RAZAO_VOLUME
    )

    # regime_filter = trend_expansion é o parâmetro padrão da fonte.
    if not (eh_tendencia and eh_expansao):
        return 0

    momento_curto = atual["close"] - recentes5[0]["close"]
    momento_longo = atual["close"] - recentes20[0]["close"]
    if (
        tendencia > ZERO
        and sma5 > sma20
        and momento_curto > media_amplitude * LIMIAR_TENDENCIA
        and momento_longo > media_amplitude * MULTIPLICADOR_MOMENTO_LONGO
        and volume_relativo >= RAZAO_VOLUME
        and amplitude_atual >= media_amplitude * RAZAO_AMPLITUDE
    ):
        return 1
    return 0


def gerar_sinal(row) -> int:
    """Devolve ``1`` no primeiro disparo causal, ou ``0`` caso contrário."""
    if not isinstance(row, dict):
        return 0
    barras = _barras(row)
    if barras is None:
        return 0

    atual = barras[-1]
    anteriores = barras[:-1]
    sinal_atual = _sinal_bruto(atual, anteriores)
    if sinal_atual == 0:
        return 0

    # A fonte limpa _last_direction em qualquer candle sem sinal. Como esta
    # hipótese só emite BUY, comparar com o candle anterior reproduz essa
    # supressão sem estado global; com apenas 21 barras o anterior ainda não
    # tinha 20 precedentes e, portanto, não poderia ter emitido BUY.
    if len(barras) >= JANELA + 2:
        sinal_anterior = _sinal_bruto(barras[-2], barras[:-2])
        if sinal_anterior == sinal_atual:
            return 0
    return sinal_atual


__all__ = ["gerar_sinal"]
