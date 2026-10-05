"""Entrada Aroon(25) tendência forte — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares, 05/10/2026;
revisão humana/conselho antes do teste oficial: pendente (Regra 12). A numeração
v1 é a contagem própria do autor, não a VERSAO do projeto.

Origem: artigo "Aroon" da Central de Ajuda da Nelogica (indicadores do Profit
Pro), parâmetros PADRÃO do artigo/da literatura, fixados antes de qualquer teste.
Variações testadas antes desta versão (Regra 11.2): esta é 1 de 13 hipóteses de
indicadores testadas na mesma sessão, cada uma UMA vez, sem ajuste de limiar
(Didi, ADX, Donchian, CCI, Keltner, HiLo, SAR, Aroon, Bollinger, CMF, MFI, Force
Index, VWAP). Em desenvolvimento rodou-se com a saída titular saida_chatgpt_v4.
Sem dependência de data, evento ou preço absoluto (Regra 11.3): só comparações
relativas dentro da janela de candles.
Resultado medido (7 anos, preços reescalados, 1 contrato, saída v4): ver
conselho/2026-10-05-AD.txt. Evidência fraca; é CANDIDATA, não titular.

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas row["ohlc_recentes"], não
realiza I/O, não mantém estado e não importa módulos do projeto (Regra 3).

Aroon Up = 100 x (posição da última máxima mais alta nas 26 barras) / 25; Aroon
Down análogo com a mínima. Compra no candle em que passa a valer Up > 70 e
Down < 30 (tendência forte de alta, faixas do artigo) e no anterior não valia;
vende na situação inversa. Precisa de 27 candles em ohlc_recentes.
"""

N = 25


def _forte(janela):
    """janela: N+1 candles. Devolve +1 (alta forte), -1 (baixa forte) ou 0."""
    altas = [float(c["Maximo"]) for c in janela]
    baixas = [float(c["Minimo"]) for c in janela]
    ia = len(altas) - 1 - altas[::-1].index(max(altas))
    ib = len(baixas) - 1 - baixas[::-1].index(min(baixas))
    up, down = 100.0 * ia / N, 100.0 * ib / N
    if up > 70.0 and down < 30.0:
        return 1
    if down > 70.0 and up < 30.0:
        return -1
    return 0


def gerar_sinal(row) -> int:
    j = row.get("ohlc_recentes") or ()
    if len(j) < N + 2:
        return 0
    atual = _forte(j[-(N + 1):])
    anterior = _forte(j[-(N + 2):-1])
    if atual != 0 and atual != anterior:
        return atual
    return 0
