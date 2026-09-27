"""
laboratorio_estrategias/estrategias/_template.py

MODELO para uma estrategia nova. Copie este arquivo como
estrategias/nome_da_estrategia.py e escreva sua logica dentro de
gerar_sinal(row).

O nome comecando com "_" faz o rodar_ranking.py e o classificacao.py
IGNORAREM este arquivo na descoberta automatica - ele nao entra no
ranking. Ao copiar, tire o "_" do nome do arquivo novo.

IMPORTANTE: nao tente adivinhar nomes de coluna (nao existe "high",
"maxima" com acento, etc.) - os nomes abaixo sao EXATOS, definidos em
rodar_ranking.py/classificacao.py (leitura do CSV) e indicadores.py
(calculo dos indicadores). Use exatamente como esta escrito aqui.

Colunas de preco (vem direto do CSV exportado do Profit):
    row['Abertura']    - float
    row['Maximo']      - float  (sem acento, termina em "o")
    row['Minimo']      - float  (sem acento, termina em "o")
    row['Fechamento']  - float
    row['Volume']      - string (nao convertido)
    row['dt']          - pandas.Timestamp (data + hora do candle)
    row['date']        - datetime.date (so a data, usado pro limite diario)

Indicadores ja calculados (vem de indicadores.py - nao recalcule):
    row['MA21']                - float, media movel de 21 periodos do Fechamento
    row['MA50']                - float, media movel de 50 periodos do Fechamento
    row['trend']                - int: 1 (MA21>MA50), -1 (MA21<MA50), 0 (igual)
    row['distancia_ma21']       - float, |Fechamento - MA21|
    row['toque_ma21']           - bool, distancia_ma21 <= 40 e trend != 0
    row['stoch']                - float, estocastico lento 8/3 (EMA)
    row['stoch_prev']           - float, stoch do candle anterior
    row['stoch_subindo']        - bool, stoch > stoch_prev
    row['stoch_descendo']       - bool, stoch < stoch_prev
    row['stoch_cross_up_20']    - bool, cruzou de <=20 pra >20 neste candle
    row['stoch_cross_down_80']  - bool, cruzou de >=80 pra <80 neste candle
    row['macd']                 - float, linha MACD (12,26)
    row['macd_signal']          - float, linha de sinal (EMA 9 do macd)
    row['macd_cross_up']        - bool, macd cruzou o sinal pra cima neste candle
    row['macd_cross_down']      - bool, macd cruzou o sinal pra baixo neste candle

Se sua ideia precisar de um indicador que nao esta nessa lista, adicione
o calculo em indicadores.py (uma vez so, reaproveitado por todas as
estrategias) - nao calcule dentro da propria estrategia.

Contrato:
    gerar_sinal(row) -> 1 (compra), -1 (venda) ou 0 (sem operacao)

O motor_backtest.py cuida de tudo mais: stop estrutural, alvo 2R, limite
diario de operacoes/perdas, bloqueio de horario e custo por operacao. A
estrategia SO decide a direcao do sinal, nada de gestao aqui dentro.
"""


def gerar_sinal(row) -> int:
    # Exemplo minimo (substitua pela sua logica):
    if not row['toque_ma21']:
        return 0
    if row['trend'] == 1 and row['stoch_subindo']:
        return 1
    if row['trend'] == -1 and row['stoch_descendo']:
        return -1
    return 0
