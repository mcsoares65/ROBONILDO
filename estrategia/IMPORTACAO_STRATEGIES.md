# Triagem do pacote `strategies.zip` — V465

Origem analisada: `strategies.zip`, 41 itens e 24 estratégias registradas.
SHA-256: `f34bedd67900c6af7f73f3f14798731300990f4ec7a477ba1a151d6bf20a619c`.

O pacote usa outro contrato: cada classe mantém uma fila de objetos `Bar` e
devolve um `OrderIntent` que mistura entrada, stop e alvo. No Robonildo, esses
papéis foram separados em `gerar_sinal(row)` e `avaliar_saida(row, posicao)`.

## Convertidas em entradas candidatas

| Estratégia recebida | Cartucho Robonildo |
|---|---|
| `channel_reversion_long` | `entrada_daytrader_channel_reversion_long_v1.py` |
| `channel_reversion_short` | `entrada_daytrader_channel_reversion_short_v1.py` |
| `channel_long_v2` | `entrada_daytrader_channel_long_v2.py` |
| `channel_short_v2` | `entrada_daytrader_channel_short_v2.py` |
| `ema_pullback_long` | `entrada_daytrader_ema_pullback_long_v1.py` |
| `failed_break_long` | `entrada_daytrader_failed_break_long_v1.py` |
| `failed_break_short` | `entrada_daytrader_failed_break_short_v1.py` |
| `failed_break_long_v2` | `entrada_daytrader_failed_break_long_v2.py` |
| `failed_break_short_v2` | `entrada_daytrader_failed_break_short_v2.py` |

As nove regras usam somente OHLC e puderam ser reproduzidas sem estado global.
A janela do motor passou de 12 para 22 candles fechados: 20 para o cálculo,
um candle atual e um para reproduzir a supressão de sinais consecutivos do
framework original. A conversão foi comparada candle a candle em 9.394 candles
reais: zero divergências nas nove estratégias.

## Convertida em saída candidata

Todas as nove entradas acima continham a mesma proteção. Ela foi retirada das
entradas e centralizada em `saida_daytrader_rr2_v1.py`:

- amplitude média dos 20 candles anteriores;
- stop = maior entre 20 pontos e 1,25 vez a amplitude média;
- alvo = maior entre stop + 5 pontos e 2 vezes o stop;
- nenhuma saída antecipada adicional.

Assim o laboratório pode cruzar livremente qualquer uma das nove entradas com
as saídas existentes, ou qualquer entrada existente com essa nova saída.

## Não ativadas: volume ausente no contrato oficial

As 14 estratégias abaixo dependem de volume. O CSV exportado pode conter esse
campo, mas o `Candle`, o `motor.py` e o DDE operacional ainda não o entregam ao
mesmo contrato de decisão. Ativá-las apenas no laboratório quebraria a paridade
com o mercado ao vivo.

`ema_pullback_short`, `donchian_long`, `inside_bar_long`,
`dual_momentum_long`, `pullback_long_v2`, `pullback_short_v2`,
`breakout_long_v2`, `inside_long_v2`, `dual_momentum_long_v2`,
`structure_retest_long_v2`, `hybrid_consensus_long_v2`, `trend_pullback_v3`,
`momentum_expansion_v3` e `compression_breakout_v3`.

Para liberá-las, primeiro é necessário validar a coleta de volume no DDE e no
CSV, adicionar o campo ao `Candle`/`row` do console único e comprovar paridade
replay × normal.

## Não ativada: ciclo de vida com estado

`smc_structure_retest_v3` é uma máquina de estados com aquecimento, sweep,
BOS/FVG, reteste e prazo de validade entre candles. O contrato atual não possui
`reset()` por pregão nem instância isolada por execução. Transformá-la em estado
global faria classificações repetidas e reinícios produzirem respostas
diferentes. Ela só deve ser adaptada depois de existir um contrato oficial de
ciclo de vida para cartuchos stateful.

## Arquivos que não são cartuchos

`capital_risk_adjusted.py` e `regime_filtered.py` são decoradores; `reference.py`
é uma referência; `base.py`, `registry.py`, `gen3/core.py` e `__init__.py` são
infraestrutura do framework externo. Eles não foram colocados nas pastas ativas.

Nenhuma estratégia foi promovida a titular nesta importação. Resultado
histórico não garante desempenho futuro; as candidatas ainda precisam passar
pelos rankings de entrada, saída e cruzado do `classificacao.py`.
