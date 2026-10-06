"""Entrada Keltner Channels rompimento — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares, 05/10/2026;
revisão humana/conselho antes do teste oficial: pendente (Regra 12). A numeração
v1 é a contagem própria do autor, não a VERSAO do projeto.

Origem: artigo "Keltner Channels" da Central de Ajuda da Nelogica (indicadores do Profit
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

Linha central = média simples de 20 candles do preço típico (H+L+C)/3; bandas =
central ± 1 x média simples de 20 candles da amplitude (H-L), como no artigo.
Compra quando o fechamento rompe a banda superior (estava na ou abaixo dela no
candle anterior); vende no rompimento da inferior.
"""

N = 20


def _banda(janela):
    tp = sum((float(c["Maximo"]) + float(c["Minimo"]) + float(c["Fechamento"])) / 3.0 for c in janela) / N
    amp = sum(float(c["Maximo"]) - float(c["Minimo"]) for c in janela) / N
    return tp + amp, tp - amp


def gerar_sinal(row) -> int:
    j = row.get("ohlc_recentes") or ()
    if len(j) < N + 1:
        return 0
    sup, inf = _banda(j[-N:])
    sup_ant, inf_ant = _banda(j[-N - 1:-1])
    c = float(j[-1]["Fechamento"])
    c_ant = float(j[-2]["Fechamento"])
    if c_ant <= sup_ant and c > sup:
        return 1
    if c_ant >= inf_ant and c < inf:
        return -1
    return 0
