"""Entrada CCI(20) cruza ±100 — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares, 05/10/2026;
revisão humana/conselho antes do teste oficial: pendente (Regra 12). A numeração
v1 é a contagem própria do autor, não a VERSAO do projeto.

Origem: artigo "CCI" da Central de Ajuda da Nelogica (indicadores do Profit
Pro), parâmetros PADRÃO do artigo/da literatura, fixados antes de qualquer teste.
Variações testadas antes desta versão (Regra 11.2): esta é 1 de 13 hipóteses de
indicadores testadas na mesma sessão, cada uma UMA vez, sem ajuste de limiar
(Didi, ADX, Donchian, CCI, Keltner, HiLo, SAR, Aroon, Bollinger, CMF, MFI, Force
Index, VWAP). Em desenvolvimento rodou-se com a saída titular saida_protecao_encerramento_v02.
Sem dependência de data, evento ou preço absoluto (Regra 11.3): só comparações
relativas dentro da janela de candles.
Resultado medido (7 anos, preços reescalados, 1 contrato, saída v4): ver
conselho/2026-10-05-AD.txt. Evidência fraca; é CANDIDATA, não titular.

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas row["ohlc_recentes"], não
realiza I/O, não mantém estado e não importa módulos do projeto (Regra 3).

CCI = (PT - SMA20(PT)) / (0,015 x desvio médio absoluto), PT = (H+L+C)/3.
Compra quando o CCI cruza +100 para cima; vende quando cruza -100 para baixo
(uso de continuação de tendência, como descrito no artigo).
"""

N = 20


def _cci(janela):
    pt = [(float(c["Maximo"]) + float(c["Minimo"]) + float(c["Fechamento"])) / 3.0 for c in janela]
    media = sum(pt) / N
    dm = sum(abs(x - media) for x in pt) / N
    if dm == 0:
        return None
    return (pt[-1] - media) / (0.015 * dm)


def gerar_sinal(row) -> int:
    j = row.get("ohlc_recentes") or ()
    if len(j) < N + 1:
        return 0
    atual = _cci(j[-N:])
    anterior = _cci(j[-N - 1:-1])
    if atual is None or anterior is None:
        return 0
    if anterior <= 100.0 and atual > 100.0:
        return 1
    if anterior >= -100.0 and atual < -100.0:
        return -1
    return 0
