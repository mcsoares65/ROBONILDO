# Método Just — regras extraídas e limites da adaptação V466

## O que a entrevista afirma objetivamente

- A lógica é regressão à média depois de um deslocamento até uma região de
  exaustão, operando contra o movimento que chegou à faixa.
- Para o dólar, a referência principal é 1%. Para o índice, Paulinho diz que
  as variações começam em 0,60%; o Robonildo opera WIN, portanto usa 0,60%.
- Uma referência é o fechamento da sessão anterior.
- Outra referência é a origem do movimento, exemplificada pelas extremidades
  intradiárias.
- O contexto favorece venda acima da referência e compra abaixo dela.
- A proteção do método é percentual: 0,20% de stop e 0,40% de objetivo (2R).
- Movimentos acima de 2% no dólar são tratados como anormais e podem justificar
  não operar; a entrevista não fornece o equivalente objetivo para o índice.

## Tradução para o contrato do Robonildo

O vídeo mostra tanto ordens limite previamente apregoadas quanto entradas após
um validador visual. O motor do Robonildo toma a decisão depois do fechamento
de cada candle de 15 minutos. Por isso, a versão testável adota o validador:

1. o candle atual ou o imediatamente anterior alcança a faixa;
2. o candle atual fecha novamente para dentro da faixa;
3. o candle atual fecha em baixa para VENDA ou em alta para COMPRA.

Isso evita usar a máxima/mínima intrabar como se fosse o preço de execução.
Não é alegada identidade com a execução discricionária demonstrada no vídeo.

## Cartuchos candidatos

| Cartucho | Papel | Regra |
|---|---|---|
| `entrada_paulinho_just_fechamento_V01.py` | entrada | rejeição em ±0,60% do fechamento anterior |
| `entrada_paulinho_just_origem_V01.py` | entrada | rejeição em ±0,60% da origem intradiária |
| `saida_paulinho_just_rr2_V01.py` | saída | stop 0,20%; alvo 0,40%; sem gestão posterior |

## O que ficou deliberadamente fora

- escolha visual/discricionária da origem;
- faixas adicionais e ajustes progressivos não quantificados para o índice;
- ordens limite executadas dentro do candle;
- parciais e tentativa de carregar o restante da posição;
- filtros subjetivos de exaustão, notícias ou “mercado cansado”;
- aumento de mão, preço médio ou recuperação de perdas.

Esses elementos só devem virar código quando houver uma regra numérica e dados
capazes de reproduzi-la igualmente no `principal.py` e no `classificacao.py`.
