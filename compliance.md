# Regras do Jogo — Laboratório de Estratégias ROBONILDO

**Versão 8 (PROPOSTA — pendente de ratificação pelo conselho)**

> O objetivo principal do projeto é o foco no resultado financeiro, a busca constante pela melhoria dos resultados é nossa unico objetivo.
> Este documento simplifica o critério de vitória conforme decisão do dono
> do laboratório. A Pontuação Composta, o fator de presença e o multi deixam
> de ordenar os rankings. Entradas, saídas e combinações cruzadas passam a
> obedecer ao mesmo valor monetário ajustado ao risco: `acumulado`.

Antes de escrever ou submeter qualquer arquivo em `estrategia/`, todo
participante — humano, colega, ou IA (ChatGPT, Claude, Manus, Gemini,
Grok, DeepSeek, ou qualquer outra) — concorda com as regras abaixo. São as
mesmas cartas pra todo mundo: ninguém joga com regra diferente, ninguém
decide sozinho que uma regra não se aplica a ele.

Se um participante (inclusive uma IA agindo em nome de alguém) não puder
concordar com algum item abaixo, ele não deve gerar ou submeter código pra
este laboratório.

---

## Objetivo do laboratório

**O objetivo de cada participante é maximizar dinheiro líquido preservando
capital. O critério oficial é o Acumulado definido na Regra 5.**

Isso significa, na prática:
- Uma estratégia vence quando apresenta maior Acumulado em reais.
- O critério de vitória é único e público (a fórmula da Regra 5) — não há
  "vitória" por outro caminho, nem posição especial pra quem discordar do
  critério (discordância se resolve pedindo mudança formal do critério,
  não ignorando ele numa submissão).
- "Melhor" nunca é decidido só pelo autor da estratégia (humano ou IA) —
  é decidido rodando o motor oficial e lendo o resultado de
  `classificacao.py`.

---

## 1. O contrato: `gerar_sinal(row) -> int` / `avaliar_saida(row, posicao) -> bool | dict`

- Entrada: recebe **uma única linha** (`row`) e devolve **um único
  inteiro**: `1` (compra), `-1` (venda) ou `0` (nada). Nada além disso.
- Saída: recebe `row` e `posicao` e devolve, em uma das duas formas:
  - **booleano simples** (compatibilidade retroativa): `True` fecha agora,
    `False` mantém a posição como está.
  - **ou um dicionário**: `{"fechar": bool, "novo_stop": float | None,
    "novo_alvo": float | None}` — o cartucho de saída define e/ou
    redefine **livremente** o stop e/ou o alvo da posição, em qualquer
    direção, junto com (ou em vez de) pedir fechamento imediato.
- **O motor não tem fórmula própria de saída.** Ele não calcula stop nem
  alvo em nenhum momento — nem como piso de segurança, nem como "ponto de
  partida" da posição. Quem define esses valores, desde o primeiro
  instante em que a posição abre, é exclusivamente o arquivo de saída
  titular (`estrategia/saida/titular/`).
- **O motor consulta o cartucho de saída titular já na abertura da
  posição** (além de consultar a cada candle fechado, como sempre). Se o
  cartucho não devolver um dicionário com `novo_stop`/`novo_alvo` nesse
  momento (por exemplo, um cartucho antigo que só devolve `bool`), a
  posição nasce **sem nenhum stop nem alvo** — permanece assim até o
  cartucho definir algo num candle seguinte ou, se nunca definir, só fecha
  por pedido explícito do cartucho (`fechar=True`) ou pelo corte de
  horário do pregão. Isso é o comportamento correto e esperado, não uma
  falha: a responsabilidade é inteira do cartucho.
- **O motor não valida nem limita a reconfiguração proposta**, em nenhuma
  direção: não há garantia de "só aperta, nunca afrouxa". O cartucho de
  saída tem autoridade total sobre o próprio risco da operação, do
  primeiro instante ao último. Um cartucho mal desenhado ou com bug pode
  deixar a operação sem proteção nenhuma, por tempo indefinido — risco
  assumido conscientemente pelo dono do laboratório, não uma omissão.
- `posicao` continua **sem expor** `stop`/`alvo` ao cartucho de saída
  (preserva a decisão do DeepSeek contra acoplamento oculto, rodada 3) —
  o cartucho decide com base no que já recebia hoje (`lado`, `entrada`,
  `candles_decorridos`, `maxima_desde_entrada`, `minima_desde_entrada`,
  `resultado_flutuante_pts`), mais `row["ohlc_recentes"]` (últimos 12
  candles fechados, desde a V444) para quem precisar calcular um nível
  estrutural próprio.
- Limite diário, bloqueio de horário e corte de horário do pregão
  continuam sendo do `motor.py` — não fazem parte da decisão de stop/alvo
  e não são afetados por esta mudança. Não são "regra de saída" no
  sentido em que esta regra usa o termo: são mecanismos
  operacionais/regulatórios de fechamento de pregão, não uma escolha de
  estratégia.

## 2. Use os nomes de coluna exatos — não adivinhe

- A lista completa e oficial de campos disponíveis em `row` (e em
  `posicao`, do lado da saída) é a documentada no template oficial de
  cartucho do projeto. É a única fonte confiável.
- Não é permitido inventar nome de coluna, tentar variações "prováveis"
  nem criar indicador novo dentro do próprio arquivo da estratégia.
- Se sua ideia precisa de um indicador que não existe ainda, ele entra no
  motor — uma vez só, documentado, reaproveitado por todos. **E, no mesmo
  commit/entrega, o template é atualizado com a nova coluna.** Indicador
  novo sem a atualização correspondente no template no mesmo envio é
  submissão incompleta, tratada como se o indicador não existisse.
- Se você (IA ou humano) está incerto se uma coluna existe, **pergunte
  antes de assumir "já deve existir"**.

## 3. Proibido qualquer I/O ou acesso fora do escopo de `row`/`posicao`

Uma estratégia não tem motivo legítimo para:

- Importar `os`, `sys`, `subprocess`, `socket`, `requests`, ou qualquer
  biblioteca de rede/processo/sistema de arquivos. Isso inclui não
  importar `configuracao.py` nem qualquer outro módulo do projeto — um
  valor que a estratégia precisa (como `SWING_LOOKBACK_CANDLES` ou
  `RELACAO_RISCO_RETORNO`) é copiado explicitamente para dentro do
  próprio arquivo, documentado como cópia, não importado.
- Usar `open()`, `eval()`, `exec()`, ou reabrir o dataset (`.csv`) por
  conta própria.
- Ler, escrever ou alterar qualquer outro arquivo do projeto — incluindo
  `motor.py`, `classificacao.py`, `configuracao.py`, ou qualquer relatório
  gerado.
- Manter estado global que acumule informação de candles além do que o
  motor já entrega linha a linha (`row["ohlc_recentes"]` cobre o caso de
  precisar enxergar candles recentes sem guardar histórico próprio).

Qualquer um desses itens presente num arquivo de estratégia é motivo
automático de rejeição, mesmo sem prova de má intenção — a regra é sobre o
que o código **pode** fazer, não sobre o que a pessoa/IA diz que ele faz.

## 4. Sem alegação de "já validado" sem prova rodada

- Comentário ou docstring não é validação. Nenhuma estratégia entra
  documentada como "testada", "estável" ou "validada" a menos que tenha
  sido **de fato rodada** no motor oficial, com resultado exportado.
- Se uma IA gerou o código, qualquer afirmação de que um filtro, horário
  ou regime "se mostrou melhor" precisa vir acompanhada do resultado real
  que comprova isso — ou ser removida do comentário antes da submissão.
- **Todo número citado como "benchmark" ou "resultado de referência" de
  outra estratégia precisa citar o dataset exato usado** (ver Regra 9) —
  um número sem essa citação não pode ser tratado como confirmado, só como
  alegação a verificar.

## 5. Critério de ranking — uma fórmula só, e ela muda por decisão explícita

- O critério proposto para substituir integralmente a Pontuação Composta é o
  **Acumulado**, calculado em `classificacao.py`:

  ```
  acumulado = resultado - abs(drawdown)
  ```

  Como o drawdown é armazenado com sinal negativo, a fórmula equivalente é
  `acumulado = resultado + drawdown`.
- O mesmo critério será aplicado aos rankings de entradas, saídas e
  combinações cruzadas.
- Maior Acumulado vence. Em caso de empate: maior resultado, menor drawdown
  absoluto e, persistindo o empate, maior quantidade de dias operados.
- **Esse critério só muda por decisão explícita do dono do laboratório**,
  comunicada a todos os participantes ao mesmo tempo.
- Profit factor, capital mínimo, presença e multi permanecem métricas de
  auditoria e robustez, mas não alteram a posição do ranking.
- Amostra pequena não é validação; o tamanho da amostra continua obrigatório
  na apresentação do resultado.

## 6. Transparência de autoria

- Todo arquivo de estratégia identifica, no docstring, se foi escrito por
  humano, gerado por IA (e qual), ou uma combinação — e por quem foi
  revisado antes de entrar no laboratório.
- Isso não é burocracia: é o que permite rastrear a origem se um problema
  aparecer depois. **Documento sem essa identificação clara é tratado como
  incompleto e devolvido ao autor antes de qualquer revisão de conteúdo** —
  já aconteceu de um documento do conselho chegar sem indicação de autoria
  e gerar atribuição errada.
- Quando o nome de um arquivo incluir um número de versão próprio do autor
  (padrão `entrada_<assinatura>_v<NN>.py` / `saida_<assinatura>_v<NN>.py`),
  o docstring deixa explícito que esse número é a contagem própria do
  autor — **não** a `VERSAO` do projeto (`versionamento.py`) e não
  necessariamente sequencial com entregas anteriores do mesmo autor. Isso
  evita confundir "v21 de uma estratégia" com "V445 do projeto".

## 7. Nomenclatura e duplicatas

- Arquivo novo: `estrategia/entrada/nome_da_estrategia.py` ou
  `estrategia/saida/nome_da_estrategia.py`, conforme o lado.
- Padrão recomendado de nome: `entrada_<assinatura>_v<NN>.py` /
  `saida_<assinatura>_v<NN>.py`, onde `<assinatura>` identifica o autor
  (ver Regra 6 sobre o que o número de versão significa nesse padrão).
- Nome de arquivo começando com `_` é reservado para arquivos internos —
  a descoberta automática ignora esses arquivos.
- **Antes de submeter, confira se o conteúdo não é idêntico (ou quase) a
  um arquivo já existente com outro nome.** Se duas estratégias no ranking
  têm `resultado`, `drawdown` e `dias` idênticos, é duplicata até prova em
  contrário.

## 8. Execução em ambiente controlado

- Todo arquivo novo — principalmente vindo de fora do círculo direto de
  confiança, ou gerado por IA sem revisão humana completa — deve ser lido
  na íntegra por um humano **antes** de ser importado e rodado.
- O dataset oficial deve permanecer com permissão de somente leitura.

## 9. O dataset usado é sempre explícito — nunca implícito

- **Todo resultado, benchmark ou comparação citado precisa vir acompanhado
  do período exato do dataset usado** (data inicial, data final, e
  idealmente contagem de candles).
- Quando o dataset for atualizado, **todos os participantes precisam ser
  avisados explicitamente**, com a nova data final — resultados antigos
  não são comparáveis a resultados novos sem essa atualização.

## 10. Teste de robustez antes de qualquer promoção fora do laboratório

- Um resultado bom em cima de limiares numéricos muito específicos e
  estreitos é candidato a *overfitting* até prova em contrário.
- Antes de tratar uma estratégia como confiável o suficiente pra ser
  promovida a titular, perturbe os limiares numéricos chave em ±10–30% e
  confira se o PF mínimo se mantém na mesma faixa. Se o resultado
  desmoronar com uma pequena mudança, é sinal de ajuste fino ao ruído do
  período testado, não um padrão real.
- Esse teste, e o resultado dele, deve constar no histórico da decisão de
  promoção — não é opcional "se der tempo".

---

## 11. Garimpagem histórica — o histórico de validação não é uma fonte de descoberta ilimitada

**O problema que esta regra resolve:** a Regra 10 já cobre limiares
*isoladamente* frágeis. Ela **não** cobre o problema maior, que é
estrutural: uma estratégia pode ter limiares individualmente "robustos"
(passam no teste de ±10–30%) e ainda assim ser fruto de **garimpagem** —
ou seja, o autor (humano ou IA) rodou dezenas de variações contra o mesmo
histórico de validação até uma combinação específica "vencer", e só essa
combinação foi reportada. Isso é conhecido em estatística como
*data-snooping* / *multiple comparisons* — quanto mais variações forem
testadas contra o mesmo dataset, maior a chance de uma delas parecer boa
só por acaso, sem que exista um padrão real repetível no futuro. Nenhum
teste de sensibilidade de limiar isolado (Regra 10) detecta esse
problema, porque ele mede a fragilidade de uma escolha, não quantas
escolhas foram tentadas antes dela.

Três frentes, todas obrigatórias a partir desta versão:

### 11.1 — Divisão em três blocos: Desenvolvimento, Validação e Holdout Cego

O histórico oficial passa a ser dividido em três blocos, comunicados e
travados publicamente antes de qualquer novo ciclo de propostas:

- **Desenvolvimento** (a maior parte do histórico): livre para qualquer
  participante rodar quantas vezes quiser, iterar, ajustar. É onde a
  criatividade acontece.
- **Validação** (o período já usado hoje em `classificacao.py` para o
  ranking oficial — ex.: o corte de `LAB_DIAS_TESTE` para Teste Curto):
  usado para o ranking competitivo entre candidatas. Continua exatamente
  como já funciona hoje.
- **Holdout Cego** (novo): um bloco final do histórico, definido pelo dono
  do laboratório, que **nenhuma IA nem humano usa para desenvolver,
  ajustar ou escolher entre variações** — nem mesmo "só para ver". Ele só
  é rodado **uma única vez**, pelo dono do laboratório, no momento em que
  uma estratégia está sendo considerada para promoção a **titular** (não
  para entrar no ranking geral — só na hora de trocar quem está em
  produção). O resultado do Holdout não é usado para ajustar a estratégia
  depois — se ela for mal no Holdout, ela não é promovida nesse ciclo, e
  qualquer nova versão criada em resposta ao resultado do Holdout precisa
  de um Holdout novo (o atual já foi "gasto", queimado, não serve mais
  como cego).
- O bloco de Holdout é definido de uma vez, documentado (datas exatas), e
  só muda quando o dataset é renovado com dados genuinamente novos
  (nunca encolhido ou trocado para "dar outra chance" a uma estratégia
  específica).

### 11.2 — Divulgação obrigatória de todas as variações testadas, não só a vencedora

- Ao propor uma estratégia, o participante (IA ou humano) declara, no
  próprio corpo da proposta, **quantas variações relevantes** dessa mesma
  ideia foram testadas antes de chegar na versão submetida (mesmo que só
  internamente, sem cada uma virar um arquivo formal) — não é preciso
  anexar cada tentativa descartada, mas **o número aproximado e a natureza
  das mudanças feitas entre elas precisa ser dito**.
- Uma estratégia apresentada como "primeira tentativa, já validada" que na
  verdade é a 30ª variação de limiares testada por uma IA na mesma sessão
  é uma submissão que viola esta regra — o conselho avalia a força da
  evidência de forma diferente para "resultado da primeira ideia" versus
  "melhor de 30 tentativas no mesmo período".
- Isso não bane iterar — itera-se à vontade **no bloco de Desenvolvimento**
  (11.1). O que é vedado é apresentar o resultado final sem contexto de
  quantas tentativas geraram aquele número específico.

### 11.3 — Proibição explícita de qualquer referência a datas, eventos ou estrutura específica do dataset

- Uma estratégia não pode conter qualquer lógica que dependa de uma data
  específica, um intervalo de datas fixo, ou qualquer valor que só faz
  sentido porque "nesse dataset, esse dia teve tal comportamento" (ex.:
  bloquear um dia específico do calendário, não um dia da semana genérico;
  usar um valor de preço absoluto do WINFUT como limiar, em vez de algo
  relativo como distância de média ou ATR).
- Filtros de dia da semana, horário do pregão ou regime de volatilidade
  relativo são aceitáveis (já existem exemplos no laboratório) — o que é
  proibido é qualquer coisa que só funcione porque "conhece" o histórico
  específico usado para testar, e não generalizaria para um histórico
  novo com a mesma estrutura de mercado.

---

## 12. Aprovação prévia do conselho via GitHub, antes do teste manual em `classificacao.py`

**O problema que esta regra resolve:** hoje, qualquer participante pode
colocar um arquivo em `estrategia/entrada/` ou `estrategia/saida/` e rodar
`classificacao.py` diretamente — o conselho só vê o resultado depois, já
pronto. Isso significa que a única revisão que uma estratégia recebe
**antes** de consumir tempo de teste é a do próprio autor. Não há hoje
nenhum portão em que outra IA (ou o dono do laboratório) confirme, antes
da rodada, que a estratégia respeita as Regras 1–11 acima.

Novo fluxo, obrigatório a partir da ratificação desta versão:

1. **Proposta (Pull Request)** — toda nova estratégia (ou alteração de uma
   já existente) é submetida como um Pull Request num repositório Git do
   projeto, nunca colocada direto na pasta `estrategia/` sem passar por
   esse fluxo. O PR inclui:
   - O arquivo `.py` da estratégia.
   - Autoria (Regra 6).
   - A declaração de variações testadas (Regra 11.2).
   - Confirmação de que nenhuma lógica depende de data/evento específico
     (Regra 11.3).
   - Se já houver algum teste preliminar rodado no bloco de
     Desenvolvimento (11.1), o resultado dele — nunca um resultado do
     bloco de Validação ou do Holdout, que só existem depois da aprovação.
2. **Revisão do conselho** — antes de qualquer teste oficial em
   `classificacao.py` contra o bloco de Validação, ao menos um outro
   participante do conselho (idealmente mais de um, quando disponíveis)
   revisa o PR e confirma, por escrito no próprio PR, que:
   - O contrato (Regra 1) está correto.
   - Não há violação de I/O ou escopo (Regra 3).
   - Não há sinal de garimpagem ou dependência de dataset específico
     (Regra 11).
   - A autoria está clara (Regra 6).
   Essa revisão é sobre **conformidade com as regras**, não sobre "se a
   estratégia é boa" — isso é decidido depois, pelo resultado real em
   `classificacao.py`. O conselho não aprova nem rejeita estratégias por
   achar que vão ganhar ou perder; aprova ou rejeita por estarem dentro ou
   fora das regras do jogo.
3. **Merge e teste oficial** — só depois do PR aprovado por ao menos um
   revisor, o dono do laboratório faz o merge (movendo o arquivo para
   `estrategia/entrada/` ou `estrategia/saida/`) e roda `classificacao.py`
   contra o bloco de Validação. O resultado entra no ranking normalmente.
4. **Promoção a titular** — segue exigindo, adicionalmente a este fluxo,
   o teste de robustez (Regra 10) e, quando for de fato uma troca de
   titular (não apenas uma posição no ranking geral), a rodada única e
   não repetível contra o Holdout Cego (Regra 11.1).

Este fluxo não substitui as Regras 1–11 — é o **portão** por onde toda
estratégia passa antes delas serem verificadas na prática pelo teste
oficial, e é o mecanismo que permite a qualquer IA nova integrar o
laboratório de forma transparente: basta ler este documento e o repositório
inteiro (histórico de PRs, revisões e decisões) já está público para
qualquer novo participante consultar antes de propor algo.

---

## 13. Fator de presença — REGRA REVOGADA PELA V7

> Todo o conteúdo histórico desta seção permanece documentado apenas para
> rastreabilidade das versões v4–v6. A partir da ratificação da v7, cobertura,
> presença, Pontuação Composta e multi **não ordenam nenhum ranking**. O
> critério único passa a ser o Acumulado da Regra 5. Nenhuma subseção abaixo
> prevalece sobre essa decisão.

**O problema que esta regra resolve:** o termo `√dias_operados` já
recompensa estratégias que operam em mais dias, mas seu efeito pode ser
insuficiente. Uma estratégia excessivamente seletiva pode evitar grande
parte das condições de mercado, apresentar drawdown reduzido e parecer
superior a concorrentes que demonstraram desempenho em uma amostra
operacional muito maior.

Intenção confirmada pelo dono do laboratório: **dias operados deve pesar
por si só na pontuação** — mais dias operados, mais resultado e menos
drawdown, juntos, é o cenário ideal. Nenhum desses três fatores deve
depender de quais outras estratégias foram testadas na mesma rodada.

### 13.1 — Cobertura absoluta, não relativa ao grupo

A versão original desta regra (v4) definia o denominador como "o maior
número de dias operados do grupo testado junto" — relativo aos
concorrentes da rodada. Isso reabria o problema que a V433
(`versionamento.py`) fechou deliberadamente para o `multi`: a mesma
estratégia, com o mesmo resultado, pontuaria diferente dependendo de quem
mais estivesse no lote. A v5 corrige isso usando um denominador **fixo
pelo dataset**, não pelos concorrentes:

```text
cobertura = dias_operados_da_estrategia / total_de_pregoes_do_periodo
```

onde `total_de_pregoes_do_periodo` é a quantidade de pregões distintos no
histórico avaliado (`len(dias)` em `classificacao.py`) — o mesmo valor
para qualquer estratégia testada nesse dataset, sozinha ou em arsenal
completo.

Depois da ratificação desta versão, a Pontuação Composta será aplicada nos
três modos de classificação. No ranking cruzado:

```text
pontuacao_base =
    (resultado / capital_minimo) × PF_minimo × √dias_operados

pontuacao_final = pontuacao_base × cobertura
```

Nos rankings de entrada e saída, a mesma cobertura incidirá sobre a nota
multitemporal:

```text
multi_base =
    média ponderada dos scores longo, mensal e diário disponíveis

multi_final = multi_base × cobertura
```

O ranking de entradas será ordenado por `multi_final`, o ranking de saídas
será ordenado por `multi_final` e o ranking cruzado será ordenado por
`pontuacao_final`. As notas-base permanecerão visíveis para auditoria.

Como `cobertura` varia de `0` a `1`, o fator não cria pontos artificiais.
Ele preserva a pontuação de quem operou todo o período disponível e
aplica uma redução proporcional a quem operou uma fração menor dele —
**sem referência a nenhuma outra estratégia**, preservando a propriedade
da V433 de que o mesmo resultado sempre produz o mesmo número.

Benefício colateral: como o denominador não depende mais de "grupos
comparáveis", a antiga necessidade de definir grupos por lado fixo
(entrada/saída) e condições idênticas deixa de ser necessária só para o
cálculo do `cobertura` — o mesmo `total_de_pregoes_do_periodo` vale para
qualquer ranking (E, S ou C) rodado sobre o mesmo histórico.

### 13.2 — Dias, não quantidade de operações

- `dias_operados` é a quantidade de datas distintas com pelo menos uma
  operação encerrada e válida.
- Duas ou mais operações na mesma data continuam contando como um único
  dia.
- O número bruto de operações não gera bônus. Isso evita incentivar giro
  excessivo, custos desnecessários ou sobreoperação.
- O fator mede presença no histórico avaliado, não agressividade
  operacional.

### 13.3 — Histórico curto ou de um único pregão

- Se o histórico tiver somente um pregão, quem operar terá cobertura de
  100%.
- Quem não operar terá cobertura de 0% e pontuação final igual a zero.
- O relatório deve advertir que um único pregão é amostra insuficiente
  para promover uma estratégia a titular, independentemente da
  pontuação.
- A regra funciona matematicamente em amostra curta, mas não transforma
  uma amostra curta em evidência de robustez.

### 13.4 — Apresentação obrigatória no ranking

Cada um dos três rankings deverá exibir, no mínimo:

```text
resultado | drawdown | capital_minimo | dias | presenca | pontuacao_base | pontuacao_final
```

Nos rankings de entrada e saída, os dois últimos campos serão apresentados
como `multi_base` e `multi_final`.

`presenca` será apresentada em percentual (`cobertura × 100`). O
cabeçalho ou rodapé do relatório deverá informar a fórmula vigente e o
número total de pregões do período usado como denominador.

### 13.5 — Salvaguardas

- Resultado negativo não pode produzir pontuação final positiva (já
  garantido matematicamente: `cobertura` nunca é negativo, então o sinal
  de `pontuacao_base` se preserva).
- Capital mínimo, profit factor ou dias inválidos devem invalidar a
  linha; o sistema não pode converter silenciosamente um valor inválido
  em vantagem.
- A pontuação não substitui a leitura separada de resultado, drawdown,
  capital mínimo, estabilidade multitemporal e teste em Holdout Cego.
- Empates técnicos serão resolvidos, nesta ordem, por maior resultado
  líquido, menor drawdown absoluto, maior presença e maior número de
  dias operados.
- Nenhuma estratégia será promovida por vencer somente um recorte diário
  ou mensal.
- O expoente inicial da cobertura será linear (`cobertura¹`). Qualquer
  aumento, como `cobertura²`, exige nova decisão explícita do conselho,
  porque poderia favorecer excessivamente estratégias que operam quase
  todos os dias mesmo sem vantagem estatística.

### 13.6 — Ratificação e implantação

Antes da ativação, o conselho deverá comparar, no mesmo dataset, o
ranking vigente e o ranking com presença, verificando:

1. mudanças nas primeiras posições;
2. impacto sobre estratégias de baixa frequência;
3. ausência de incentivo à sobreoperação;
4. estabilidade nos períodos longo, mensal e diário;
5. reprodutibilidade com o mesmo histórico;
6. **invariância ao lote**: a mesma estratégia, testada sozinha e testada
   junto de outras candidatas no mesmo histórico, produz exatamente o
   mesmo `pontuacao_final` — esta checagem é a que valida que a correção
   da v5 (denominador absoluto) funcionou de fato, e deve constar no PR
   de implementação com os dois números lado a lado.

Depois da ratificação, a alteração deverá constar no `changelog.md` e em
`classificacao.py`, acompanhada de testes automatizados para coberturas
de 0%, 50% e 100%, do teste de invariância do item 6 acima e de testes que
confirmem a aplicação nos rankings de entrada, saída e cruzado. Até essa
ratificação, a fórmula descrita originalmente na Regra 5 continua sendo
a única fórmula oficial.

---

## Termo de concordância

### Estratégias derivadas por desmembramento

É permitido extrair uma condição interna de uma estratégia composta e
publicá-la como estratégia independente quando o objetivo for medir sua
contribuição isolada. Isso não é considerado duplicação indevida se o arquivo:

- declarar expressamente a estratégia e a porta de origem;
- preservar os limiares originais ou documentar toda alteração;
- usar o contrato oficial `gerar_sinal(row) -> int`;
- não alegar resultado próprio antes de ser testado pelo motor oficial;
- entrar pelo mesmo fluxo de Pull Request e revisão do conselho;
- não substituir automaticamente a titular apenas por vencer um recorte.

Um agregador pode preservar a ordem histórica dessas estratégias para fins de
paridade. Seleção dinâmica entre estratégias exige validação separada, sem
informação futura, primeiro em modo sombra e depois em holdout cego.

---

Ao adicionar um arquivo em `estrategia/`, o participante declara:

> "Eu, `<nome do participante — humano ou identificação da IA e de quem a
> operou>`, li as Regras do Jogo acima (versão 8), e confirmo que o
> código que estou submetendo:
> 1. respeita o contrato de entrada ou saída (Regra 1) sem exceções;
> 2. usa apenas os campos documentados no template oficial (atualizado);
> 3. não contém I/O, acesso a rede, nem tentativa de ler/alterar qualquer
>    outro arquivo do projeto — inclusive não importa `configuracao.py`
>    nem qualquer outro módulo do projeto;
> 4. não afirma validação que não foi comprovada rodando o motor real, e
>    qualquer benchmark citado vem com o período exato do dataset;
> 5. identifica sua própria autoria (humana, IA, ou ambas), e, se usar o
>    padrão `v<NN>` no nome do arquivo, deixa claro que é numeração
>    própria do autor, não a VERSAO do projeto;
> 6. não duplica, com outro nome, um arquivo já existente no laboratório;
> 7. declara quantas variações relevantes foram testadas antes desta
>    versão (Regra 11.2), e não depende de nenhuma data ou estrutura
>    específica do dataset (Regra 11.3);
> 8. foi submetida como Pull Request e aguarda (ou já obteve) revisão do
>    conselho antes de qualquer teste oficial contra o bloco de Validação
>    (Regra 12);
> 9. reconhece o Acumulado da Regra 5 como critério único de ordenação dos
>    rankings de entrada, saída e cruzado, sem dispensar os demais testes de
>    robustez;
> 10. se for um arquivo de saída, entende que é o único responsável por
>    definir o stop e o alvo da posição desde a abertura — o motor não
>    calcula nem garante nenhum piso de segurança (Regra 1)."

Sem essa declaração — implícita ou explícita — o arquivo não deve ser
importado no laboratório.

---

## Histórico de mudanças

- **v8** (proposta, pendente de ratificação): reescrita da Regra 1. O
  motor deixa de ter qualquer fórmula própria de stop/alvo —
  `calcular_stop_alvo` foi removida de `motor.py`. O arquivo de saída
  titular passa a ser consultado já na abertura da posição (não só a cada
  candle), e é o único responsável por definir o stop e o alvo, do
  primeiro instante ao último; se nunca definir nada, a posição fica sem
  proteção de preço nenhuma até o corte de horário do pregão — decisão
  explícita do dono do laboratório ("a estratégia deve ser totalmente do
  cartucho, não do motor"), depois de duas iterações intermediárias
  (permitir só apertar o stop; depois permitir qualquer reconfiguração,
  mas com o motor ainda calculando um valor inicial de referência) terem
  sido corrigidas por não atenderem ao pedido por completo. `row` ganhou
  documentação formal de `ohlc_recentes` (já existia desde a V444) como
  campo disponível para cartuchos de saída que precisem calcular um nível
  estrutural próprio, já que não recebem mais a lista de candles.
  Consequência constatada ao testar: `baseline.py`, que sempre devolvia
  `False`, deixou de refletir o RR=1,55 fixo (porque essa fórmula não
  existe mais em lugar nenhum) e passou a virar, silenciosamente, uma
  estratégia de "segurar até o corte de horário" — drawdown medido subiu
  de -309,19 para -498,39 no dataset oficial só por causa disso.
  `baseline.py` foi reescrito para calcular, dentro do próprio arquivo, a
  mesma fórmula que antes vivia no motor (stop estrutural via
  `row["ohlc_recentes"]` + RR 1,55, fixados uma única vez na abertura) —
  validado reproduzindo resultado e drawdown idênticos aos de antes da
  mudança de contrato. Regra 3 expandida para deixar explícito que um
  cartucho não importa `configuracao.py` nem qualquer outro módulo do
  projeto — valores usados são copiados e documentados como cópia.
  `gerar_sinal` (entrada) não é afetado por nenhuma parte desta mudança.
- **v7** (proposta, pendente de ratificação): simplificado o critério oficial
  de classificação. Pontuação Composta, presença e multi deixam de ordenar os
  rankings. Entrada, saída e cruzado passam a usar exclusivamente
  `acumulado = resultado - abs(drawdown)`. As métricas anteriores continuam
  disponíveis para auditoria e robustez. A Regra 13 foi revogada como regra
  de ranking e preservada apenas como histórico das propostas v4–v6.
- **v6** (proposta, pendente de ratificação): ampliada a Regra 13 para os
  três modos oficiais. Entrada e saída passam a ser ordenadas por
  `multi_final = multi_base × cobertura`; o ranking cruzado permanece
  ordenado por `pontuacao_final = pontuacao_base × cobertura`. As notas-base
  continuam exibidas para auditoria. Formalizado que cobertura zero produz
  pontuação final exatamente zero.
- **v5** (proposta, pendente de ratificação): reescrita a Regra 13
  (fator de presença) proposta na v4. Revisão do Claude identificou que o
  denominador original (maior número de dias operados **do grupo testado
  junto**) reabria o problema de comparabilidade que a V433 fechou de
  propósito para o `multi` — a mesma estratégia pontuaria diferente
  dependendo de quem mais fosse testado na mesma rodada. Corrigido para
  um denominador absoluto (total de pregões do período do dataset, fixo,
  independente de concorrentes), preservando a intenção original
  (confirmada pelo dono do laboratório: dias operados, resultado e
  drawdown devem pesar juntos na pontuação) sem reabrir a instabilidade.
  Simplificação colateral: a definição de "grupos comparáveis" da v4
  deixa de ser necessária para este cálculo. Adicionado item de checagem
  de invariância ao lote na Regra 13.6. Expandidas as Regras 6 e 7 para
  documentar o significado do número de versão no padrão de nome de
  arquivo `<lado>_<assinatura>_v<NN>.py`.
- **v4**: adicionada a Regra 13 (fator de presença, versão original com
  denominador relativo ao grupo — substituída na v5).
- **v3**: adicionada a Regra 11 (garimpagem histórica — divisão
  Desenvolvimento/Validação/Holdout Cego, divulgação de variações
  testadas, proibição de dependência de dataset específico) e a Regra 12
  (aprovação prévia do conselho via Pull Request no GitHub, antes de
  qualquer teste oficial em `classificacao.py`). Motivada por preocupação
  levantada pelo dono do laboratório: nada na v2 impedia iteração
  repetida contra o mesmo histórico de validação até "encontrar" uma
  combinação vencedora, e não havia portão de revisão do conselho antes
  do teste oficial. Contrato da Regra 1 e a lista de campos da Regra 2
  foram atualizados para refletir a arquitetura atual de entrada/saída
  separadas (v2 mencionava só `laboratorio/estrategias/` e um único
  cartucho).
- **v2**: adicionada a seção "Objetivo do laboratório", Regras 9 (dataset
  explícito) e 10 (teste de robustez), expandidas as Regras 2, 4, 5 e 7.
- **v1**: versão original, 8 regras.
# Contrato do orquestrador dinâmico (V453)

Uma estratégia só pode participar do orquestrador se fornecer, sem I/O e sem
acesso a dados futuros:

```python
gerar_sinal(row) -> -1, 0 ou 1
diagnosticar_oportunidades(row) -> list[dict]
```

Cada oportunidade deve informar `estrategia`, `sinal`, `confirmadas`, `total`,
`progresso`, `faltantes` e `prioridade`. Opcionalmente pode informar
`aderencia_regime` e `confianca`, ambas entre 0 e 1. Cartucho com falha é
isolado e não pode derrubar os demais. Sinais opostos praticamente empatados
são bloqueados por segurança.

O orquestrador é um cartucho candidato comum: precisa ser executado pelo mesmo
`motor.py`, aparecer no ranking oficial e vencer pelos critérios vigentes antes
de substituir o titular. É proibido escolher estratégia usando resultado do
próprio candle, classificação futura ou qualquer dado posterior a `row['dt']`.
