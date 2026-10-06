"""Entrada Saída de Extremo — v02 (v01 + dois vetos).

Autoria: a regra-base é a v01 (extração da Porta 3 do grok_3, escrita por Claude
em sessão operada por Marcio Soares). Os dois vetos e seus limiares vêm do arquivo
`entrada_regime_04_v6.py`, enviado pelo dono do laboratório (autoria original dos
vetos: não informada). Esta versão apenas os isola numa estratégia de ideia única,
sem as portas 1 e 2 (que repetiam o grok_3) e sem alterar nenhum limiar. Revisão
humana antes do teste oficial: pendente. O `v02` é a versão da estratégia, não a
VERSAO do projeto.

Ideia: a v01 entra a favor da tendência quando o estocástico sai da zona extrema
(cruza 20 para cima na alta, 80 para baixo na baixa) num candle sem exaustão de
corpo. A v02 recusa a entrada em dois contextos (cada veto é uma confirmação E
sobre o mesmo sinal, não uma ideia alternativa):
  V5: cruzamento fraco E tendência das médias fraca
      (|estocástico - estocástico anterior| <= 6,31 e |MA21 - MA50| / ATR <= 0,40);
  V6: cruzamento raso E mercado já expandido
      (quanto o estocástico anterior penetrou na zona extrema <= 4,322 e o range
      dos 5 candles anteriores / ATR >= 2,66).

Limiares copiados do arquivo de origem, sem alteração. Segundo esse arquivo, foram
escolhidos olhando a primeira metade de 82 operações da porta e conferidos na segunda;
o período dessas operações não foi informado.

Variações testadas antes desta versão (Regra 11.2): 4 sobre a porta isolada, todas
no mesmo rodízio de 2020-2026 (v01; v01+V5; v01+V6; v01+V5+V6), mais o arquivo
original completo (agregador com vetos). Nenhum limiar foi ajustado.
Medição (saída titular saida_protecao_encerramento_v02, preços reescalados à volatilidade de 2026,
custo R$ 0,50 por operação, sem slippage; acumulado = resultado - |drawdown|):
                         2026    2020-25 resultado    2020-25 acumulado (soma de 6 anos)
  v01                    4.167        1.947                 -7.595
  v02 (V5+V6)            4.812          445                 -7.603
Leitura honesta: em 2026 melhora um pouco (12 operações vetadas); de 2020 a 2025 os
vetos cortam operações que em média davam lucro e o resultado cai, com o acumulado
igual. É candidata de laboratório para o teste oficial; não há base para promover.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3): as constantes abaixo são cópias.
"""

CORPO_MAXIMO_PROPORCAO = 0.70

# Vetos (limiares do arquivo de origem)
V5_VARIACAO_ESTOCASTICO_MAXIMA = 6.31
V5_SEPARACAO_MEDIAS_ATR_MAXIMA = 0.40
V6_PROFUNDIDADE_EXTREMO_MAXIMA = 4.322
V6_RANGE_5_CANDLES_ATR_MINIMO = 2.66
V6_CANDLES_ANTERIORES = 5


def _numero(valor, padrao=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _candles_anteriores(row):
    candles = list(row.get("ohlc_recentes") or ())
    if candles and candles[-1].get("dt") == row.get("dt"):
        candles = candles[:-1]
    return candles[-V6_CANDLES_ANTERIORES:]


def _veto_v5(row, atr):
    variacao = abs(_numero(row.get("stoch")) - _numero(row.get("stoch_prev")))
    separacao_atr = abs(_numero(row.get("MA21")) - _numero(row.get("MA50"))) / atr
    return (variacao <= V5_VARIACAO_ESTOCASTICO_MAXIMA
            and separacao_atr <= V5_SEPARACAO_MEDIAS_ATR_MAXIMA)


def _veto_v6(row, atr, sinal):
    anterior = _numero(row.get("stoch_prev"))
    profundidade = max(0.0, 20.0 - anterior) if sinal == 1 else max(0.0, anterior - 80.0)
    candles = _candles_anteriores(row)
    if len(candles) < 3:
        return False
    maxima = max(_numero(c.get("Maximo")) for c in candles)
    minima = min(_numero(c.get("Minimo")) for c in candles)
    return (profundidade <= V6_PROFUNDIDADE_EXTREMO_MAXIMA
            and (maxima - minima) / atr >= V6_RANGE_5_CANDLES_ATR_MINIMO)


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    hora = row["dt"].strftime("%H:%M")
    amplitude = row["Maximo"] - row["Minimo"]
    corpo = abs(row["Fechamento"] - row["Abertura"])
    if "12:30" <= hora <= "13:15" or (279.0 <= amplitude <= 360.0):
        return 0
    cruzamento_extremo = (row["stoch_cross_up_20"] if tendencia == 1
                          else row["stoch_cross_down_80"] if tendencia == -1 else False)
    if not (amplitude > 0
            and corpo <= CORPO_MAXIMO_PROPORCAO * amplitude
            and cruzamento_extremo):
        return 0
    sinal = 1 if tendencia == 1 else -1

    atr = _numero(row.get("atr"))
    if atr <= 0:
        return sinal  # sem ATR válido não há como medir os vetos: mantém o sinal da v01
    if _veto_v5(row, atr) or _veto_v6(row, atr, sinal):
        return 0
    return sinal
