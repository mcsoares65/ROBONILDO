"""Candidata independente de entrada: Gabriel ``inside_long_v2`` — compra.

Autoria: Gabriel, do ZIP original; adaptação Manus para o contrato V465.
Variações testadas: 0. Revisão humana pendente. Esta é uma candidata, não
uma titular, e não declara validação, rentabilidade ou execução em histórico.
A numeração ``v2`` é a da hipótese de Gabriel, não a VERSAO do projeto.

A fonte ``inside_long_v2.py`` mantinha uma fila e usava ``Bar.volume``. A
adaptação reconstrói causalmente o estado necessário apenas de
``row["gabriel_barras"]``: os 20 candles anteriores sustentam a decisão atual
e o candle anterior é reavaliado para reproduzir a supressão de direção
consecutiva sem estado global. Assume-se que ``Quantidade`` é a quantidade
por candle na mesma unidade semântica de ``Bar.volume``; essa equivalência e
sua paridade live/replay ainda não foram confirmadas. Quantidade ausente ou
inválida, quando necessária, não é substituída por zero: a função fecha com
sinal 0. Quantidade zero presente é preservada, seguindo a fonte (média zero
produz relação de volume 1).

A regra original de stop/alvo na abertura é exatamente a proteção já existente
em ``saida_daytrader_rr2_v1``: piso de 20 pontos, 1,25 vezes a amplitude média
dos 20 candles anteriores e alvo de 2R com piso stop+5. Por ser tecnicamente
a mesma saída, nenhum arquivo de saída Gabriel é criado; não se duplica
``saida_daytrader_rr2_v1``.

O arquivo não faz I/O, rede ou acesso a histórico, não importa módulos do
projeto e não envia ordens. Revisão humana integral continua pendente antes
de qualquer classificação oficial.
"""

from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")
JANELA = 20
RAZAO_COMPRESSAO = Decimal("0.85")
RAZAO_EXPANSAO = Decimal("1.15")
RAZAO_VOLUME = Decimal("1.10")


def _decimal(valor):
    """Converte um valor finito; ausência não vira zero."""
    if valor is None:
        return None
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return numero if numero.is_finite() else None


def _barra(bruta):
    """Normaliza OHLC e Quantidade mantendo ausência de volume explícita."""
    if not isinstance(bruta, dict):
        return None
    abertura = _decimal(bruta.get("Abertura"))
    maxima = _decimal(bruta.get("Maximo"))
    minima = _decimal(bruta.get("Minimo"))
    fechamento = _decimal(bruta.get("Fechamento"))
    quantidade = _decimal(bruta.get("Quantidade"))
    if None in (abertura, maxima, minima, fechamento, quantidade):
        return None
    if quantidade < ZERO:
        return None
    return {
        "open": abertura,
        "high": maxima,
        "low": minima,
        "close": fechamento,
        "volume": quantidade,
    }


def _barras(row):
    """Lê somente a janela pública de Gabriel e não fabrica candles."""
    if not isinstance(row, dict):
        return None
    historico = row.get("gabriel_barras") or ()
    if len(historico) < JANELA + 1:
        return None

    # A janela pública admite até 96 candles. Para a hipótese, os 22 finais
    # bastam: 20 precedentes para o sinal e mais um precedente para a
    # reconstrução causal de _last_direction.
    normalizadas = [_barra(bruta) for bruta in historico[-(JANELA + 2):]]
    if any(barra is None for barra in normalizadas):
        return None
    return normalizadas


def _sinal_bruto(atual, anteriores):
    """Replica ``_signal`` da fonte, sem a supressão stateful."""
    if len(anteriores) < JANELA:
        return 0

    recentes20 = anteriores[-JANELA:]
    volumes = [barra["volume"] for barra in recentes20]
    # _barra já garante quantidade presente para todas as barras, mas a
    # checagem explicita preserva o contrato caso esta função seja reutilizada.
    if atual["volume"] is None or any(volume is None for volume in volumes):
        return 0

    media_amplitude = (
        sum((barra["high"] - barra["low"] for barra in recentes20), ZERO)
        / Decimal(JANELA)
    )
    media_volume = sum(volumes, ZERO) / Decimal(JANELA)
    relacao_volume = (
        atual["volume"] / media_volume if media_volume > ZERO else Decimal("1")
    )
    amplitude_atual = atual["high"] - atual["low"]

    # regime_filter = "expansion" na fonte: expansão é uma disjunção de
    # amplitude ou volume, antes das condições específicas do inside bar.
    eh_expansao = (
        amplitude_atual >= media_amplitude * RAZAO_EXPANSAO
        or relacao_volume >= RAZAO_VOLUME
    )
    if not eh_expansao:
        return 0

    mother = anteriores[-1]
    anterior_mae = anteriores[-2]
    inside = (
        mother["high"] <= anterior_mae["high"]
        and mother["low"] >= anterior_mae["low"]
    )
    amplitude_mae = mother["high"] - mother["low"]
    comprimida = amplitude_mae <= media_amplitude * RAZAO_COMPRESSAO

    if (
        inside
        and comprimida
        and amplitude_atual >= media_amplitude * RAZAO_EXPANSAO
        and relacao_volume >= RAZAO_VOLUME
        and atual["close"] > mother["high"]
        and atual["close"] > atual["open"]
    ):
        return 1
    return 0


def gerar_sinal(row) -> int:
    """Retorna 1 no primeiro disparo causal da hipótese; caso contrário 0."""
    barras = _barras(row)
    if barras is None:
        return 0

    atual = barras[-1]
    anteriores = barras[:-1]
    sinal_atual = _sinal_bruto(atual, anteriores)
    if sinal_atual == 0:
        return 0

    # A fonte zera _last_direction sempre que o candle não sinaliza. Como a
    # hipótese só compra, o candle imediatamente anterior é suficiente para
    # reconstituir a memória, sem conservar estado entre chamadas.
    if len(barras) >= JANELA + 2:
        sinal_anterior = _sinal_bruto(barras[-2], barras[:-2])
        if sinal_anterior == sinal_atual:
            return 0
    return sinal_atual


__all__ = ["gerar_sinal"]
