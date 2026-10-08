# ROBONILDO — Changelog

Arquivo único e estável — entradas empilhadas, mais recente no topo.

---

## V509 — console e narração: "porta" vira "escalação", "Radar" vira "Escala"

Pedido do dono (08/10/2026). Só texto, nenhuma lógica mudou:
- Narração: "(porta 2 de 3)" → "(escalação 2 de 3)"; "da Porta 2 perdeu confirmação" → "da escalação 2 perdeu confirmação".
- Console: linha `[RADAR]` → `[ESCALA]`; no batimento, "Radar <status>" → "Escala <status>".

---

## V508 — classificacao.py (C002): time, titulares e reservas numa tabela só

Pedido do dono (07/10/2026): apresentar a classificação com o time, seguido dos titulares (azul), dos reservas
(branco) e do último em vermelho, por resultado acumulado.
- Modo E (e A) com escalação: uma única tabela — **time** e **titulares** em azul (a cor de sempre), time no topo, **reservas** em
  branco, o último da tabela em vermelho. Dentro de cada grupo a ordem é a de sempre (acumulado).
- Coluna `pos` = lugar do cartucho no ranking de entradas (um reserva pode ter lugar melhor que um titular); `T` = time.
- Some a tabela separada "ESCALAÇÃO x TITULARES INDIVIDUAIS" (a linha da Regra 17 continua abaixo). Ranking
  interno, planilha do modo A e modos S/C/D não mudaram. `VERSAO_CLASSIFICACAO` C001 → C002.

---

## V507 — robô preenche a aba REGISTRO_OPERACOES (planilha PLANO_TRADE)

Proposta do dono (07/10/2026): alimentar a aba REGISTRO_OPERACOES e chamar a planilha só de PLANO_TRADE.
- Planilha: o robô procura `D:\DAYTRADE\PLANO_TRADE.xlsx` e, se não achar aberta, `PLANO_TRADE_MA_v2.xlsx`. Pode
  renomear o arquivo quando quiser (feche o Excel, renomeie, reabra); o vínculo DDE não depende do nome.
- Aba REGISTRO_OPERACOES: uma linha por operação, escrita na entrada e completada na saída — data, hora de entrada,
  lado, entrada, stop, alvo, hora de saída, saída, motivo, resultado (pts e R$ líquido), pico (R$), devolveu (R$),
  banca após. Coluna O guarda o id da operação (não editar): reiniciar o robô com posição aberta não duplica a linha.
- Na primeira partida o robô troca o cabeçalho do modelo antigo (MA_v2: Fechamento/MA21/MA50/Distância…) pelo novo e
  apaga só a linha de exemplo de 17/08/2026. Cabeçalho diferente disso: não escreve nada.
- Excel ocupado: 3 tentativas; se falhar, avisa no console (a verdade continua em `operacoes_<dia>.csv`). Não grava no replay.

---

## V506 — LOGS e ANALISE fora da pasta do robô

Pedido do dono (07/10/2026): as pastas de logs e de análise não ficam dentro da pasta do robô.
- Logs (operações, auditoria, caminho das operações, coleta DDE, `estado_risco.json`, notícias lidas) passam a
  `D:\DAYTRADE\LOGS`; as planilhas do `classificacao.py` modo A, a `D:\DAYTRADE\ANALISE` (continua valendo
  a opção de escolher outra pasta ao rodar).
- Na primeira partida o robô copia o que existir em `<pasta do robô>\logs` e ainda não existir na nova pasta
  (principalmente o `estado_risco.json`, com posição aberta e banca). Nada é apagado nem sobrescrito.
- Caminhos ficam em `configuracao.py` (`PASTA_LOGS`, `PASTA_ANALISE`).

---

## V505 — robô grava o caminho de cada operação (pico, horário do pico, vale, derrapagem)

Pergunta do dono (07/10/2026): o lucro de pico é mesmo devolvido antes da saída? O backtest só vê máxima/mínima de
candle de 15 min (e acha isso raro); ao vivo, 06 e 07/10 mostraram o contrário. Agora o robô guarda o dado real:
- `logs/caminho_operacoes.csv`: uma linha por operação fechada — pico (pts e R$), horário do pico, minutos até o pico,
  vale, **devolução** (pico − resultado, pts e % do pico), **derrapagem** na saída (preço do DDE × nível teórico do
  stop/alvo; positivo = pior), duração, nº de leituras e maior intervalo entre leituras (acusa buraco no DDE).
- `logs/caminho_pontos_<dia>.csv`: trilha de preços da operação (no máx. 1 por segundo), para testar regras de saída
  em dado real. `logs/caminho_aberto.json`: estado da operação em curso (sobrevive a reinício do robô).
- `analisar_caminhos.py [pasta] [ativação R$]`: resumo e simulação "estopar com X% de queda do pico" (10% a 90%)
  sobre as trilhas gravadas, comparada ao resultado real.
- Só grava (não decide nada); preço é a leitura do DDE, não o fill da corretora. Desligado no replay. Não muda
  `operacoes_<dia>.csv`, auditoria, motor, risco nem ordens.

---

## V504 — saída titular sem corte antecipado de operação em prejuízo

Pedido do dono (07/10/2026): se a operação se desenrola em prejuízo, nenhum corte antes das 18:20:58.
- Titular de saída agora é `saida_baseline` (stop dos últimos 5 candles + alvo 1,55R, sem regra de horário). A
  `saida_protecao_encerramento_v02` (cortes das 17h15 e 18h) virou candidata em `estrategia/saida/`.
- Só fecham a operação: stop, alvo e o corte absoluto das 18:20:58 do motor (inalterado).
- Medição (time titular, K de volatilidade por ano): 2026 R$ 17.070 vs 17.494 (−424); 2020–25 R$ 7.259 vs 6.184 (+1.075).
  Em 2026 os cortes ajudavam um pouco; nos anos anteriores atrapalhavam. Nenhum código de motor mudou.

---

## V503 — classificacao.py modo A: colunas do Time na "Apuração diária"

Pedido do dono (07/10/2026): na aba "Horários por dia" ele não achou o resultado do time num dia (06/10).
- "Apuração diária" ganhou, logo depois de Data e Dia, três colunas do time (escalação × saída titular; com um
  titular só, o rótulo é "Titular"): **Time (R$)** com o resultado do dia, **Entrada** e **Saída** (hora de entrada e
  janela do candle de saída). Com mais de uma operação no dia, uma por linha, na mesma ordem. A linha Total soma o Time.
- As colunas por estratégia vêm depois, como antes. Mensal, anual e "Horários por dia" não mudaram.

---

## V502 — radar dos três titulares + replay sem gravar no histórico acumulado

Log de replay do dono (07/10/2026, V500):
- **Radar cego.** Com os três titulares em arquivos, o radar mostrava `0/1 | aguardando condições | 0%` o tempo
  todo (e sempre a MACD + Estocástico): os arquivos extraídos só tinham `gerar_sinal`, sem o radar que as portas
  tinham no titular antigo. Cada um dos três ganhou `diagnosticar_oportunidades(row)` com as mesmas condições
  (X/Y confirmações, próxima condição que falta, "BLOQUEADA ATÉ …"). `gerar_sinal` não mudou: em 49.503
  avaliações (2025-26) o sinal do radar e o `gerar_sinal` divergiram 0 vezes.
- **Replay gravava no arquivo real.** O replay trocava, no `historico_acumulado.csv`, os candles reais do dia pelos
  que ele montava (o das 09:00, só a partir da hora em que o replay começou). Agora, em replay, nada é gravado nesse
  arquivo; o robô avisa na partida.

---

## V501 — classificacao.py modo A: aba "Horários por dia"

Pedido do dono (07/10/2026): na análise diária, incluir o horário em que a estratégia entrou e saiu da operação.
- Nova aba "Horários por dia" na planilha do modo A, ao lado da "Apuração diária", com o mesmo desenho (dia nas
  linhas, estratégia nas colunas). Cada célula lista as operações do dia: `entrada 09:45 | saída 10:30-10:45 | +55,00`.
  A hora de entrada é a da execução; a saída é a janela de 15 min do candle em que a posição fechou (OHLC de 15 min
  não revela o minuto exato do stop/alvo), igual à aba "Operações titulares".
- A "Apuração diária" (valores) não mudou. Metodologia atualizada.

---

## V500 — rechecagem do export sem poluir o console

Log do dono (07/10, 02:54): com candles aproximados na base, a rechecagem do export a cada 30 s repetia a linha
"[HISTORICO] ... tem candle mais recente ..." o tempo todo. O resolvedor do CSV agora só imprime quando a mensagem muda.
O histórico acumulado na pasta `ACUMULADO` (V499) funcionou: 7224 candles carregados, 3 aproximados, entradas liberadas.

---

## V499 — recuperação do buraco pelo export também antes da abertura

Log do dono (07/10, 02:42): o robô V498 partiu com o histórico persistente terminando em 05/10 18:00, avisou "buraco de
39 candles, entradas bloqueadas" (correto: o dia 06/10 inteiro não está no arquivo), mas disse que conferia a pasta a
cada 30 s e isso só acontecia depois que o mercado abrisse ("Bom dia! Aguardando abertura" desviava o laço).
- A conferência do export do Profit agora roda antes dos desvios "aguardando abertura" e "mercado encerrado". Exportar
  o histórico de madrugada libera na hora (simulado: partida com o mesmo buraco, export às 02:59, "Entradas LIBERADAS").
- `BURACO_MAX_CANDLES_PREENCHER` 37 → 38: um pregão tem 38 candles (09:00 a 18:15), não 37.
- Histórico acumulado fora da pasta do robô (ideia do dono): `D:\DAYTRADE\HISTORICO\ACUMULADO\historico_acumulado.csv`
  (`PASTA_HISTORICO_ACUMULADO`). Rodar o script de outra pasta (cópia de segurança, versão de teste) usa e alimenta o
  mesmo histórico, sem buraco ao trocar de pasta (foi o caso de 06/10: o dia ficou gravado na outra pasta). Na 1ª
  partida copia o arquivo do local antigo (`logs\`). A pasta não atrapalha o backtest (só enxerga pastas de ano).
  A cópia da outra pasta precisa ter a mesma linha em `configuracao.py`; e nunca dois robôs ao mesmo tempo.
- O ROT funcionou no Windows do dono ("planilha encontrada pelo nome").
- Pendente de entender: o arquivo persistente não tem nenhum candle de 06/10 (último: 05/10 18:00) embora o robô tenha
  rodado o dia todo.

---

## V498 — integridade da base de dados: checar na partida, narrar, recuperar sozinho

Incidente de 06/10/2026: a entrada das 15:15 foi bloqueada por "buraco" e o robô não tinha dito nada o dia todo.
Duas causas empilhadas (ata `conselho/2026-10-07-AI.txt`): (1) o candle das 18:15 nunca fechava (o robô parava de
ler às 18:20:58), então a manhã seguinte via 1 candle faltando e bloqueava 50 candles desde as 09:15; (2) a
planilha DDE ficou parada ~1 h com o Excel ocupado e a falha de leitura era silenciosa. O limite de 25% da banca
NÃO participou (removido na V483).
- `integridade_historico.py` (novo): análise de buracos de pregão, recuperador pelo CSV e vigia de leitura do DDE.
- Partida: a continuidade do histórico é a primeira checagem, nos dois caminhos de carga (persistente e CSV), com
  voz. Antes só rodava no caminho do CSV e só imprimia.
- **Buraco NÃO bloqueia mais a entrada** (pedido do dono, 07/10: bloquear repetiria a falha do dia). O robô avisa na
  hora, tenta preencher com o export do Profit e, o que o export não cobrir, preenche por aproximação (reta entre o
  preço antes e depois; candle plano, só em memória, nunca no arquivo) e segue operando. Linha de status mostra
  "dados aproximados (N candles)". Quando o export do Profit cobrir, os aproximados são trocados pelos reais (checado
  a cada 30 s, sem reiniciar). Medido em 2025-26: aproximar erra o sinal em ~53% no 1º candle depois do buraco, ~12%
  no 10º, ~0% no 30º (ignorar o buraco erra 78%/50%/4%).
- Exceção: buraco maior que `BURACO_MAX_CANDLES_PREENCHER` (37 candles, um pregão: robô desligado por dias, como em
  01/10 com 80 candles) não tem base para aproximar. Esse caso ainda bloqueia por `CANDLES_AQUECIMENTO_APOS_BURACO`
  (50), com lembrete falado a cada 5 min (`LEMBRETE_BLOQUEIO_SEGUNDOS`), aviso quando o radar chega a 100% e
  liberação automática ao exportar o histórico. Para nunca bloquear: valor enorme em `BURACO_MAX_CANDLES_PREENCHER`.
- Fim do pregão: o robô segue acompanhando sem operar até o candle das 18:15 fechar (relógio do DDE em 18:30, ou 60 s
  com o DDE parado) e o salva. Não há mais buraco falso na manhã seguinte.
- DDE: falha de leitura vira aviso falado em 10 s (8 s com posição aberta, com e-mail); no instante em que um candle
  inteiro se perde na queda, "BURACO NOS DADOS AGORA"; ao voltar a leitura, confere e preenche na hora. Console: no
  máximo uma linha de falha a cada 30 s.
- `leitor_dde.py`: tenta achar a planilha por nome (ROT) para o DDE poder viver numa instância própria do Excel;
  se não achar, comportamento de antes. NÃO testado em Windows.
- `_noticias` inicializado (erro latente).

---

## V497 — escalação de titulares de entrada (Regra 17)

Pedido do dono (06/10/2026): o "cenário" é o radar do terminal (Retomada MA21, MACD + Estocástico, Saída de
Extremo...), só que agora escalando entre estratégias titulares, cada uma num arquivo.
- `escalacao.py` (novo): `estrategia/entrada/titular/` aceita 1 ou mais cartuchos. A cada candle todos são
  consultados; só um lado sinalizando, entra o de maior prioridade (`PRIORIDADE_ESCALACAO`, depois ordem
  alfabética); lados opostos no mesmo candle, não entra. Uma posição por vez, regras de risco inalteradas.
- `principal.py` e `classificacao.py` usam a mesma escalação. Com 1 titular nada muda (o `tres_portas` segue
  como titular em transição). Com 2 ou mais, o juiz mostra "ESCALAÇÃO x TITULARES INDIVIDUAIS" no modo E, fora
  do ranking, e usa o time como entrada titular nos modos S e A.
- Saída: continua 1 titular (radar de saída fica para depois).
- Medições na ata `conselho/2026-10-06-AH.txt`: cenários de mercado (6) não escolhem par de forma estável
  (só "esticado" e "fim de tarde" repetem); saídas livres (sem alvo, stop de segurança largo) não vencem o esqueleto
  atual; a `tendencia_trailing_v01` lidera o acumulado 2020–2026.
- `compliance.md`: Regra 17, adendo 6.

---

## V496 — saídas: uma regra de encerramento por arquivo (Regra 16)

Pedido do dono (05/10/2026): a mesma regra das entradas. Funil encadeado pode; regra solta no mesmo arquivo
não. Stop e alvo da abertura (Regra 1) são a base de toda saída e não contam.
- 9 saídas agregadas movidas para `estrategia/saida/desclassificadas/` (perda_fim_tarde, protecoes_cirurgicas,
  composta, stop_limitado_alvo_forte_v01, reversao_lucro, alvo_risco_curto, perda_forca_macd,
  regime04_v6_ab_rrfixo, compressao_atr). O corte 17h15 estava copiado em 9 arquivos e o das 18h em 7.
- 4 saídas isoladas novas por extração literal: `perda_leve_1630_v01`, `perda_final_1700_v01`,
  `stop_atr_alvo_ma21_v01`, `stop_limitado_alvo_forte_v02`. Paridade: 0 divergências em 4.000 estados
  por comparação (fechamento e abertura).
- Titular de saída (`saida_protecao_encerramento_v02` = 17h15 + 18h) não foi trocado; só comentário.
- Medição na ata AG: de 2020 a 2025 os cortes da titular pioram o acumulado (−9.259 contra −7.229 sem corte);
  em 2026 ajudam pouco (+465).
- `compliance.md`: itens 7 e 8 da Regra 16, item 12 do Termo, adendo 5. Ata `conselho/2026-10-05-AG.txt`.

---

## V495 — candidata `entrada_compressao_amplitude_v02` (v01 corrigida)

Pedido do dono (05/10/2026). A v01 (DeepSeek, hoje em `desclassificada/`) nunca emitia sinal: o máximo da
compressão incluía o próprio candle atual. A v02 usa as 12 velas anteriores; nenhum limiar mudou.
- Medição (saída titular, preços reescalados, 2020–2025): 211 operações, R$ 37,7 por operação, t = 3,01;
  2026: −274 de acumulado. Variante B (compressão também só nas velas anteriores): t = 2,92. Declaradas as
  duas variações (Regra 11.2).
- Entradas quase não coincidem com a compressão por faixa em ATR (2 a 9 por ano): não é regra repetida.
- Leitura honesta: t alto fora de 2026, mas 2020–2025 já foi visto em ranking agregado, 2026 é negativo e são
  poucas operações; pede Regra 10 e acompanhamento à frente antes de qualquer promoção.
- Paridade com a variante medida: 0 divergências.

---

## V494 — sem nome de IA nos nomes de arquivo

Pedido do dono (05/10/2026). 54 cartuchos de entrada e saída renomeados para
`<lado>_<estrategia>_v<NN>.py` (ex.: `saida_chatgpt_v4` → `saida_protecao_encerramento_v02`,
`entrada_aroon_forte_claude_v1` → `entrada_aroon_forte_v01`). Conteúdo e regras intactos; só o nome do
arquivo e as referências a esses nomes nos comentários e na constante `NOME`.
- Titulares: `entrada_grok_3_v1` → `entrada_tres_portas_v01`; `saida_chatgpt_v4` →
  `saida_protecao_encerramento_v02`. Carregados pela pasta `titular/`; nenhum código de motor, risco ou ordem
  foi alterado. Os nomes novos aparecem nos logs e no ranking.
- Tabela antigo → novo em `conselho/2026-10-05-AF.txt`; atas, changelog e diário antigos não foram reescritos.
- Removida a cópia de `saida_chatgpt_v4` da raiz de `saida/` (idêntica à titular).
- `compliance.md`: Regra 7 deixa de dizer que os existentes não são renomeados.

---

## V493 — ranking de entrada: dois cartuchos saem da raiz

Pedido do dono (05/10/2026). Movidos para `estrategia/entrada/desclassificada/` (só um comentário de
cabeçalho; conteúdo intacto):
- `entrada_regime_04_v6`: agregador OU, contra a Regra 16 (as portas 1 e 2 repetem o grok_3). A parte nova,
  os vetos da porta 3, já está isolada em `entrada_saida_extremo_v02`.
- `entrada_deepseek_compressao_rompimento_V99`: **nunca emite sinal** (0 sinais em 2024 e em 2026, contra
  81 e 38 da compressão do ChatGPT). Causa: o máximo/mínimo da compressão inclui o candle atual
  (`ohlc_recentes[-1]`), então o fechamento nunca supera o máximo mais a folga. Não é duplicata da
  compressão do ChatGPT; é um cartucho quebrado. Uma versão corrigida entraria como `v02`, com a Regra 11.2.
- Nenhum código de motor, risco ou ordem alterado.

---

## V492 — candidata `entrada_saida_extremo_v02` (saída de extremo com vetos)

Pedido do dono (05/10/2026), a partir do `entrada_regime_04_v6` que ele enviou.
- `estrategia/entrada/entrada_saida_extremo_v02.py`: a porta 3 (saída de extremo) isolada, mais os dois
  vetos do arquivo enviado (V5: cruzamento fraco e tendência fraca; V6: extremo raso e mercado já
  expandido). Ideia única (Regra 16): as portas 1 e 2 do arquivo original repetiam o grok_3 e ficaram
  de fora. Limiares copiados, nada ajustado.
- `entrada_saida_extremo_v01.py`: a porta 3 sem vetos, que estava em `desclassificada/` como
  `entrada_saida_extremo_claude_v1`, renomeada pelo padrão da V491 e posta no ranking como base de comparação.
- Medição prévia (saída v4, preços reescalados): 2026 sobe de 4.167 para 4.812 de acumulado; de 2020 a 2025
  o resultado cai de 1.947 para 445 e o acumulado fica igual. Sem base para promover; é para o teste oficial.
- Paridade com a lógica original: 0 divergências em 32.533 candles (2020, 2023, 2025, 2026).

---

## V491 — nomes de arquivo pela estratégia, sem nome de IA; regra repetida é eliminada

Pedido do dono (05/10/2026). `compliance.md` (CODEOWNERS):
- Padrão `<lado>_<estrategia>_v<NN>.py` (ex.: `entrada_macd_v01.py`, `entrada_ma_estocastico_v01.py`,
  `saida_stop_atr_v01.py`): o nome diz a ideia; `v<NN>` é a versão da estratégia; autoria só no docstring.
- Regra 7: regra repetida (inclusive dentro de cartucho maior) é eliminada; duplicata não entra no
  laboratório. Regra 6 e itens 5 e 6 do Termo ajustados; adendo 4 no histórico.
- Cartuchos já existentes não são renomeados (as atas citam esses nomes). Só documentação.

---

## V490 — Regra 16: uma estratégia, uma ideia (sem OU interno)

Pergunta do dono (05/10/2026): o titular reúne várias estratégias dentro dele? Conferido: as
três portas do `entrada_grok_3_v1` são livres, ligadas por OU com prioridade fixa, e as portas
1 e 2 nunca disparam juntas. Quase toda a família "3 portas" é assim. O dono: confirmação
encadeada (E, ex.: MA + estocástico) fica; OU entre ideias não.
- `compliance.md`: Regra 16 (ideia única; E permitido, OU proibido; titular de ideia única;
  agregador só como paridade, fora do ranking; combinar ideias exige modo sombra e Holdout
  cego), item 12 no Termo, adendo 3 no histórico.
- 11 agregadores candidatos movidos para `estrategia/entrada/desclassificada/`; cópia duplicada
  de `entrada_grok_3_v1` na raiz removida. O titular não foi trocado.
- Ata `conselho/2026-10-05-AE.txt`: denúncia, levantamento e medição das portas isoladas
  (2020-2026): nenhuma tem vantagem fora de 2026; em 2026 a melhor é a MACD+estocástico
  (acumulado 6.335, contra 17.160 do agregador).
- Nenhum código de motor, risco ou ordem alterado.

---

## V489 — Regra 12: só o dono aprova; revisão do conselho vira consultiva

Pedido do dono (05/10/2026): só ele faz o merge dos PRs, então a exigência de aprovação
do conselho antes do teste oficial não faz sentido. `compliance.md` (CODEOWNERS):
- Regra 12 reescrita: o PR continua sendo o portão (autoria, declaração de variações,
  Regra 11.3), mas quem aprova é o dono, e o merge dele é a aprovação. Outras IAs podem
  comentar; não bloqueia.
- O restante não muda: teste oficial só depois do merge, Regra 10 e Holdout na promoção.
- Ajustados os dois lugares que citavam "revisão do conselho" (lista de contribuições
  isoladas e item 8 do Termo de concordância) e acrescentado o adendo 2 ao histórico.
- Só documentação; nenhum código alterado. As atas anteriores não são reescritas (Regra 15).

## V488 — narração não promete ordem depois do horário limite

Log de 05/10/2026, 18:15: o robô narrou "Se confirmado no fechamento das 18:30, a ordem
será disparada", mas 18:30 é depois de `HORARIO_BLOQUEIO_NOVAS_ENTRADAS` (18:20) e do corte
forçado (18:20:58): nenhuma ordem era possível. A narração de expectativa avaliava a estratégia
sem checar o gestor.
- A frase passa por `gestor.pode_abrir_posicao(fechamento previsto)`, a mesma porta da entrada
  real. Se recusar (horário limite ou limite diário de perdas), diz o motivo em vez de prometer
  a ordem. Só muda texto/voz; sinal, ordem e risco não mudam.
- Medido no backtest (titular, 7 anos): entradas executadas às 18:15 são raras (0 a 9 por ano,
  27 no total) e somam R$ -220; não é um problema financeiro, só de aviso. O horário limite
  (18:20) NÃO foi alterado; decisão do dono se quiser antecipá-lo.
- Não testado ao vivo (Windows).

## V487 — três entradas candidatas a partir da documentação de indicadores da Nelogica

A documentação (94 indicadores exportáveis pelo DDE do Profit + 85 artigos) foi estudada;
13 hipóteses de indicadores (9 de preço, 4 de volume) com parâmetros padrão foram
testadas UMA vez cada, em 2020-2026, com a saída titular v4 (ata `conselho/2026-10-05-AD.txt`).
- Novas candidatas em `estrategia/entrada/`: `entrada_keltner_rompimento_claude_v1.py`,
  `entrada_cci_100_claude_v1.py`, `entrada_aroon_forte_claude_v1.py`. Sinais idênticos aos
  do teste (0 divergências em 16.501 candles).
- 2020-2025: R$ 12,1 mil (Keltner), 12,8 mil (CCI), 13,5 mil (Aroon) contra 6,2 mil do titular
  de entrada; em 2026 todas ficam muito abaixo do titular (R$ 17,5 mil, ajustado a 2026).
- **Evidência fraca**: t de 1,4 a 2,1; nenhuma sobrevive à correção por 13 testes. As 4 de volume
  (CMF, MFI, Force Index, VWAP) falharam e não viraram cartucho.
- Campos de fluxo de ordens (agressão, Cumulative Delta, Weis Wave) não têm histórico: só dá para
  medir à frente; proposta de coleta passiva na ata. Nenhum titular, motor ou configuração alterado.

---

## V486 — avisos de integridade do DDE deixam de inundar a narração

Log de 05/10/2026: na abertura (09:04–09:31) o DDE chegou em rajadas, com o horário
congelado por até ~2,5 min, e o robô emitiu **825 avisos** (342 "Preço parado", 461
"Horário do DDE distante", 22 "Salto suspeito"), um por iteração (~2 s), cada um
falado em voz alta. A fila do SAPI não tem limite, então a voz continuou lendo avisos
velhos depois das 11:40.
- Um aviso de cada tipo a cada 120 s (`AVISO_INTEGRIDADE_REPETIR_SEGUNDOS`, impresso e
  narrado).
- `narrar(..., descartavel=True)`: se a voz ainda está falando, o aviso não entra na fila.
  Usado só nos avisos de integridade; as demais narrações não mudam.
- Não alterado: o robô continua **sem bloquear entradas** quando o vínculo está
  atrasado/congelado (os avisos só informam). Pendente de decisão do dono.
- Não testado em Windows/SAPI (ambiente de desenvolvimento é Linux): conferir no
  próximo pregão.

---

## V485 — pasta `estrategia/testes/` removida

Decisão do dono: a pasta não faz parte do núcleo do projeto. Conferido que nada
(`principal`, `motor`, `classificacao`, `historico_csv`, cartuchos) importa dela;
só havia comentários citando o caminho. Removidos os 17 arquivos de teste e o passo
"Testes de laboratório" do CI; ficam as checagens de compilação e da Regra 3.
Ajustados dois comentários (`classificacao.py`, `historico_csv.py`). Nenhuma
estratégia, motor ou configuração alterados.

Consequência assumida: o CI deixa de rodar testes automáticos (trava de risco/fail-closed
V462, igualdade serial x paralelo, histórico por ano). O código de teste continua no
histórico do git (commit anterior a este) se for preciso recuperar.

---

## V484 — medição das candidatas ChatGPT "meta 20k"

Executados os passos 1 e 2 da ata AB (7 anos, preços reescalados, 1 contrato):
- `entrada_chatgpt_compressao_rompimento_v1` — R$ 8.662, 391 ops, t=2,4, drawdown
  -1.188; positiva em todos os anos de 2020-2025, -195 em 2026. **Volta para
  `estrategia/entrada/` como candidata.**
- `entrada_chatgpt_abertura_expansao_v1` (t=0,3) e `entrada_chatgpt_gap_continuacao_v1`
  (t=0,2, drawdown -3.048) ficam em `desclassificada/`.
- `saida_chatgpt_tempo_sem_progresso_v1` (já em `saida/`): +R$ 1.129 e drawdown menor
  que a v4 com o titular de entrada, mas pior em 2021 e 2026; efeito pequeno.
- Detalhes no adendo de `conselho/2026-10-05-AB.txt`. Nenhum titular alterado;
  pendentes ranking C, Regra 10 e holdout após 05/10/2026.

---

## V483 — trava de 25% da banca desligada

Por decisão do dono (05/10/2026), `RISCO_MAXIMO_PCT_BANCA` passa de `0.25` para `0`.
Medido no mesmo motor (2020-2026, preços reescalados à volatilidade de 2026, 1 contrato):

| Trava | Titular (R$) | Entrada composta + saída v4 (R$) | 2026 titular (R$) |
|---|---|---|---|
| 25% (antes) | 21.826 | 24.364 | 15.066 |
| 35% | 23.225 | 25.679 | 17.389 |
| 50% | 23.446 | 25.800 | 17.494 |
| desligada | 23.679 | 25.890 | 17.494 |

- A trava bloqueava poucas entradas (4 a 11 por ano) e, na soma, custou mais do que evitou
  (+R$ 1.853 no titular sem ela). Por ano o efeito é misto: ela ajudou em 2022, 2023 e 2024
  (+R$ 738, +1.043, +751) e atrapalhou em 2020, 2025 e 2026 (-1.301, -518, -2.428).
- Risco assumido: sem a trava, a pior perda isolada simulada foi R$ 707 (2024, ~47% da banca
  real de R$ 1.490, igual ao incidente de 01/10); em 2026 a pior foi R$ 205.
- `motor.validar_risco_inicial`: `pct == 0` desliga só o limite percentual; a recusa por stop
  inválido/ausente (fail-closed, V462) continua ativa. Teste novo
  `test_pct_zero_nao_desliga_o_fail_closed`.
- Para religar: `RISCO_MAXIMO_PCT_BANCA = 0.25` (ou 0.35 / 0.5) em `configuracao.py`.

---

## V482 — adendo 2 da ata AA: histórico completo e causa da discrepância de 2026

Só documentação (`conselho/2026-10-05-AA.txt`), nenhum código alterado. Substitui as
estimativas do adendo 1 por números medidos nos 7 anos (2020-2026) e investiga por
que 2026 rende R$ 79 por operação contra R$ -17 a +10 nos outros anos:
- não é poucos trades, volatilidade, estrutura do preço, ajuste de preço ou escala
  (entrada aleatória com a saída titular rende ~0 em 2026 também);
- os filtros fixos de `entrada_grok_3_v1` (quinta-feira, janelas de horário, faixas
  de amplitude em pontos) respondem por cerca de metade da vantagem em 2026 e quase
  nada nos outros anos: assinatura de ajuste à amostra (Regra 11.3);
- a vantagem da entrada composta se apagou em 2024-2026 (+173 em 3 anos);
- o histórico tem preços ajustados (pontos antigos inflados) e o pregão fechava às
  17:45 em 2/3 dos dias até 2023.
Pede ao conselho a revisão do titular de entrada e limiares em ATR em vez de pontos.

**Testes:** o `test_chatgpt_meta20k.py` (quebrado desde que as 3 entradas do ChatGPT
foram para `entrada/desclassificada/`) foi removido na V481; nesta rebase a correção
que eu tinha feito nele ficou sem efeito.

---

## V481 — saída ChatGPT estrutural assimétrica

- Adiciona `saida_chatgpt_estrutura_assimetrica_v1.py` como candidata S001.
- Stop estrutural de quatro candles limitado a 2,10 ATR.
- Alvo assimétrico: 1,90R em compras e 1,55R em vendas.
- Em 2026 até 24/09, com a entrada titular: resultado R$16.420,63, drawdown -R$323,50 e acumulado R$16.097,12.
- Nenhum titular foi alterado; detalhes e limitações em `conselho/2026-10-05-AC.txt`.

---

## V480 — Regra 15 (atas sempre consultadas) e adendo da ata AA

Só documentação, nenhum código alterado.
- `compliance.md`: nova **Regra 15** — as atas do conselho devem ser consultadas
  antes de propor, testar, promover ou descartar; o PR cita as atas lidas;
  resultados que influenciam decisões são registrados em ata; atas não são
  reescritas (correção por ata nova ou adendo datado); períodos consumidos como
  Holdout ficam registrados. Item 11 na declaração do Termo de concordância.
  A Regra 14 (portão estatístico das atas) segue sem texto no documento.
- `conselho/2026-10-05-AA.txt`, adendo 1: diagnóstico por cenário (modo D) de 2026
  e de 2020-2025 e simulação em memória de "se cenário X, então Y" (roteador de
  saída). Mapas completos por cenário (melhor cartucho por cenário em 2020-2025)
  perdem ~R$ 1.500 em 2026: sobreajuste. Só a hipótese R1 (saída composta em
  lateral, titular no resto) fica registrada para medição à frente; nada foi
  implementado. Corrige a ata: o ganho da entrada composta é consistente em sinal,
  mas de significância no limite (t ~ 2).

---

## V479 — candidatas ChatGPT com novas fontes de retorno

Meta de pesquisa: superar os R$ 15.909,65 de melhor cruzamento conhecido em
2026 e investigar se R$ 20 mil de Acumulado é alcançável sem aumentar contratos.
O valor é uma meta, não resultado prometido.

Foram adicionadas três entradas independentes:

- `entrada_chatgpt_abertura_expansao_v1.py`: primeiro fechamento confirmado
  fora da faixa formada entre 09:00 e 10:00;
- `entrada_chatgpt_compressao_rompimento_v1.py`: primeiro rompimento após oito
  candles comprimidos em múltiplos de ATR;
- `entrada_chatgpt_gap_continuacao_v1.py`: continuação matinal de gap moderado
  que permaneceu aberto.

Também foi adicionada `saida_chatgpt_tempo_sem_progresso_v1.py`, que conserva
o stop estrutural e o alvo 1,55R da saída titular, mas encerra uma operação após
quatro candles quando ela continua negativa e nunca avançou 0,45 ATR.

Todas são candidatas. Nenhum titular ou motor foi alterado. Em cumprimento à
Regra 12 do `compliance.md`, não houve ranking oficial antes da revisão do PR.
A verificação foi sintética: seis testes novos e suíte completa com 109 testes
OK e seis pulados, além de `py_compile` e `git diff --check`.

### Arquivos

- três `estrategia/entrada/entrada_chatgpt_*_v1.py`;
- `estrategia/saida/saida_chatgpt_tempo_sem_progresso_v1.py`;
- `estrategia/testes/test_chatgpt_meta20k.py`;
- `conselho/2026-10-05-AB.txt`;
- `versionamento.py`, `changelog.md`.

---

## V478 — ata AA do conselho: rankings de 7 anos (2020-2026)

Documentação (`conselho/2026-10-05-AA.txt`) e ajuste dos testes. Registra os
rankings de entrada, saída e cruzado rodados no motor V477 e a leitura deles:
- a entrada composta supera o titular em 7 anos (+R$ 2.798), com o ganho fora de
  2026: segue candidata, ainda sem Regra 10 nem Holdout;
- a saída composta não tem evidência fora de 2026 (+915 em 7 anos, +663 só em 2026,
  drawdown pior): o titular `saida_chatgpt_v4` fica;
- `saida_stop_atr` cai de 2ª (2026) para 15ª (7 anos);
- 2026 é um regime atípico; o drawdown de 7 anos exige ~4x a banca real;
- o agregado de 7 anos queimou o 2025 como ano cego: o único Holdout real é o futuro.
Lista também as rodadas pendentes (cruzada 2020-2025, entrada por ano, janela do
drawdown, Regra 10).

**Testes:** 13 testes estavam quebrados na `main` desde o commit que moveu as
candidatas descartadas para `entrada/desclassificada/` e `saida/desclassificadas/`.
Novo `estrategia/testes/apoio_cartuchos.py` localiza o cartucho em qualquer das
duas pastas; os testes de daytrader/paulinho importam do novo caminho. Suíte: 103
testes OK, 6 pulados.

---

## V477 — mais rápido: sem cópia do histórico a cada candle e em vários processos

**Motor de simulação:** o `executar_jogo` entregava ao motor uma cópia de todo o
histórico até o candle atual, a cada candle (custo quadrático). Com a linha de
indicadores pronta o motor só lê o último candle, então agora recebe só ele. Mesmo
resultado; metade do tempo de uma combinação em 2026 e ganho muito maior com anos.

**Paralelismo (modos E, S, C e A):** o histórico é cortado em blocos de pregões
seguidos e cada bloco roda em um processo (cálculo dos indicadores do bloco + todas
as combinações), juntando as operações no fim. É exato porque o motor não leva nada
de um pregão para o outro. Padrão: núcleos − 1 (máx. 8) — no seu PC de 4 núcleos,
3 processos. `--processos N` escolhe; `--sem-paralelo` roda em série. O modo D e
históricos pequenos (< 2.500 candles) rodam em série.

Conferido: as 576 combinações de 2026 dão exatamente as mesmas operações em série e
em paralelo (e `test_paralelo.py` repete a conferência numa série sintética).

---

## V476 — histórico por ano (uma pasta por ano)

O backtest passa a ler uma pasta por ano: `D:\DAYTRADE\HISTORICO\2023`, `\2024`,
… `\2026`, cada uma com um ou mais `.csv` de 15 min do Profit. O robô
(`principal.py`) continua lendo só a pasta do ano corrente: `CAMINHO_HISTORICO_INICIAL`
aponta agora para `...\HISTORICO\2026\WINFUT_F_0_15min.csv` (se o nome do export
mudar, o CSV mais recente da pasta continua sendo escolhido sozinho).

No `classificacao.py`, depois de escolher o modo, aparece a pergunta
`Anos do backtest [Enter = todos | 2023-2025 | 2026 | ultimos 2 | 2023,2025]`
(ou use `--anos 2023-2025`). Os arquivos dos anos escolhidos viram uma série única.
Pastas com vários `.csv` são fundidas; entram só candles do ano da pasta e só
arquivos de 15 min (o resto é avisado e ignorado). Se os anos escolhidos não forem
consecutivos, os 3 primeiros pregões após o salto servem só de aquecimento. Sem
pastas de ano, tudo funciona como antes (arquivo único).

**Desempenho:** o cálculo dos indicadores relia o histórico inteiro a cada candle
(custo quadrático). Agora cada linha vê os últimos 1.500 candles (~40 pregões); as
linhas saem idênticas bit a bit (conferido em 2026 e 2023–24 e por teste), o
ranking de 2026 não muda e a rodada caiu de ~2 min para 34 s. Três pastas de ano
(684 pregões) rodam o modo E em ~2,5 min.

---

## V475 — limpeza do que não é usado por `classificacao.py` nem `principal.py`

Removidos (continuam no histórico do git): `classificacao_teste.py`,
`teste_email.py`, o arquivo vazio `python`, `estrategia/entrada/auxiliar/`,
`estrategia/entrada/desclassificada/`, `estrategia/saida/antigas/` (cópias
idênticas das saídas que seguem em `saida/`) e os testes de daytrader, paulinho
(entradas) e gabriel (entradas), que testavam código já apagado. Mantidos:
documentos, CI, CODEOWNERS e `sincronizar_github.bat`. O ranking não muda: 18
entradas, 32 saídas.

---

## V474 — testes fora das pastas de estratégia

`estrategia/entrada/` e `estrategia/saida/` passam a conter só estratégias
candidatas (mais as subpastas `titular/`, `auxiliar/`, `antigas/`,
`desclassificada/`). Os 17 `test_*.py` foram para `estrategia/testes/`; os dois
`test_candidatas_cenario.py` viraram `test_entrada_candidatas_cenario.py` e
`test_saida_candidatas_cenario.py`.

Rodar: `python -m unittest discover -s estrategia/testes -p "test_*.py"`
(99 testes). O CI foi ajustado e a checagem da Regra 3 agora varre as pastas de
estratégia sem exceção.

---

## V473 — `classificacao.py` só grava arquivo no modo A

Os modos E, S, C e D agora só imprimem na tela. Deixaram de ser gravados: o
histórico `logs/classificacao_historico.md`, os CSVs dos rankings, o CSV do
modo D e os CSVs do simulador. O modo A (Análise) continua gerando o Excel,
agora em `analise/` dentro da pasta do projeto (`..\DAYTRADE\ROBONILDO\analise`),
sem o destino antigo `D:\DAYTRADE\ANALISES` e sem cópia de reserva em `logs/`.
`--saida-dir` ainda permite escolher outra pasta.

---

## V472 — tela do `classificacao.py` mais enxuta

Saíram do início da execução: a linha "Multi = score ABSOLUTO…", os títulos
`[ETAPA 1/2]`/`[ETAPA 2/2]`, a lista de saídas validadas, a linha "Saídas
compatíveis | Combinações a executar" e o log de cada combinação. No lugar, uma
barra `[COMBINAÇÕES]` que atualiza na mesma linha. Incompatíveis continuam
aparecendo no fim.

---

## V471 — `classificacao.py` sem o inventário de cartuchos no início

Removido o bloco "CARTUCHOS NO DISCO (entrada/saída — sem laboratório)" que
aparecia no começo de toda execução. A descoberta de cartuchos e o relatório de
incompatíveis no final continuam como antes.

Também: `estrategia/entrada/test_candidatas_cenario.py` passa a pular (skip) os
testes de candidatas que foram removidas do disco, em vez de quebrar a suite.

---

## V470 — modo D (Diagnóstico de cenários) dentro do `classificacao.py`

O diagnóstico de cenários passou a ser uma opção do `classificacao.py`, ao lado
de E/S/C/A. O antigo `diagnostico_cenarios.py` (que chegou vazio na main) foi
incorporado e o arquivo removido.

Só leitura: R$ e operações de cada entrada (× saída titular) e de cada saída
(× entrada titular) por cenário; distribuição de cenários; matriz de acerto do
reconhecedor quando os dados são simulados em regimes; e, com `--metades`, o que
se repete nas duas metades do período. Não pergunta cenário (já separa por
cenário). Grava `logs/diagnostico_cenarios_c001_motor_<versão>.csv`.

`python classificacao.py [csv] --modo D [--metades]` ou, sem argumentos,
escolher **D** na pergunta do ranking.

### Arquivos alterados
- `classificacao.py` (modo D)
- `diagnostico_cenarios.py` (removido)
- `estrategia/entrada/test_modo_diagnostico.py` (novo), `test_cenario.py`
- `versionamento.py`, `changelog.md`

---

## V469 — descoberta sem depender de sublinhado no nome do arquivo

No disco do dono os arquivos `_*.py` perderam o `_` inicial. `_paulinho_just.py`,
`_daytrader_ohlc.py` e `_test_*.py` apareceram como candidatos incompatíveis e os
imports `estrategia.entrada._paulinho_just` / `._daytrader_ohlc` falharam
(`entrada_paulinho_just_fechamento_V01` deixou de carregar).

Correção que não depende do prefixo:

- auxiliares de cartucho em `estrategia/entrada/auxiliar/` (`daytrader_ohlc.py`,
  `paulinho_just.py`); a descoberta nunca desce em subpastas;
- testes renomeados para `test_*.py`, ignorados pelo `classificacao.py` (a regra
  dos arquivos `_*` reservados, Regra 7, continua valendo);
- imports dos 11 cartuchos atualizados; CI atualizado (`-p "test_*.py"`).

Rodar: `python -m unittest discover -s estrategia/entrada` (e `estrategia/saida`).
Merge com a main: mantidas as remoções do dono (daytrader, gabriel,
paulinho_origem); testes dependentes ajustados; `diagnostico_cenarios.py`, que
chegou vazio na main, foi restaurado (`test_cenario` depende dele).
Nenhuma estratégia ou titular alterado. **Ação do dono:** apagar de
`estrategia/entrada/` os arquivos antigos `daytrader_ohlc.py` e `paulinho_just.py`.

### Arquivos alterados
- `classificacao.py` (`_listar_py`)
- `estrategia/entrada/auxiliar/` (2 arquivos movidos) e 11 cartuchos de entrada (import)
- 16 arquivos `test_*.py` renomeados em `estrategia/entrada` e `estrategia/saida`
- `.github/workflows/robonildo-v2-ci.yml`, `historico_csv.py`
- `versionamento.py`, `changelog.md`

---

## V468 — candidatas compostas (entrada e saída) com holdout

Pedido: reunir as melhores regras em uma entrada e uma saída. Método: desenho em
janeiro–junho/2026; holdout em julho–outubro/2026 rodado uma única vez; nenhum
limiar novo (todos copiados dos cartuchos de origem).

- `saida_composta_stop_atr_alvo_ma21_claude_v1`: stop estrutural limitado a
  1,80 ATR + alvo na MA21 (com 1R de distância, senão 1,55R) + corte das 18h.
- `entrada_composta_grok_fim_tarde_claude_v1`: as três portas da `grok_3` (cópia
  literal) + rompimento de fim de tarde como 4ª porta.

Acumulado (resultado − |drawdown|), pareado com o titular da outra ponta:

| | desenho jan–jun | holdout jul–out | 2023–24 (já visto) |
|---|---|---|---|
| saída composta | 11.773 | 3.189 | −2.136 |
| `saida_chatgpt_v4` (titular) | 10.273 | 4.057 | −2.418 |
| `saida_stop_atr` (1ª do ranking) | 11.670 | 3.220 | −2.619 |
| entrada composta | 10.394 | 4.016 | −660 |
| `entrada_grok_3_v1` (titular) | 10.273 | 4.057 | −2.418 |

Nenhuma supera o titular no holdout de 2026. Nas demais entradas positivas
(chatgpt_v19/v21, deepseek_v5, gemini_V20, grok_32/4/v6, manus_v1/v2,
claude_v1) a união com a `grok_3` é idêntica à `grok_3`: não há sinal a somar. A
única que acrescenta é a de fim de tarde. Ficam como candidatas de laboratório;
promoção só pelo conselho (Regra 12). Nenhum titular alterado.

### Arquivos alterados
- `estrategia/entrada/entrada_composta_grok_fim_tarde_claude_v1.py`
- `estrategia/saida/saida_composta_stop_atr_alvo_ma21_claude_v1.py`
- `estrategia/entrada/_test_composta_grok_fim_tarde.py`
- `estrategia/saida/_test_composta_stop_atr_alvo_ma21.py`
- `versionamento.py`
- `changelog.md`

---

## V467 — pasta `tests/` extinta; testes passam para o laboratório

`estrategia/entrada` e `estrategia/saida` são o laboratório: a grande maioria das
candidatas é descartada e só quem passa na peneira chega a titular. Os testes de
verificação agora ficam ao lado delas, em arquivos com prefixo `_test_` (o `_`
os mantém fora da classificação, Regra 7). A pasta `tests/` foi removida.

- `estrategia/entrada/`: `_test_candidatas_cenario`, `_test_cenario`,
  `_test_periodo_simulador`, `_test_modo_analise`, `_test_historico_csv`,
  `_test_daytrader_entradas`, `_test_paulinho_entradas`, `_test_gabriel_entradas`
  (este último também cobre dados/volume do contrato Gabriel);
- `estrategia/saida/`: `_test_candidatas_cenario`, `_test_risco_stop`,
  `_test_daytrader_saida`, `_test_paulinho_saida`, `_test_gabriel_saidas`.

Nenhum teste foi removido (83 antes, 83 depois). Rodar:
`python -m unittest discover -s estrategia/entrada -p "_test_*.py"` e o mesmo
para `estrategia/saida`. O CI passa a rodar as duas suites e a checagem da
Regra 3 ignora `_test_*`. Nenhum cartucho nem titular foi alterado.

### Arquivos alterados
- `tests/` (removida)
- 17 arquivos `_test_*.py` em `estrategia/entrada` e `estrategia/saida`
- `.github/workflows/robonildo-v2-ci.yml`
- `historico_csv.py` (referência no docstring)
- `versionamento.py`
- `changelog.md`

---

## V466 — método Just de Paulinho convertido em candidatas auditáveis

A entrevista fornecida descreve regressão à média depois de um deslocamento
até uma região de exaustão. Para o índice, Paulinho informa faixas começando
em 0,60%; para a proteção, stop de 0,20% e alvo de 0,40%.

Foram criadas duas entradas independentes:

- `entrada_paulinho_just_fechamento_V01.py`: ±0,60% do fechamento anterior;
- `entrada_paulinho_just_origem_V01.py`: ±0,60% da origem intradiária.

Como o Robonildo decide no fechamento do candle de 15 minutos, o sinal exige
que o preço alcance a faixa, volte para dentro e feche na direção da regressão.
A proteção está em `saida_paulinho_just_rr2_V01.py`, arredondada ao tick do WIN.

O motor agora entrega 96 candles em `ohlc_recentes`, suficientes para localizar
a sessão anterior. Não foram inventados critérios não quantificados no vídeo,
como escolha visual da origem, faixas adicionais, notícias ou parciais. Nenhum
titular foi alterado. Detalhes em `estrategia/PAULINHO_JUST.md`.

### Arquivos alterados

- `motor.py`
- `estrategia/PAULINHO_JUST.md`
- `estrategia/entrada/_paulinho_just.py`
- dois cartuchos `estrategia/entrada/entrada_paulinho_*_V01.py`
- `estrategia/saida/saida_paulinho_just_rr2_V01.py`
- `tests/test_v466_cartuchos_paulinho.py` (somente validação; não é candidata)
- `tests/test_v465_strategias_importadas.py`
- `tests/test_gabriel_compatibilidade.py`
- `versionamento.py`
- `changelog.md`

---

## V465 — pacote `strategies` separado em entradas e saída

O pacote recebido continha 24 estratégias de outro framework. Nove delas usam
somente OHLC e foram convertidas em cartuchos candidatos de entrada: quatro
reversões de canal, um pullback de média e quatro falsos rompimentos. O estado
interno usado pelo framework original foi substituído por uma comparação
determinística entre o candle atual e o anterior.

As nove regras traziam a mesma proteção embutida. Ela agora é o cartucho de
saída candidato `saida_daytrader_rr2_v1.py`: stop de 1,25 vez a amplitude média
dos 20 candles anteriores, com piso de 20 pontos, e alvo de 2R. Dessa forma,
entrada e saída podem ser classificadas e cruzadas separadamente.

O motor passa a entregar 22 candles em `ohlc_recentes`, suficientes para a
regra de 20 períodos e a supressão do sinal consecutivo. O reconhecedor de
cenários foi explicitamente mantido em seus 12 candles originais, evitando
alteração indireta de comportamento.

A conversão foi confrontada com os arquivos originais em 9.394 candles reais:
zero divergências nas nove estratégias. Quatorze estratégias dependentes de
volume não foram ativadas porque o DDE e o laboratório ainda não fornecem esse
campo pelo mesmo contrato. A estratégia SMC v3 também ficou pendente, pois
exige uma máquina de estados com ciclo de vida ainda inexistente nos cartuchos.

Nenhum titular foi alterado. O inventário completo e os motivos técnicos estão
em `estrategia/IMPORTACAO_STRATEGIES.md`.

### Arquivos alterados

- `motor.py`
- `cenario.py`
- `estrategia/entrada/_daytrader_ohlc.py`
- nove cartuchos `estrategia/entrada/entrada_daytrader_*.py`
- `estrategia/saida/saida_daytrader_rr2_v1.py`
- `estrategia/IMPORTACAO_STRATEGIES.md`
- `tests/test_v465_strategias_importadas.py`
- `versionamento.py`
- `changelog.md`

---

## V464 — bloqueios de horário explícitos no radar

Quando a estratégia priorizada está fora de sua janela operacional, o radar
deixa de mostrar a expressão ambígua `Falta horário permitido` e informa a
situação diretamente, por exemplo:

`Radar Retomada MA21 | 0/3 | BLOQUEADA ATÉ 13:30 | 0% ■`

Os horários exibidos são horários do relógio. Como o candle rotulado 13:15
fecha às 13:30, um bloqueio inclusivo até esse rótulo aparece como
`BLOQUEADA ATÉ 13:30`. A Retomada MA21 também diferencia a quinta-feira e a
janela da tarde; MACD + Estocástico e Saída de Extremo mostram o fim de suas
respectivas janelas bloqueadas.

A mudança é exclusivamente visual. Nenhum horário, limiar, prioridade, sinal,
ordem, stop, alvo, motor ou cálculo da classificação foi alterado. O percentual
e o quadrado colorido continuam no final da linha.

O número V463 já aparece no `classificacao.py` da `main` para o critério de
pontos diários incorporado anteriormente. Por isso, esta entrega avança para
V464 e evita uma nova colisão de versões.

### Arquivos alterados

- `principal.py`
- `estrategia/entrada/entrada_grok_3_v1.py`
- `estrategia/entrada/titular/entrada_grok_3_v1.py`
- `versionamento.py`
- `changelog.md`

---

## V457 — a narração de expectativa passa a dizer a que horas a ordem sai

No pregão de 29/09 o log imprimiu, em sequência, "Nenhum sinal de entrada foi
confirmado" e logo abaixo "Se confirmado no fechamento, a ordem será
disparada". A leitura natural é que a ordem deveria ter saído naquele
fechamento — mas a frase se referia ao fechamento **seguinte**.

Não havia bug. O candle que fecha às 13:30 é o candle **rotulado 13:15**, e a
Porta 1 do titular bloqueia até "13:15" — aquele era o último candle do
bloqueio. A expectativa apontava para o fechamento das 13:45.

Agora a frase nomeia o horário: *"Se confirmado no fechamento das 13:45, a
ordem será disparada."* Nenhuma regra operacional mudou — é só texto.

Fica registrada, **sem alteração**, uma ambiguidade real na Porta 1: o
bloqueio escrito como até "13:15" se estende até as 13:30 no relógio, porque
o rótulo do candle é a abertura. Mexer nisso é mudança de estratégia e precisa
passar pelo `classificacao.py` nos dois períodos disponíveis antes de qualquer
decisão.

### Arquivo alterado

- `principal.py`

---

## V456 — portão estatístico: o ranking passa a mostrar quem empata com o 1º

O ranking apresentava como 1º, 2º e 3º lugares resultados cuja diferença era
menor que o ruído da própria amostra. O caso que motivou isto: a
`saida_chatgpt_v4` foi promovida a titular sobre a `saida_chatgpt_v3` por
R$ 56,12 — uma diferença que vem de apenas 5 operações entre as **mesmas 181**,
contra um erro padrão de R$ 2.164 no total do período (2,6% do ruído), e que na
primeira metade do histórico é exatamente R$ 0,00.

O `classificacao.py` agora calcula o desvio-padrão do resultado por operação e
o erro padrão do total do período, e imprime uma coluna nova, `emp`, marcando
com `=` toda posição cuja diferença para a 1ª seja **menor que essa faixa de
ruído**. No rodapé, informa a faixa em reais e em porcentagem, e quantas
posições empatam no topo.

Medido contra o dataset oficial (184 pregões): faixa de ruído de R$ 2.164,31 =
**12,7%** do resultado do 1º lugar. No ranking cruzado, **133 das 238
combinações empatam** com a primeira. No ranking de saída, **11 dos 17
cartuchos empatam** com o primeiro.

Nenhuma regra operacional mudou. O portão é informativo: não reordena, não
filtra ninguém e não toca no motor nem em cartucho algum. Ele apenas torna
visível a incerteza que já existia — e estabelece um piso verificável para
promoções: vantagem acima da faixa de ruído.

### Arquivo alterado

- `classificacao.py`

---

## V455 — radar quantitativo e recuperação silenciosa do DDE

O percentual e o quadrado colorido permanecem no final da linha. O radar passa
a quantificar a primeira condição pendente — por exemplo,
`afastamento 184/200 pts` — e, quando chega a 100%, informa há quantos segundos
a mesma oportunidade permanece continuamente confirmada. Se uma condição for
perdida, a contagem é reiniciada.

A estratégia titular recebeu somente campos de telemetria para o painel; seus
limiares, prioridades e sinais não foram modificados.

Falhas transitórias recuperadas nas tentativas internas de leitura do DDE não
são mais impressas. Se as três tentativas falharem, uma única mensagem final,
com o último erro COM, permanece visível e o ciclo é descartado com segurança.

### Arquivos alterados

- `principal.py`
- `leitor_dde.py`
- `estrategia/entrada/titular/entrada_grok_3_v1.py`
- `versionamento.py`
- `changelog.md`

---

## V454 — direção do candle e percentual do radar

A narração de fechamento sem entrada agora diferencia a direção efetiva do
candle da tendência estrutural das médias. Quando elas divergem, a mensagem é
objetiva: “O candle fechou em alta, mas a tendência das médias ainda é de
baixa. Nenhum sinal de entrada foi confirmado.” O cenário inverso também é
tratado, assim como candles alinhados ou estáveis.

O radar passa a apresentar o percentual de maturação ao lado do quadrado
colorido, no mesmo padrão da análise de uma posição aberta, por exemplo:
`50% ■`. A mudança é informativa e não altera sinais ou ordens.

### Arquivos alterados

- `principal.py`
- `versionamento.py`
- `changelog.md`

---

## V453 — candidato de orquestração dinâmica

Adicionado um cartucho capaz de descobrir e avaliar simultaneamente qualquer
quantidade de estratégias de entrada que forneçam o contrato completo de
telemetria. O orquestrador normaliza prontidão, aderência ao regime e confiança,
coloca a melhor oportunidade no radar e, quando houver confirmação, escolhe o
sinal de maior score. Conflitos direcionais quase empatados são bloqueados.

O orquestrador foi incluído como candidato do ranking e não foi promovido para
produção sem backtest. Ele não consulta resultados futuros nem arquivos de
classificação. Estratégias sem `diagnosticar_oportunidades(row)` continuam no
ranking individual, mas não participam da orquestração.

### Arquivos alterados

- `versionamento.py`
- `changelog.md`

### Arquivo novo

- `estrategia/entrada/entrada_orquestrador_dinamico_v1.py`

---

## V452 — dados isolados por instalação

Removido o caminho absoluto que ainda direcionava o histórico persistente à
instalação antiga em `D:\DAYTRADE\ROBONILDO`. Histórico acumulado, estado da
posição, registros, auditoria e relatórios passam a usar a pasta `logs` situada
na mesma raiz do projeto efetivamente executado. A localização funciona mesmo
quando o programa é iniciado a partir de outro diretório.

### Arquivos alterados

- `configuracao.py`
- `principal.py`
- `versionamento.py`
- `changelog.md`

---

## V451 — grade do radar alinhada

O radar passa a usar colunas fixas para preço, tendência, estratégia,
confirmações, condição faltante e indicador colorido. A troca da estratégia
prioritária não desloca mais as demais informações, e o quadrado permanece na
mesma posição. A alteração é exclusivamente visual.

### Arquivos alterados

- `principal.py`
- `versionamento.py`
- `changelog.md`

---

## V450 — grade da posição alinhada

A linha da operação corrente passa a usar campos de largura fixa, preservando
o alinhamento quando lado, resultado, distâncias ou percentual mudam de
tamanho. Foram acrescentados espaços entre as colunas e o prefixo `R$` foi
removido do resultado. A alteração é exclusivamente visual.

### Arquivos alterados

- `principal.py`
- `versionamento.py`
- `changelog.md`

---

## V449 — linha de posição compacta

Corrigida a quebra de linha no Prompt de Comando durante posição aberta. A
apresentação mantém lado, entrada, preço atual, resultado, alvo, stop,
distâncias e progresso, mas remove palavras redundantes. Não há alteração em
sinais, risco, saídas ou ordens.

### Arquivos alterados

- `principal.py`
- `versionamento.py`
- `changelog.md`

---

## V448 — estratégias isoladas e radar de oportunidades

As três portas ocultas da entrada titular Grok passam a existir também como
estratégias independentes e classificáveis: `Retomada MA21`,
`MACD + Estocástico` e `Saída de Extremo`. O agregador titular preserva os
mesmos limiares e a prioridade histórica, sem ativar seleção dinâmica de
ordens nesta etapa.

O novo radar mostra a estratégia mais próxima, confirmações `X/Y`, direção e
primeira condição faltante. O gradiente agora representa progresso técnico,
de roxo a verde-limão, em vez de permanecer roxo até surgir um sinal completo.
A narração anuncia cenários a partir de 70% e identifica nominalmente a
estratégia que confirmou a entrada. Durante posição aberta, a linha principal
prioriza entrada, preço atual, resultado, alvo, stop e distâncias.

### Arquivos alterados

- `motor.py`
- `principal.py`
- `estrategia/entrada/titular/entrada_grok_3_v1.py`
- `versionamento.py`
- `changelog.md`
- `compliance.md`

### Arquivos novos

- `estrategia/entrada/entrada_retomada_ma21_grok_v1.py`
- `estrategia/entrada/entrada_macd_estocastico_grok_v1.py`
- `estrategia/entrada/entrada_saida_extremo_grok_v1.py`

---

## V447 — narração de saída não confundia mais dict(fechar=False) com "fechar" (PR #9)

Bug apontado pelo ChatGPT e confirmado direto no código de `main`: a
narração especulativa de saída fazia `bool(avaliar_saida(...))`. Como
`avaliar_saida()` sempre devolve um dict (mesmo sem fechamento, ex.
`{"fechar": False, ...}`), e um dict não-vazio é sempre "verdadeiro" em
Python, o narrador avisava "saída se aproximando" em **todo** candle com
posição aberta — não só quando o cartucho realmente sinalizava
fechamento.

Corrigido para checar especificamente a chave `"fechar"` do dict. Escopo
confirmado antes de mexer: essa variável só alimenta a frase narrada —
não afeta a entrada, a ordem enviada ao Profit, nem o fechamento real da
posição. Era um bug cosmético na narração.

### Arquivo alterado

- `principal.py`

---

## V446 — classificacao.py passa a gerar log automático de resultado (PR #8)

Pedido do dono do laboratório: em vez de depender de alguém colar
manualmente o resultado de uma rodada no chat ou num PR, o próprio
`classificacao.py` agora grava sozinho o histórico de cada rodada.

Toda vez que o RANKING ENTRADA, RANKING SAÍDA ou RANKING CRUZADO é
impresso, o resultado também é gravado — em modo *append*, nunca
sobrescreve — em `logs/classificacao_historico.md`, carimbado com
data/hora e o SHA do commit do repositório em que rodou. Serve
diretamente a Regra 4 do `compliance.md`: dá para conferir depois se um
resultado foi mesmo rodado contra o motor atual, sem depender da palavra
de quem rodou.

### Arquivo alterado

- `classificacao.py`

---

## V445 — motor deixa de ter fórmula própria de saída

Pedido explícito do dono do laboratório, esclarecido em duas rodadas: a
estratégia de saída deve ser **inteiramente** do cartucho de saída
titular, não do motor — nem como piso de segurança, nem como "ponto de
partida" calculado na abertura.

`calcular_stop_alvo()` foi **removida** de `motor.py`. `Sinal`/`Posicao`
nascem com `stop=None`/`alvo=None`. O motor passa a consultar o cartucho
de saída titular já na abertura da posição (além de a cada candle
fechado, como sempre), usando o mesmo contrato de sempre
(`avaliar_saida(row, posicao) -> bool | dict`). Se o cartucho nunca
definir nível nenhum, a posição fica sem stop/alvo até o corte de horário
do pregão — comportamento esperado, não uma falha.

**Consequência encontrada ao testar** (`classificacao.py`, dataset
oficial): `baseline.py` sempre devolvia `False`, o que antes significava
"aceito o RR=1,55 que o motor já calculou". Sem essa fórmula em lugar
nenhum, devolver `False` sempre virou, silenciosamente, "segurar até o
corte de horário" — drawdown medido piorou de -309,19 para -498,39.
Corrigido reescrevendo `baseline.py` para calcular, dentro do próprio
arquivo, a mesma fórmula que antes vivia no motor (stop estrutural via
`row["ohlc_recentes"]`, novo desde a V444, + RR 1,55, fixados uma única
vez na abertura) — validado reproduzindo resultado (R$16.585,04 / 175
operações / drawdown -309,19) idêntico ao de antes da mudança de
contrato: migração comportamentalmente neutra, só muda onde a regra mora.

A candidata `saida_claude_v3.py` sofria do mesmo problema (sem stop
inicial). Substituída por `saida_claude_v4.py`, que soma um stop inicial
(mesma fórmula do baseline) ao comportamento de breakeven/trailing já
existente. Ainda não supera o baseline no dataset oficial (R$5.896,31 vs
R$16.585,04) — não promovida.

`compliance.md` atualizado para a Versão 8: Regra 1 reescrita para o novo
contrato; Regra 3 esclarecida contra um cartucho importar
`configuracao.py` ou qualquer outro módulo do projeto.

**Parte 2 (mesma versão) — o motor orquestra, o cartucho só avalia
estratégia/lucratividade:** faltava fechar o circuito na produção.
`principal.py` ainda chamava `abrir_posicao(sinal)` sem `row` — sem isso,
o motor nunca perguntava ao cartucho de saída o stop/alvo inicial fora do
backtest (`classificacao.py` já passava `row` corretamente). Corrigido
para `abrir_posicao(sinal, row=row_fechamento)`. `registrador.
registrar_operacao_aberta` e `email_notificacao.notificar_abertura`
passaram a receber a `Posicao` (com os níveis reais definidos pelo
cartucho), não o `Sinal` (que nunca carrega stop/alvo desde que o motor
parou de calculá-los) — isso também corrige um crash certo: o e-mail
formatava `sinal.stop`/`sinal.alvo` com `.2f`, que quebra com `None`.
A exibição ao vivo de progresso da posição (`principal.py`) também fazia
aritmética direta com `stop`/`alvo`, com o mesmo risco assim que um
cartucho (como `saida_claude_v4`) deixasse um dos dois sem definir —
corrigido para mostrar "o cartucho de saída ainda não definiu um
alvo/stop" em vez de quebrar ou inventar uma porcentagem. Testado
isoladamente (registro, e-mail e cálculo de progresso, com e sem níveis
definidos) — sem exceções em nenhum caso.

**Parte 3 (mesma versão) — corte de horário forçado disparava atrasado:**
`cfg.HORARIO_LIMITE_ABSOLUTO` foi alterado em algum momento de `"18:20"`
para `"18:20:58"` (com segundos, de propósito — reduzir a folga de
risco), mas as duas comparações contra esse valor (`motor.
verificar_corte_final` — o corte de segurança de verdade — e o aviso de
"mercado encerrado" em `principal.py`) continuaram comparando só por
minuto (`strftime("%H:%M")`). Como `"18:20" < "18:20:58"` em ordem
lexicográfica, o corte só disparava às **18:21:00** — o oposto do que a
mudança para segundos pretendia (quase 1min02s de atraso a mais, todo
dia). Corrigido para `strftime("%H:%M:%S")` nos dois lugares — testado e
confirmado disparando exatamente às 18:20:58. Removida também
`HORARIO_ULTIMO_CANDLE` de `configuracao.py` (sem uso há várias versões).
`HORARIO_LIMITE_ABSOLUTO` é agora, exclusivamente, o único horário de
saída forçada do projeto. `HORARIO_BLOQUEIO_NOVAS_ENTRADAS` (bloqueia
abrir posição nova, regra diferente) não foi tocado.

**Parte 4 (mesma versão) — `saida_grok_v6.py` sem stop nenhum como
titular:** o dono do laboratório trouxe um ranking de entrada ao vivo,
pareado com `saida_grok_v6.py` como saída titular, mostrando drawdown
quase idêntico (`-498,39`) repetido em quase todas as estratégias de
entrada "3 portas". Causa: `saida_grok_v6.py` (autoria Grok/xAI) é um
cartucho do contrato antigo (`avaliar_saida(row, posicao) -> bool`) que
nunca definia stop/alvo — a lógica original sempre assumiu "stop/alvo do
motor continuam prioritários", ela só antecipa um fechamento lucrativo
perto do fim do pregão (pós-17:30, lucro flutuante ≥ 1,0 ATR). Sob o
motor v10 (Parte 1 acima), que não tem mais fórmula própria nenhuma,
promovê-lo a titular deixou toda posição sem nenhuma proteção de preço —
só o corte de horário forçado (18:20:58) ou o próprio profit-lock
fechavam uma posição, absorvendo o prejuízo inteiro de qualquer dia ruim;
como as entradas "3 portas" são variações próximas da mesma ideia
(correlacionadas), várias caem no mesmo dia catastrófico, daí o drawdown
quase igual entre elas.

Corrigido com o mesmo padrão de migração do `baseline.py`: na abertura da
posição (`candles_decorridos == 0`) o arquivo agora define o mesmo stop
estrutural + alvo em RR 1,55 que o motor calculava antes
(`SWING_LOOKBACK_CANDLES`/`RELACAO_RISCO_RETORNO` copiados de
`configuracao.py`, não importados — Regra 3). Nas chamadas seguintes não
redefine mais nada, e a lógica original do autor (o profit-lock
pós-17:30) continua 100% inalterada a partir daí. Contrato atualizado de
`bool` para `dict`, igual aos demais cartuchos titulares desde a v10.
Docstring reescrita preservando o texto original do autor (Grok) para
rastreabilidade, separado do que foi acrescentado nesta migração, com
aviso de que o backtest antigo citado ali (medido contra o motor v7, com
stop/alvo fixo do motor) não vale mais e precisa ser re-testado contra o
motor v10 antes de qualquer nova comparação/promoção (Regra 4).

Validado: unit test isolado (`_stop_alvo_inicial` para COMPRA e VENDA,
janela insuficiente, e a lógica original do autor preservada em todos os
ramos) — sem exceção em nenhum caso. Rodado também via `classificacao.py`
no dataset oficial, colocado temporariamente como titular: resultado
R$16.336,05 (176 operações), drawdown **-309,19** — o mesmo número que
`baseline.py` reproduz, confirmando que a mesma proteção de preço foi
restaurada e o `-498,39` desaparece.

Arquivos alterados: `motor.py`, `estrategia/saida/titular/baseline.py`,
`principal.py`, `registrador.py`, `email_notificacao.py`, `analise.py`,
`configuracao.py`, `compliance.md`, `versionamento.py`, `saida_grok_v6.py`.
Arquivo novo: `estrategia/saida/saida_claude_v4.py` (candidata, não
titular). Arquivo removido do laboratório: `saida_claude_v3.py` (superada
pela v4).

---

## V444 — filtro DiNapoli 3x3 e nova candidata de entrada

O console passa a incluir em `row['ohlc_recentes']` uma tupla imutável com
os 12 últimos candles fechados. O campo é retrocompatível: cartuchos antigos
o ignoram e mantêm os mesmos sinais. Não há candle futuro nem estado privado
da estratégia.

Criada `entrada_chatgpt_dinapoli_v1.py`, derivada sem outras alterações da
entrada titular `grok_3_portas_assimetrica_v2.py`. O padrão DiNapoli 3x3 não
abre novas operações: funciona somente como veto da Porta 3 quando identifica
uma reversão contrária à entrada proposta. A configuração escolhida venceu a
titular nos três históricos de controle, sem piorar o drawdown:

- oficial (250 pregões): multi 1.078,7 contra 1.063,0;
- longo (429 pregões): multi 300,4 contra 296,5;
- controle 2026 (181 pregões): multi 831,8 contra 760,4.

A saída DiNapoli também foi pesquisada, mas não superou a titular em todos os
históricos e foi rejeitada. `saida_chatgpt_v3.py` é entregue apenas como
candidata vencedora do histórico oficial: multi 1.111,7 contra 1.063,0, com o
mesmo drawdown. A promoção continua condicionada ao ranking local atualizado.

Arquivos: `motor.py`, `entrada_chatgpt_dinapoli_v1.py`,
`saida_chatgpt_v3.py`, `versionamento.py` e `changelog.md`.

---

## V443 — narração de entrada identifica "porta X de Y" + confirma disparo

Esclarecido antes de implementar: não é um funil sequencial — só uma
porta dispara por candle, as outras não chegam a ser avaliadas naquele
caso. Implementado de forma honesta com essa realidade: novo campo
opcional `total_portas` no retorno de `diagnosticar_sinal()` — se
presente, a narração acrescenta "(porta X de Y)". Estratégias sem
esse campo continuam funcionando como antes.

Toda narração de expectativa de entrada agora termina com "Se
confirmado no fechamento, a ordem será disparada." — centralizado em
`principal.py`, não depende do texto de cada estratégia.

Arquivos alterados: `principal.py`,
`estrategia/entrada/titular/grok_3_portas_assimetrica_v2.py`.

---

## V442 — e-mail aceita mais de 1 destinatário

`EMAIL_NOTIFICACAO_DESTINATARIO` (em `configuracao.py`) agora aceita
vários e-mails separados por vírgula: `"voce@gmail.com,
socio@gmail.com"`. Espaços extras e vírgulas sobrando são ignorados.
Se a lista vier vazia, avisa no terminal e não tenta enviar — mesmo
padrão defensivo do resto do módulo.

Arquivo alterado: `email_notificacao.py`.

---

## V441 — "[CENÁRIO EM FORMAÇÃO]" agora é falado, não só impresso

Até a V440, esses avisos (expectativa de entrada, expectativa perdida,
saída se aproximando, progresso periódico) só apareciam no terminal —
decisão deliberada da V416, pra narração nunca competir com envio de
ordem. Verificado antes de reverter: `narrar()` usa SAPI com
`SVSFlagAsync=1`, genuinamente não bloqueante — não há risco técnico
em narrar também. Adicionado `narrar()` nos 5 pontos onde antes só
havia `print()`.

Arquivo alterado: `principal.py`.

---

## V440 — narração da saída passa a espelhar a da entrada

Duas adições: (1) aviso especulativo — com posição aberta e candle
ainda em formação, chama o cartucho de saída antecipadamente; se já
fecharia com o dado de agora, avisa antes do candle fechar de
verdade, com a explicação real via `diagnosticar_saida`. (2)
fechamento real explicado — quando o motivo é `SAIDA_CARTUCHO`, usa
a explicação do cartucho em vez da frase genérica de lucro/prejuízo.
Testado isoladamente em 3 cenários (não dispara cedo demais, dispara
com explicação real, cartucho quebrado nunca trava).

Arquivo alterado: `principal.py`.

---

## V439 — removido o modo LABORATÓRIO (L) do prompt de `principal.py`

Prompt volta a ser só REPLAY/NORMAL (R/N). O modo L chamava
`classificacao.executar()` e saía — redundante desde que
`classificacao.py` ganhou vida própria (e, com a V438, até pergunta
sozinho qual ranking rodar). Rodar o laboratório agora é sempre
`python classificacao.py` direto.

Arquivo alterado: `principal.py`.

---

## V438 — `classificacao.py` pergunta qual ranking rodar (E / S / C)

Ao iniciar, pergunta: **E** = ranking de entradas (cada entrada ×
saída titular), **S** = ranking de saídas (entrada titular × cada
saída), **C** = ranking cruzado (todas as combinações). Só executa
as combinações do modo escolhido — evita rodar o cartesiano completo
quando só se quer E ou S. Testado de ponta a ponta escolhendo "E":
confirmado que roda só as 4 combinações de entrada, resultado
idêntico a toda validação anterior.

Arquivo alterado: `classificacao.py`.

---

## V437 — candidata de saída `saida_grok_v6.py`

Trava de lucro no fim do pregão: depois das 17:30, se o lucro
flutuante já passou de 1,0× ATR, realiza — evita devolver ganho no
leilão/final do dia. Backtest isolado (V19 × saídas): +R$165,09
sobre o baseline, mesmo drawdown. Não usa `lado` (só
`resultado_flutuante_pts`, já direcional por natureza), o que evitou
por design o bug de comparação que pegou outras candidatas depois.

Arquivo novo: `saida_grok_v6.py` (candidata em `estrategia/saida/`).

---

## V436 — corrigida regressão: e-mail sumiu do `principal.py`

**Reportado:** e-mail não chegou na abertura de uma ordem real, mesmo
com tudo configurado e já validado via `teste_email.py` isolado.

**Causa raiz:** o `principal.py` em uso não tinha **nenhuma**
referência a `email_notificacao` — nem o import, nem as 4 chamadas
(implementadas originalmente na V427). A integração se perdeu em
algum ponto da reestruturação grande de entrada/saída (V429+), que
reescreveu boa parte do arquivo sem carregar essa parte junto —
regressão silenciosa, sem erro nenhum no log.

**Corrigido:** reinserido o import e as 4 chamadas
(`notificar_abertura`/`notificar_fechamento`), nos mesmos pontos de
sempre, adaptados à estrutura atual do arquivo.

Arquivos alterados: `principal.py`, `versionamento.py`.

---

## V435 — saída candidata com proteção de lucro

Criado `estrategia/saida/saida_chatgpt_v1.py` como **candidata**, sem
substituir `estrategia/saida/titular/baseline.py`. A promoção só deve ocorrer
se o ranking de saída e o ranking cruzado de `classificacao.py` confirmarem
melhora robusta.

A candidata trabalha exclusivamente no fechamento dos candles de 15 minutos:

- preserva a prioridade do stop e do alvo rígidos do motor;
- arma o trailing somente após máxima excursão favorável relevante;
- combina devolução de lucro com reversão adversa em Estocástico, RSI e MACD;
- possui proteção para devolução excepcional da MFE;
- realiza posição ainda lucrativa no candle rotulado 17:45, cuja execução
  histórica ocorre aproximadamente às 18:00, antes do corte rígido das 18:20.

A operação real de 24/09/2026 motivou a hipótese: VENDA em 185.420, melhor
excursão observada de aproximadamente +675 pontos e encerramento em 184.985
(+435 pontos; R$ 86,50 líquidos), após devolver cerca de 240 pontos do pico.
Esse caso ilustra a oportunidade, mas **não valida sozinho** a estratégia.

Segurança: a senha de aplicativo de e-mail foi removida de
`configuracao.py`. Agora é lida da variável de ambiente
`ROBONILDO_EMAIL_SENHA_APP`; `email_notificacao.py` não tenta autenticar sem
ela. A credencial anteriormente exposta deve ser revogada e substituída.

Arquivos novos/alterados: `saida_chatgpt_v1.py`, `configuracao.py`,
`email_notificacao.py`, `versionamento.py`, `changelog.md`.

---

## V434 — cartucho de saída "v1" renomeado para `baseline.py`

`saida_claude_v1.py` → `baseline.py`, mesma pasta
(`estrategia/saida/titular/`), mesmo conteúdo — sempre devolve
`False`, nunca antecipa fechamento. O nome novo reflete melhor o
papel dele: é a referência fixa a ser superada, não uma candidata
numerada na sequência v1/v2/v3.

A descoberta é puramente por pasta (exatamente 1 arquivo), então a
troca de nome não exigiu nenhuma mudança em `principal.py` nem
`classificacao.py` — testado e confirmado (inventário de cartuchos
continua mostrando `baseline.py [TITULAR]` normalmente).

Referências ao nome antigo atualizadas em `saida_claude_v2.py`
(comparação histórica de testes).

Arquivo renomeado: `saida_claude_v1.py` → `baseline.py`.
Arquivo alterado: `saida_claude_v2.py`, `versionamento.py`.

---

## V433 — pontuação "multi" passa a ser absoluta, não mais percentil

**Antes:** `multi` era o percentil 0-100 de cada horizonte **entre as
estratégias da rodada** — nota relativa, que mudava se o conjunto de
concorrentes mudasse.

**Agora:** `multi` é a média ponderada dos scores brutos individuais —
50% longo + 30% mensal + 20% diário (pesos redistribuídos se faltar
horizonte). Um colega que rode uma única estratégia isolada obtém o
**mesmo** `multi` que obteria aqui no arsenal completo — comparável por
valor, não por posição no ranking.

`_percentil_25` continua existindo, mas só dentro do cálculo de robustez
por janela — deixou de alimentar o `multi`. `_normalizar_percentil` foi
removido do caminho do `multi`.

Arquivo alterado: `classificacao.py`.

**Nota de reconciliação:** esta mudança e o rename do `baseline.py`
(entrada seguinte, agora V434) foram entregues como "V433" em duas
sessões paralelas, sem saber uma da outra. Renumerado nesta atualização —
sem conflito de código entre as duas, só de numeração.

---

## V432 — ranking triplo (entrada / saída / cruzado)

Com cartuchos de entrada e saída independentes, a classificação passa a
publicar **três** rankings:

1. **Ranking de entrada** — cada cartucho em `estrategia/entrada/` (titular +
   candidatas) pareado com a **saída titular**.
2. **Ranking de saída** — cada cartucho em `estrategia/saida/` pareado com a
   **entrada titular**.
3. **Ranking principal (cruzado)** — todas as combinações entrada × saída,
   ordenadas pela pontuação combinada. Colunas: posição, estratégia entrada,
   estratégia saída, resultado, diária, dias, drawdown, pontuação.

O motor (`MotorRobonildo`) já recebe `gerar_sinal` e `avaliar_saida` de forma
independente; a classificação só explora o produto cartesiano.

Árvore de pastas (inalterada desde V431):

```
estrategia/entrada/titular/   → 1 arquivo (produção)
estrategia/entrada/*.py      → candidatas
estrategia/saida/titular/     → 1 arquivo (produção)
estrategia/saida/*.py        → candidatas
```

Arquivos alterados: `classificacao.py`, `versionamento.py`, `changelog.md`.

---

## V429 — arquitetura de dois cartuchos independentes (entrada/saída)

Implementa a estrutura aprovada em conselho (rodada 3): a competição
passa a disputar entrada **e** saída, em cartuchos independentes.

### Estrutura de pastas

- `estrategia/entrada/` substitui `estrategia/` — mesma regra
  (exatamente 1 arquivo, `gerar_sinal(row)` obrigatório).
- `estrategia/saida/` é nova — exatamente 1 arquivo,
  `avaliar_saida(row, posicao) -> bool` obrigatório.
- `saida_claude_v1.py` é o baseline inicial: sempre devolve `False`,
  reproduz o comportamento atual (RR=1,55 fixo) sem nenhuma diferença —
  existe para dar um alvo concreto a ser superado, não para vencer.

### Motor (`motor.py`)

- `Posicao` ganhou `candles_decorridos`, `maxima_desde_entrada`,
  `minima_desde_entrada` — rastreados automaticamente pelo motor; o
  cartucho de saída nunca guarda estado próprio.
- `verificar_saida()` aceita `avaliar_saida` opcional no
  `MotorRobonildo()` e `row` opcional na chamada. Ordem de prioridade
  fechada em conselho: (1) stop/alvo do motor — piso/teto duro, sempre
  primeiro; (2) cartucho de saída — só antecipa, nunca afrouxa,
  consultado apenas se (1) não fechou; (3) corte de horário —
  inalterado.
- Exceção no cartucho de saída nunca derruba o motor — cai no padrão
  (não fecha antecipado) e fica registrada em
  `motor.ultimo_erro_saida`.
- `posicao` pública passada ao cartucho: lado, entrada,
  candles_decorridos, máxima/mínima desde a entrada, resultado
  flutuante em pontos — **sem** `motivo_entrada` (decisão do
  DeepSeek, aceita: evita acoplamento oculto entre os dois cartuchos).

### Produção e laboratório (`principal.py`, `classificacao.py`)

Descoberta dos dois cartuchos com implementação única, reaproveitada
nos dois arquivos. `classificacao.py` pareia toda estratégia de
**entrada** candidata com o cartucho de **saída titular do momento** —
nada fixo no código de teste.

### Validação

Regressão confirmada: sinal do candle de 18/09 14:15 idêntico (VENDA
@ 186.570,0). Rodada completa do dataset oficial: 121 trades,
composição ALVO=44/STOP=23/CORTE=54, **zero** "SAIDA_CARTUCHO"
espúrio com o baseline — confirma que a nova arquitetura não muda
nenhum resultado já validado.

Arquivos alterados: `motor.py`, `principal.py`, `classificacao.py`,
`versionamento.py`. Pasta nova: `estrategia/entrada/`,
`estrategia/saida/`.

---

## V428 — encerramento de mercado agora finaliza o script

Ao atingir `HORARIO_LIMITE_ABSOLUTO` (18:20) sem posição aberta
internamente:

1. Envia **ALT+Z de segurança** para o Profit mesmo assim, sem checagem
   prévia — cobre o cenário de uma ordem ter ficado aberta no Profit
   sem o robô saber (desync já visto neste projeto antes).
2. Narra **"Finalizado."**
3. **O script termina** — antes, ficava rodando indefinidamente,
   aguardando o pregão seguinte. Agora, operar no dia seguinte exige
   rodar `python principal.py` de novo.

Arquivos alterados: `principal.py`, `versionamento.py`.

---

## V427 — notificação por e-mail em cada abertura/fechamento de posição

Novo módulo `email_notificacao.py`: envia um resumo por e-mail a cada
abertura ou fechamento de posição real (lado, entrada, stop, alvo,
motivo do fechamento, resultado em pontos e reais).

**Desligado por padrão** (`EMAIL_NOTIFICACAO_ATIVO = False` em
`configuracao.py`) — é opt-in. Preencha destinatário, remetente e a
**senha de app** do Gmail (não a senha normal da conta — o Gmail exige
2FA + uma senha de app específica, gerada em
`myaccount.google.com/apppasswords`) antes de ligar.

**Mesmo princípio da narração/notícias (V416):** o envio nunca pode
atrasar nem bloquear a decisão ou o envio de uma ordem. Roda numa
thread separada com timeout curto; qualquer falha (rede, credencial,
servidor fora do ar) fica contida ali — só um aviso no terminal, nunca
uma exceção propagada. Testado com servidor SMTP inválido de propósito:
retorno em menos de 1ms tanto desativado quanto com falha simulada.

Arquivo novo: `email_notificacao.py`.
Arquivos alterados: `principal.py`, `configuracao.py`, `versionamento.py`.

---

## V426 — fim da narração repetida de avisos de integridade do DDE

Reportado: avisos de "preço parado" e "deriva de relógio" eram narrados
de novo a cada ciclo de leitura (~2 segundos) enquanto a mesma situação
persistisse — gerando dezenas de narrações idênticas em poucos minutos.

Corrigido com cooldown de 60 segundos por categoria de aviso, em
`leitor_dde.py`. A checagem continua rodando a cada ciclo normalmente;
só a emissão do aviso (e a narração correspondente) fica espaçada
enquanto a situação não mudar. Testado: 3 minutos de preço travado
(90 ciclos) geraram 3 avisos, não mais 90.

Arquivos alterados: `leitor_dde.py`, `versionamento.py`.

---

## V425 — investigando ordens que não chegam ao Profit (diagnóstico)

**Reportado em produção:** o log mostra "Enviado ALT+C para o Profit",
a posição fica "aberta" internamente (preço flutua, resultado é
calculado) — mas a ordem nunca chega ao Profit de verdade. Sério: o
robô poderia tentar fechar uma posição que não existe.

`executor_ordem.py` **não mudou** na reestruturação V420-424 (conferido
byte a byte) — a causa provavelmente não está na reestruturação.

**Hipótese principal:** UIPI (User Interface Privilege Isolation) do
Windows. Se o Profit roda como Administrador e o Python não, o Windows
bloqueia **silenciosamente** o envio de teclas sintéticas entre os
dois — `keybd_event()` não gera erro, mas a tecla nunca chega.

**O que foi adicionado:** `FocoProfit.diagnosticar()`, chamado a cada
tentativa de envio — mostra o título exato da janela encontrada, PID e
status de elevação (Administrador) dos dois processos. Se forem
diferentes, avisa a causa suspeita e a solução diretamente.

**Ainda sem confirmação da causa raiz** — aguardando novo log com esse
diagnóstico ativo.

Arquivos alterados: `executor_ordem.py`, `versionamento.py`.

---

## V424 — checagem de mercado ainda não aberto + versionamento separado

### Correção: mensagem de encerramento indevida antes da abertura

Reportado em produção: às 08:34 de 23/09/2026, o robô emitiu "Mercado
encerrado por hoje" logo ao iniciar. Causa: o DDE ainda mostrava o
último horário de **ontem** (18:24:59) porque o leilão de abertura de
hoje ainda não tinha gerado tick novo. A checagem de encerramento
comparava só a hora (não a data) contra `HORARIO_LIMITE_ABSOLUTO`, e
"18:24" de ontem passou como "depois das 18:20" de hoje.

Corrigido: nova checagem, antes da de encerramento, compara a **data**
informada pelo DDE contra o relógio real do computador (só fora do modo
Replay, onde isso é esperado). Se a data do DDE estiver atrasada, o robô
narra **"Bom dia! Aguardando abertura do mercado."** e não processa o
dado velho — em vez de declarar o mercado encerrado.

### Versionamento separado de `configuracao.py`

O changelog técnico (200+ linhas de comentário) foi extraído para um
arquivo próprio, `versionamento.py` — `configuracao.py` caiu de ~317
para 109 linhas. `cfg.VERSAO` continua funcionando exatamente igual em
todo o resto do projeto (reexportado via `from versionamento import
VERSAO`), nenhum outro arquivo precisou mudar.

Arquivos alterados: `principal.py`, `configuracao.py`.
Arquivo novo: `versionamento.py`.

---

## V423 — titular destacada em azul celeste na classificação

- A linha da estratégia titular (identificada automaticamente pela pasta
  `estrategia/`, mesma regra de sempre) aparece agora em **azul celeste**
  na tabela de classificação — independente da posição no ranking. A cor
  da titular tem prioridade sobre verde (1º lugar) e vermelho (último).
- Removido o sufixo de texto " [TITULAR]" do nome exibido — agora
  redundante com a cor. O CSV ganha uma coluna `titular` (True/False) em
  vez do sufixo embutido no nome da estratégia.

Arquivos alterados: `classificacao.py`, `configuracao.py` e `changelog.md`.

---

## V422 — classificação compacta no Prompt

- A tabela passou a ocupar no máximo 120 caracteres por linha.
- O espaço entre colunas foi reduzido para um caractere.
- Nomes de estratégias maiores que a coluna são abreviados apenas na tela;
  o nome completo e todas as métricas continuam preservados no CSV.
- Corrigida a quebra que colocava a coluna `multi` e seus valores em uma
  segunda linha.

Arquivos alterados: `classificacao.py`, `configuracao.py` e `changelog.md`.

---

## V421 — classificação histórica simplificada

- `classificacao.py` passou a alimentar diretamente o `MotorRobonildo` com os
  candles históricos e continua produzindo o ranking multitemporal.
- O arquivo intermediário `laboratorio.py` tornou-se desnecessário e pode ser
  excluído depois da instalação destes arquivos.
- A pasta `laboratorio/estrategias` foi mantida como local dos cartuchos que
  participam da competição.
- Não houve alteração em `motor.py`, `principal.py` nem na estratégia V19.

Arquivos alterados: `classificacao.py`, `configuracao.py` e `changelog.md`.

---

## V420 — console único para jogo ao vivo e gravado

- Criado `motor.py` como fonte única de indicadores, interpretação do cartucho,
  stop/alvo, limites diários, posição, encerramento e contabilização.
- `principal.py` alimenta esse motor com eventos do DDE e prioriza decisões e
  ordens antes de encaminhar as notícias pendentes para a apresentação.
- Criado `laboratorio.py`, que alimenta o mesmo `MotorRobonildo` com candles
  históricos em ordem cronológica. Ele não contém uma segunda estratégia nem
  um segundo gestor de risco.
- Criado `classificacao.py` apenas para descobrir cartuchos, executar cada um
  pelo laboratório e calcular a classificação multitemporal da V419.
- Removido o teste de paridade entre produção e laboratório: ambos agora
  instanciam a mesma classe concreta, portanto não há dois motores a comparar.
- A antiga auditoria de paridade do DDE foi corretamente renomeada para
  `auditor_execucao.py`; ela registra execução observada e não compara motores.
- `noticias.py` permanece independente. As notícias entram em fila e só são
  apresentadas depois do processamento operacional do ciclo.
- Tornam-se obsoletos após a instalação completa: `estrategia/_nucleo.py`,
  `gestor_risco.py`, `laboratorio_integrado.py` e `auditor_paridade.py`.

Arquivos novos ou alterados: `motor.py`, `principal.py`, `laboratorio.py`,
`classificacao.py`, `configuracao.py`, `construtor_candle.py`, `registrador.py`,
`auditor_execucao.py` e `changelog.md`.

---

## V419 — classificação multitemporal e paridade opcional

### Classificação multitemporal

- A classificação oficial passa a combinar três horizontes: 50% histórico
  longo, 30% mensal e 20% diário.
- As notas de cada horizonte são normalizadas de 0 a 100 entre as estratégias,
  preservando empates.
- A nota mensal combina média, mediana e percentil 25 dos meses. A nota diária
  combina média, mediana e percentil 25 dos pregões, incluindo dias sem trade.
- Quando o arquivo não sustenta um horizonte, os pesos são redistribuídos
  somente entre os horizontes válidos. Um arquivo de um pregão recebe apenas
  nota diária e é identificado como classificação provisória de confiança
  muito baixa.
- Arquivos com menos de 66 candles usam os 65 candles imediatamente anteriores
  do histórico persistente somente para aquecer os indicadores. Esses candles
  não geram operações nem entram na pontuação do período avaliado. Se o
  aquecimento não estiver disponível, o laboratório interrompe com mensagem
  explícita em vez de produzir uma classificação falsa.
- O CSV completo passa a ser `logs/classificacao_integrada_v419.csv` e conserva
  também a pontuação robusta anterior para auditoria.

### Paridade

- O teste continua implementado, mas fica desligado por padrão por meio de
  `LAB_EXECUTAR_PARIDADE = False`, reduzindo o tempo das apurações.
- Para uma auditoria formal, basta alterar temporariamente a opção para `True`.

### Arquivos alterados

- `laboratorio_integrado.py`
- `configuracao.py`
- `changelog.md`

---

## V418 — validação defensiva do sinal e consistência da versão

### Correções

- `calcular_stop_alvo()` agora aceita exclusivamente `1` (COMPRA) ou `-1`
  (VENDA). Qualquer outro valor gera `ValueError`, interrompe a avaliação do
  sinal e impede que um retorno inválido seja interpretado silenciosamente
  como VENDA.
- O laboratório integrado, o título da classificação, o nome do CSV e a
  seção correspondente de `configuracao.py` foram atualizados para V418.
- As frases de contexto recuperaram a ortografia correta: “favorável à
  alta/baixa”, “distância da média” e “estratégia do laboratório, por meio da
  ponte genérica”.

### Preservado da V417

- Produção e laboratório continuam usando o retorno real de
  `gerar_sinal(row)` para definir COMPRA/VENDA.
- A escolha inicial continua restrita a L, R ou N, sem queda silenciosa para
  o modo NORMAL.
- A estratégia titular V19 e seus parâmetros não foram alterados.

### Arquivos alterados

- `estrategia/_nucleo.py`
- `laboratorio_integrado.py`
- `configuracao.py`
- `changelog.md`

---

## V417 — correção do bug de direção (COMPRA/VENDA) e trava da pergunta inicial

**Motivado por:** Relatorio_proposta_melhoria_laboratorio_Robonildo.docx,
revisão do conselho sobre a V416.

### O bug

`calcular_stop_alvo()` (em `estrategia/_nucleo.py`) e seus dois chamadores
(a ponte de produção `avaliar_candle_via_gerar_sinal`, e
`_sinal_integrado` no laboratório integrado) decidiam COMPRA/VENDA usando
`row['trend']`, **não** o retorno real de `gerar_sinal(row)`. Funcionava
até aqui só por coincidência: toda estratégia titular já testada retorna
sinal apenas quando concorda com a tendência — mas isso nunca foi uma
garantia do motor. Uma estratégia contrária à tendência (ou um bug numa
estratégia futura) executaria no lado errado, silenciosamente, sem erro
nenhum.

### A correção

`calcular_stop_alvo()` passou a receber o sinal real da estratégia
(`sinal_bruto`/`bruto`, 1 ou -1) em vez de `row['trend']`. Corrigido nos
dois chamadores — produção e laboratório usam a mesma fonte agora.

### Validação

- Testado com cenário contrário à tendência: estratégia retorna -1 com
  `trend=+1` — confirma VENDA (correto), não mais COMPRA.
- Regressão: o trade já validado da V19 em 18/09/2026 (venda às 14:15,
  entrada 186.570) reproduz idêntico após a correção.

### Segunda correção nesta versão

A pergunta inicial (LABORATÓRIO/REPLAY/NORMAL) aceitava qualquer resposta
que não fosse L ou R como NORMAL silenciosamente — um erro de digitação
colocava o robô em modo real, com ordens de verdade, sem avisar. Agora
insiste até receber exatamente L, R ou N.

---

## V416 — prioridade operacional e narração confirmada

### Objetivo

Eliminar a separação entre o motor de classificação e o motor operacional.
A estratégia titular continua sendo a V19; nenhuma porta foi modificada.

### Mudanças

- A pergunta inicial agora aceita `L`, `R` ou `N`.
- O modo `L` executa `laboratorio_integrado.py` sem conectar ao DDE e sem
  enviar ordens.
- Indicadores, bloqueios de horário, stop, alvo, custos e limites diários vêm
  dos mesmos arquivos usados pelo Robonildo.
- A estratégia titular é carregada diretamente de `estrategia/`.
- Estratégias candidatas ficam em `laboratorio/estrategias/`, com leitura
  temporária da pasta legada durante a migração.
- Antes do ranking, a estratégia titular passa por comparação candle a candle
  contra a ponte oficial do Robonildo. Qualquer divergência cancela o ranking.
- A classificação utiliza janelas móveis de pregões e ordena pelo percentil 25
  das pontuações, reduzindo a influência de um único período favorável.
- O relatório completo é salvo em
  `logs/classificacao_integrada_v416.csv`.
- A leitura do CSV mostra percentual e quantidade de candles válidos.
- O cálculo dos indicadores, a auditoria de paridade e a execução das
  estratégias agora exibem progresso no terminal.
- A classificação no terminal recupera a apresentação familiar do laboratório:
  resultado, diária, dias operados, aproveitamento, drawdown, capital mínimo e
  pontuação. A ordenação robusta da V415 foi preservada na V416.

### Narração operacional da V416

- Cenários do candle ainda em formação permanecem visíveis no terminal, mas
  não são mais narrados em voz alta.
- O aviso sonoro dos segundos finais foi preservado.
- Depois do fechamento, o robô calcula o sinal e envia a ordem ao Profit antes
  de iniciar qualquer narração operacional.
- A voz passou a relatar somente fatos concluídos e no passado, por exemplo:
  “A ordem de compra foi enviada após a confirmação do candle.”
- Quando não há entrada, a narração informa a tendência confirmada do candle e
  que nenhum sinal foi confirmado.
- A estratégia titular V19 e suas três portas não foram modificadas.

### Limitação preservada com transparência

Um CSV de 15 minutos não informa a ordem dos preços dentro do candle. Se stop
e alvo forem tocados no mesmo OHLC, a V416 aplica a mesma precedência
conservadora do Robonildo: stop antes do alvo, e registra a ambiguidade. O
preço exato do corte das 18:20 também não pode ser reconstruído sem ticks.

### Arquivos alterados ou adicionados

- `principal.py`
- `configuracao.py`
- `laboratorio_integrado.py`
- `changelog.md`
