# Contrato de cartuchos — motor V508 e extensão WAD proposta

Fonte de execução: `motor.py`; regras de submissão: `compliance.md`. Este documento
registra os campos públicos do `row` no commit da proposta. A menção histórica a
12 candles no `compliance.md` descreve a V444; desde a V466, **a implementação
vigente oferece até 96 candles fechados**, inclusive no replay da classificação.

## Entrada

```python
def gerar_sinal(row: dict) -> int:
    """Retorna 1 (compra), -1 (venda) ou 0 (sem sinal)."""
```

| Campo de `row` | Significado |
|---|---|
| `dt` | Horário do candle fechado corrente. |
| `Abertura`, `Maximo`, `Minimo`, `Fechamento` | OHLC do candle corrente. |
| `MA21`, `MA50` | Médias simples dos últimos 21 e 50 fechamentos. |
| `trend` | Sinal da diferença MA21 − MA50: 1, 0 ou -1. |
| `distancia_ma21`, `toque_ma21` | Distância em pontos ao preço e sinal de proximidade. |
| `stoch`, `stoch_prev`, `stoch_subindo`, `stoch_descendo`, `stoch_cross_up_20`, `stoch_cross_down_80` | Estocástico lento e comparações. |
| `macd`, `macd_signal`, `macd_cross_up`, `macd_cross_down` | Linhas e cruzamentos MACD. |
| `atr`, `atr_media50`, `atr_relativo` | Volatilidade e razão de regime. |
| `rsi`, `rsi_prev`, `rsi_subindo`, `rsi_descendo` | RSI Wilder e direções. |
| `ohlc_recentes` | Tupla dos até 96 candles fechados, do mais antigo ao atual, cada um com `dt`, `Abertura`, `Maximo`, `Minimo`, `Fechamento`. |
| `gabriel_barras` | Janela paralela isolada com os campos anteriores e `Quantidade`; `None` quando não observada. Não presumir que exista volume vivo por candle. |
| **`wad_preco_recentes`** | **Novo nesta proposta**: tupla de floats alinhada, posição por posição, a `ohlc_recentes`. Williams A/D **sem volume**, com zero arbitrário no primeiro candle; apenas diferenças dentro da janela têm sentido. |

O motor calcula `wad_preco_recentes` assim, para cada candle **fechado** após o
primeiro: `TRH=max(Maximo, Fechamento_anterior)` e
`TRL=min(Minimo, Fechamento_anterior)`. Se o fechamento subiu, soma
`Fechamento−TRL`; se caiu, soma `Fechamento−TRH`; se ficou igual, soma zero.
Não há acesso a negócio, agressão, livro ou fluxo real de ordens. Esta é a
variante sem volume documentada por
[TC2000](https://help.tc2000.com/m/69445/l/755887-williams-accumulation-distribution)
e [cTrader](https://help.ctrader.com/indicators/built-in/other/williams-accumulation-distribution/).
A seção “Acumulação/Distribuição Williams” do PDF da Nelogica fornecido pelo
usuário (pp. 6–10) descreve divergências mas não especifica a equação.
**Não confundir** com uma variante que multiplica pelo volume.

## Saída

```python
def avaliar_saida(row: dict, posicao: dict) -> bool | dict:
    """Define stop/alvo no instante da abertura e pode reconfigurá-los depois."""
```

Campos de `posicao` públicos: `lado`, `entrada`, `candles_decorridos`,
`maxima_desde_entrada`, `minima_desde_entrada` e
`resultado_flutuante_pts`. O cartucho não recebe `stop` e `alvo` em
`posicao`; o motor os mantém internamente. A resposta em dicionário pode
conter `fechar`, `novo_stop` e `novo_alvo`.

## Restrição de cartucho

Cartuchos não importam código do projeto, não realizam I/O, não acumulam
estado próprio e não acessam CSV; podem usar apenas os campos públicos de
`row`/`posicao` e constantes explícitas. A saída titular atual permanece
`estrategia/saida/titular/saida_baseline.py`. A nova entrada WAD é **candidata
isolada**, não participa automaticamente da escalação titular.
