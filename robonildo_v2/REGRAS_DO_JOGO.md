# Regras do Jogo — Laboratório de Estratégias ROBONILDO_V2

Antes de escrever ou submeter qualquer arquivo em `estrategias/`, todo
participante — humano, colega, ou IA (ChatGPT, Claude, ou qualquer outra) —
concorda com as regras abaixo. São as mesmas cartas pra todo mundo: ninguém
joga com regra diferente, ninguém decide sozinho que uma regra não se aplica
a ele.

Se um participante (inclusive uma IA agindo em nome de alguém) não puder
concordar com algum item abaixo, ele não deve gerar ou submeter código pra
este laboratório.

---

## 1. O contrato é fixo: `gerar_sinal(row) -> int`

- Recebe **uma única linha** (`row`) e devolve **um único inteiro**: `1`
  (compra), `-1` (venda) ou `0` (nada).
- Nada além disso. Sem parâmetros extras, sem retorno de tupla, sem efeito
  colateral esperado.
- A lógica de entrada é a **única** responsabilidade da estratégia. Stop,
  alvo, limite diário, bloqueio de horário e custo são do `motor_backtest.py`
  — a estratégia não recalcula, não contorna, não "ajusta" nenhuma dessas
  regras por conta própria.

## 2. Use os nomes de coluna exatos — não adivinhe

- A lista completa e oficial de campos disponíveis em `row` está em
  `estrategias/_template.py`. É a única fonte confiável.
- Não é permitido inventar nome de coluna, tentar variações "prováveis"
  (`maxima`, `máxima`, `high`...) nem criar indicador novo dentro do próprio
  arquivo da estratégia.
- Se sua ideia precisa de um indicador que não existe ainda, ele entra em
  `indicadores.py` — uma vez só, documentado, reaproveitado por todos. Nunca
  dentro do arquivo da estratégia individual.

## 3. Proibido qualquer I/O ou acesso fora do escopo de `row`

Uma estratégia não tem motivo legítimo para:

- Importar `os`, `sys`, `subprocess`, `socket`, `requests`, ou qualquer
  biblioteca de rede/processo/sistema de arquivos.
- Usar `open()`, `eval()`, `exec()`, ou reabrir o dataset (`.csv`) por conta
  própria.
- Ler, escrever ou alterar qualquer arquivo do projeto — incluindo
  `motor_backtest.py`, `indicadores.py`, `rodar_ranking.py`,
  `classificacao.py`, `ranking.csv` ou `classificacao.csv`.
- Manter estado global que acumule informação de candles além do que o
  motor já entrega linha a linha.

Qualquer um desses itens presente num arquivo de estratégia é motivo
automático de rejeição, mesmo sem prova de má intenção — a regra é sobre o
que o código **pode** fazer, não sobre o que a pessoa/IA diz que ele faz.

## 4. Sem alegação de "já validado" sem prova rodada

- Comentário ou docstring não é validação. Nenhuma estratégia entra
  documentada como "testada", "estável" ou "validada no histórico do
  laboratório" a menos que tenha sido **de fato rodada** neste motor, com
  resultado exportado em `ranking.csv` ou `classificacao.csv`.
- Se uma IA gerou o código, qualquer afirmação de que um filtro, horário ou
  regime "se mostrou melhor" precisa vir acompanhada do resultado real que
  comprova isso — ou ser removida do comentário antes da submissão.

## 5. Critério de subida no ranking — regra de ouro (já em `RANKING.md`)

- Nenhuma estratégia sobe no ranking só pelo resultado agregado.
- O critério é o **Mínimo Comparado** entre Teste Longo e Teste Curto (ou o
  critério equivalente vigente em `classificacao.py`).
- Amostra pequena (poucas dezenas de trades, e principalmente poucos trades
  no Teste Curto) não é validação — é candidata a validação. Deve ser
  rotulada como tal enquanto não tiver amostra robusta.

## 6. Transparência de autoria

- Todo arquivo de estratégia identifica, no docstring, se foi escrito por
  humano, gerado por IA (e qual), ou uma combinação — e por quem foi
  revisado antes de entrar no laboratório.
- Isso não é burocracia: é o que permite rastrear a origem se um problema
  aparecer depois.

## 7. Nomenclatura

- Arquivo novo: `estrategias/nome_da_estrategia.py`, com `gerar_sinal(row)`.
- Nome de arquivo começando com `_` é reservado para arquivos internos
  (ex: `_template.py`) — o `rodar_ranking.py`/`classificacao.py` ignora
  esses arquivos na descoberta automática. Não usar esse prefixo pra
  "esconder" uma estratégia da avaliação.

## 8. Execução em ambiente controlado

- Todo arquivo novo — principalmente vindo de fora do círculo direto de
  confiança, ou gerado por IA sem revisão humana completa — deve ser lido
  na íntegra por um humano **antes** de ser importado e rodado.
- Sempre que possível, roda-se primeiro em ambiente isolado (sem rede, sem
  permissão de escrita fora de uma pasta descartável).
- O dataset (`WINFUT_F_0_15min.csv`) deve permanecer com permissão de
  somente leitura.

---

## Termo de concordância

Ao adicionar um arquivo em `estrategias/`, o participante declara:

> "Eu, `<nome do participante — humano ou identificação da IA e de quem a
> operou>`, li as Regras do Jogo acima, e confirmo que o código que estou
> submetendo:
> 1. respeita o contrato `gerar_sinal(row) -> int` sem exceções;
> 2. usa apenas os campos documentados em `_template.py`;
> 3. não contém I/O, acesso a rede, nem tentativa de ler/alterar qualquer
>    outro arquivo do projeto;
> 4. não afirma validação que não foi comprovada rodando o motor real;
> 5. identifica sua própria autoria (humana, IA, ou ambas)."

Sem essa declaração — implícita ou explícita — o arquivo não deve ser
importado no laboratório.
