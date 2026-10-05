"""
ROBONILDO - versionamento.py

Controle de versao e changelog tecnico detalhado do projeto, separado de
configuracao.py (que ficava poluido com 200+ linhas de comentario aqui).

VERSAO e a fonte unica de verdade, usada por todo o projeto via
'from versionamento import VERSAO' (configuracao.py reexporta para manter
cfg.VERSAO funcionando sem precisar mudar nenhum outro arquivo).

changelog.md tem o registro legivel/resumido para o conselho. Este arquivo
guarda o historico tecnico linha a linha, mais detalhado, indexado por
versao - util para arqueologia de codigo ("em que versao isso mudou?").
"""

# Fonte unica de verdade — sempre no topo deste arquivo.
VERSAO = "V482"

# ---------------------------------------------------------------------------
# Historico tecnico por versao (blocos separados; mais recente no final)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# V200 — integracao inicial
# ---------------------------------------------------------------------------
# estrategia + risco + candle + registro + DDE

# ---------------------------------------------------------------------------
# V201 — sincronizacao e executor
# ---------------------------------------------------------------------------
# correcoes de sincronizacao de horario, deduplicacao de historico,
# protecao contra dado futuro + executor_ordem.py

# ---------------------------------------------------------------------------
# V202 — stop/alvo tick a tick
# ---------------------------------------------------------------------------
# stop/alvo verificados tick a tick (nao mais so no fechamento do candle
# de 15min) — reacao imediata, nao atrasada

# ---------------------------------------------------------------------------
# V203 — MA_STOCH_DIRECAO_v1
# ---------------------------------------------------------------------------
# ESTRATEGIA PROMOVIDA: MA_v2 -> MA_STOCH_DIRECAO_v1
# (toque na MA21 + Estocastico Lento(8,3) na mesma direcao da tendencia),
# validada no laboratorio_estrategias em 12 meses

# ---------------------------------------------------------------------------
# V400 — pasta padronizada + ponte generica + Manus_4_Portas_V11
# ---------------------------------------------------------------------------
# pasta padronizada: D:\DAYTRADE\ROBONILDO, sem sufixo de versao no nome
# (evita confusao entre "versao da pasta" e "versao da estrategia";
# a VERSAO acima e a fonte unica de verdade).
# Ponte generica no _nucleo.py (avaliar_candle_via_gerar_sinal +
# construir_row) — qualquer estrategia do laboratorio_estrategias
# (gerar_sinal(row)) roda em producao sem traducao manual.
# ESTRATEGIA PROMOVIDA: Manus_4_Portas_V11 (validada em 21 meses de
# historico, Minimo Comparado 4.01/5.37, capital minimo real
# R$2.156,73 — NAO R$515,19, numero da janela de 12 meses testada antes).
# Narracao/contador de proximidade (principal.py) tambem passou a chamar
# avaliar_candle() de forma especulativa no candle em formacao, em vez de
# reimplementar a logica de entrada a parte — antes so cobria a Porta 1 da
# estrategia de 4 portas, ficando muda quando o sinal vinha das Portas 2/3/4.

# ---------------------------------------------------------------------------
# V401 — VERSAO obrigatoria a cada entrega + composta_v18 + RSI/ATR
# ---------------------------------------------------------------------------
# a partir daqui, TODA implementacao incrementa a VERSAO (combinado com o
# usuario em 18/09/2026) — impressa com destaque logo no inicio de
# principal.py.
# Mudancas acumuladas desde V400 (nunca versionadas individualmente):
# - ESTRATEGIA PROMOVIDA: chatgpt_composta_v18 (Minimo Comparado 2.69,
#   pontuacao composta 1.116,0 — primeira a romper 1000 pontos)
# - RSI e ATR relativo adicionados a construir_row() em _nucleo.py
# - Narracao de contexto real no sinal via construir_contexto_narracao()
# - Localizacao dinamica do ativo na aba DDE
# - Checagens de integridade do DDE
# - Pergunta REPLAY/NORMAL unificada
# - Corrigido bug de deriva de relogio em replay
# - Print de diagnostico de onde _nucleo.py foi carregado

# ---------------------------------------------------------------------------
# V402 — buraco no replay
# ---------------------------------------------------------------------------
# deteccao de "buraco" no historico quando o replay e pulado/arrastado;
# preenche com dado REAL do arquivo historico

# ---------------------------------------------------------------------------
# V403 — buraco le do CSV original do Profit
# ---------------------------------------------------------------------------
# corrigido preenchimento que lia o persistente (mesmo buraco); passa a ler
# CAMINHO_HISTORICO_INICIAL

# ---------------------------------------------------------------------------
# V404 — paridade OHLC no Replay
# ---------------------------------------------------------------------------
# cada candle fechado usa OHLC consolidado da exportacao do Profit apos o
# termino do periodo

# ---------------------------------------------------------------------------
# V405 — RR = 1,55
# ---------------------------------------------------------------------------
# relacao risco/retorno alinhada ao motor oficial (MIN_RR=1.55)

# ---------------------------------------------------------------------------
# V406 — V19 titular + ordem so apos envio confirmado
# ---------------------------------------------------------------------------
# ESTRATEGIA PROMOVIDA: chatgpt_3_portas_robusta_v19
# Corrigido AttachThreadInput erro 87; estado interno so atualiza DEPOIS
# de confirmar envio da ordem (evita posicao fantasma)

# ---------------------------------------------------------------------------
# V407 — dedup provisoria do historico
# ---------------------------------------------------------------------------
# politica provisoria: nao gravar horario ja existente

# ---------------------------------------------------------------------------
# V408 — UPSERT atomico + terminal rico
# ---------------------------------------------------------------------------
# substitui politica provisoria por UPSERT atomico por horario;
# terminal com indicadores e gradiente de sinal

# ---------------------------------------------------------------------------
# V413 — gradiente continuo da posicao aberta
# ---------------------------------------------------------------------------
# progresso -1..+1 com narracao de % ate alvo/stop

# ---------------------------------------------------------------------------
# V414 — resultado liquido unico (custo descontado)
# ---------------------------------------------------------------------------
# cor/narracao/terminal usam a mesma funcao com custo descontado;
# interpolacao RGB continua

# ---------------------------------------------------------------------------
# V415 — laboratorio integrado
# ---------------------------------------------------------------------------
# modo L usa os mesmos parametros de risco/custos/horarios do console

# ---------------------------------------------------------------------------
# V416 — narracao apos ordem
# ---------------------------------------------------------------------------
# ordens e saidas tem prioridade absoluta; voz so apos fatos concluidos

# ---------------------------------------------------------------------------
# V417 — bug de direcao (sinal real, nao trend)
# ---------------------------------------------------------------------------
# calcular_stop_alvo usa retorno de gerar_sinal(row), nao row['trend'];
# pergunta inicial insiste em L/R/N

# ---------------------------------------------------------------------------
# V418 — validacao defensiva do sinal
# ---------------------------------------------------------------------------
# somente 1 e -1 chegam ao stop/alvo; resto gera erro explicito

# ---------------------------------------------------------------------------
# V419 — classificacao multitemporal
# ---------------------------------------------------------------------------
# 50% longo + 30% mensal + 20% diario; pesos redistribuidos se faltar horizonte

# ---------------------------------------------------------------------------
# V420 — console unico (motor.py)
# ---------------------------------------------------------------------------
# motor.py concentra indicadores, cartucho, stop/alvo, limites e posicao;
# principal e classificacao so alimentam o motor

# ---------------------------------------------------------------------------
# V421 — classificacao alimenta o motor direto
# ---------------------------------------------------------------------------
# laboratorio.py removido; laboratorio/estrategias permanece como deposito

# ---------------------------------------------------------------------------
# V422 — tabela compacta (120 colunas)
# ---------------------------------------------------------------------------
# um espaco entre colunas; nomes longos abreviados so na tela

# ---------------------------------------------------------------------------
# V423 — titular em azul celeste
# ---------------------------------------------------------------------------
# linha da titular destacada; coluna titular no CSV (True/False)

# ---------------------------------------------------------------------------
# V424 — mercado ainda nao aberto + versionamento.py
# ---------------------------------------------------------------------------
# DDE com data de ontem nao dispara mais "Mercado encerrado";
# narra "Bom dia! Aguardando abertura do mercado.";
# changelog tecnico extraido para este arquivo

# ---------------------------------------------------------------------------
# V425 — diagnostico de ordem que nao chega ao Profit
# ---------------------------------------------------------------------------
# hipotese UIPI; FocoProfit.diagnosticar() com PID e elevacao

# ---------------------------------------------------------------------------
# V426 — cooldown de avisos DDE
# ---------------------------------------------------------------------------
# mesmo aviso (preco parado / deriva) no maximo a cada 60s

# ---------------------------------------------------------------------------
# V427 — e-mail em abertura/fechamento (opt-in)
# ---------------------------------------------------------------------------
# email_notificacao.py em thread; nunca bloqueia ordem

# ---------------------------------------------------------------------------
# V428 — fim de pregao encerra o script
# ---------------------------------------------------------------------------
# as 18:20: ALT+Z de seguranca + "Finalizado." + processo termina

# ---------------------------------------------------------------------------
# V429 — dois cartuchos independentes (entrada / saida)
# ---------------------------------------------------------------------------
# estrategia/entrada/ — exatamente 1 arquivo, gerar_sinal(row)
# estrategia/saida/   — exatamente 1 arquivo, avaliar_saida(row, posicao)->bool
# saida_claude_v1.py = baseline (sempre False = comportamento RR=1,55 atual)
# motor: Posicao com candles_decorridos, maxima/minima_desde_entrada;
# verificar_saida: (1) stop/alvo motor (2) cartucho saida so antecipa
# (3) corte horario; excecao no cartucho nao derruba o motor;
# posicao publica SEM motivo_entrada (evita acoplamento entrada/saida);
# classificacao pareia toda entrada candidata com a saida titular;
# regressao: 18/09 14:15 identico; 0 SAIDA_CARTUCHO espurio no baseline

# ---------------------------------------------------------------------------
# V430 — inventario explicito de cartuchos no laboratorio
# ---------------------------------------------------------------------------
# classificacao.py:
# - listar_cartuchos_disco() / imprimir_inventario_cartuchos()
# - lista no terminal o conteudo de estrategia/entrada/, estrategia/saida/
#   e da pasta do laboratorio antes da apuracao
# - mensagens de erro de "exatamente 1 arquivo" incluem os nomes achados
# - cabecalho do lab mostra entrada titular, saida titular e nomes do ranking
# Nao altera regras de ranking nem o motor — so transparencia operacional
# (V429 ja tinha a descoberta dos dois slots; V430 torna o inventario visivel).

# ---------------------------------------------------------------------------
# V431 — titulares em subpasta titular/; fim do laboratorio
# ---------------------------------------------------------------------------
# Nova arvore oficial (laboratorio/estrategias removido do projeto):
#   estrategia/entrada/titular/  → exatamente 1 .py (entrada de producao)
#   estrategia/entrada/*.py      → candidatas de ranking de ENTRADA
#   estrategia/saida/titular/    → exatamente 1 .py (saida de producao)
#   estrategia/saida/*.py        → candidatas de ranking de SAIDA (futuro)
# classificacao.py:
# - deixa de ler PASTA_ESTRATEGIAS_LABORATORIO e legado
# - descobrir_estrategias() usa entrada/titular + entrada/*.py
# - descobrir_cartucho_saida() usa saida/titular/
# - inventario no terminal reflete a nova arvore
# principal.py (producao) deve usar a mesma regra de descoberta nos
# caminhos estrategia/entrada/titular e estrategia/saida/titular.

# ---------------------------------------------------------------------------
# V432 — ranking triplo: entrada / saída / cruzado (principal)
# ---------------------------------------------------------------------------
# classificacao.py:
# - descobre entradas (titular + candidatas) e saídas (titular + candidatas)
#   de forma independente
# - Ranking ENTRADA: cada entrada × saída titular
# - Ranking SAÍDA: cada saída × entrada titular
# - Ranking PRINCIPAL (cruzado): todas as combinações entrada × saída
#   colunas: pos, entrada, saída, resultado, diária, dias, drawdown, pontuação
# - CSVs: classificacao_entrada_*, classificacao_saida_*, classificacao_cruzada_*
# principal.py já carrega só estrategia/*/titular/ (V431)
# motor.py já aceita gerar_sinal e avaliar_saida independentes (V429)

# ---------------------------------------------------------------------------
# V433 — multi ABSOLUTO individual (fim do percentil entre concorrentes)
# ---------------------------------------------------------------------------
# classificacao.py — aplicar_pontuacao_multitemporal:
# - ANTES: multi = percentil 0-100 de cada horizonte entre as estratégias
#   da rodada (nota relativa — mudava se o conjunto de concorrentes mudasse)
# - AGORA: multi = média ponderada dos scores BRUTOS individuais
#   50% score_longo_raw + 30% score_mensal_raw + 20% score_diario_raw
#   (pesos redistribuídos se faltar horizonte)
# Motivo: um colega que testa UMA estratégia isolada precisa obter o MESMO
# multi que obteria aqui no arsenal completo — comparável por valor.
# _normalizar_percentil removido do caminho do multi (permanece _percentil_25
# só dentro de robustez/horizontes, como estatística de janela, não de rank).

# ---------------------------------------------------------------------------
# V434 — cartucho de saida "v1" renomeado para baseline.py
# ---------------------------------------------------------------------------
# RENUMERADO: esta mudanca tinha sido entregue como "V433" numa sessao em
# paralelo com a mudanca de pontuacao absoluta (tambem chamada V433, acima) -
# as duas reivindicaram o mesmo numero ao mesmo tempo. A pontuacao absoluta
# ficou com V433 (ja estava no versionamento.py recebido); este rename
# passa a V434.
#
# saida_claude_v1.py -> baseline.py, mesma pasta (estrategia/saida/titular/),
# mesmo conteudo (avaliar_saida sempre False). Nome reflete melhor o papel
# dele: referencia fixa a ser superada, nao uma candidata numerada na
# sequencia v1/v2/v3. Descoberta e puramente por pasta (exatamente 1
# arquivo), entao a troca de nome nao exigiu nenhuma mudanca de codigo em
# principal.py nem classificacao.py.
#
# Validado RODANDO OS DOIS JUNTOS (V433 pontuacao absoluta + V434 rename):
# pipeline completo (classificacao.executar) com o dataset oficial - 176
# operacoes / R$15.966,98 na titular (chatgpt_3_portas_robusta_v19 x
# baseline), identico a toda validacao anterior. Inventario mostra
# "baseline [TITULAR]" corretamente. Sem conflito de codigo entre as duas
# mudancas - so o numero de versao colidiu.

# ---------------------------------------------------------------------------
# V435 — saída candidata por retenção de lucro + credencial fora do código
# ---------------------------------------------------------------------------
# Novo cartucho candidato estrategia/saida/saida_chatgpt_v1.py:
# - não altera a baseline titular nem a produção antes de promoção explícita;
# - stop/alvo do motor continuam com prioridade absoluta;
# - trailing só arma após MFE relevante (pontos + ATR);
# - saída exige devolução da MFE e confirmação adversa por RSI/Estocástico/MACD,
#   com trava de emergência para devolução excepcional;
# - posição lucrativa é realizada no fechamento rotulado 17:45 (execução
#   aproximada às 18:00 no histórico), criando margem antes do corte 18:20.
# configuracao.py deixa de conter senha de aplicativo em texto puro e passa a
# ler ROBONILDO_EMAIL_SENHA_APP do ambiente. email_notificacao.py ignora o
# envio com aviso claro quando a variável não estiver definida.

# ---------------------------------------------------------------------------
# V436 — CORRIGIDA REGRESSAO: integracao de e-mail sumida do principal.py
# ---------------------------------------------------------------------------
# Reportado: e-mail nao foi enviado na abertura de uma ordem real, mesmo com
# EMAIL_NOTIFICACAO_ATIVO=True e a senha de app configurada corretamente
# (ja confirmado funcionando via teste_email.py isolado).
#
# CAUSA RAIZ: o principal.py em uso NAO TINHA NENHUMA referencia a
# email_notificacao - nem o import, nem as 4 chamadas (1 abertura + 3
# fechamento) que foram implementadas originalmente na V427. A integracao
# foi perdida em algum ponto entre V427 e a reestruturacao grande de
# entrada/saida (V429+), que reescreveu boa parte do arquivo sem carregar
# essa parte junto - uma regressao silenciosa, sem erro nenhum no log
# (o codigo simplesmente nunca chamava a funcao, entao nunca havia nada
# pra falhar ou avisar).
#
# CORRIGIDO: reinserido o import (`import email_notificacao`) e as 4
# chamadas, nos mesmos 4 pontos de sempre (logo apos
# registrador.registrar_operacao_aberta/fechada, mesma posicao relativa
# da V427), adaptadas a estrutura atual do arquivo (que mudou bastante
# desde entao). Nenhuma outra logica alterada.
#
# LICAO: ao revisar reestruturacoes grandes do principal.py dai em diante,
# checar explicitamente que toda integracao anterior (narracao, auditoria,
# registrador, email) sobreviveu - "sintaxe valida + roda sem erro" nao
# detecta uma chamada que simplesmente deixou de existir.

# ---------------------------------------------------------------------------
# V437 — saida_grok_v6 candidata: trava de lucro no fim do pregão
# ---------------------------------------------------------------------------
# Cartucho candidato (NÃO titular): estrategia/saida/saida_grok_v6.py
# Regra: após 17:30, se resultado_flutuante_pts >= 1,0 × ATR → True
# (antecipa só lucro; stop/alvo do motor continuam prioritários).
#
# Backtest isolado (V19 × saídas, jun–set/2026, mesmo MotorRobonildo):
#   baseline (sempre False): R$ 6.809,63 | DD -249,48 | PF 4,75 | score 622,9
#   saida_grok_v6:           R$ 6.974,73 | DD -249,48 | PF 5,01 | score 673,5
#   Δ +R$ 165,09 | DD igual | stops 14→13
# Grade hora×ATR: melhor combinação 17:30 + 1,0 ATR; vizinhas 17:30/0,8 e
# 17:45/0,8 também bateram a baseline. Tentativas anteriores (giveback,
# Fibonacci, MA21 break, scratch no zero) NÃO superaram a baseline.
#
# Promoção a titular só após ranking de saída + cruzado em classificacao.py.
# Arquivo novo: saida_grok_v6.py (candidata em estrategia/saida/).

# ---------------------------------------------------------------------------
# V438 — classificacao.py pergunta qual ranking rodar (E / S / C)
# ---------------------------------------------------------------------------
# Ao iniciar classificacao.py (ou modo L do principal), pergunta:
#   E = ranking de entradas (cada entrada × saída titular)
#   S = ranking de saídas   (entrada titular × cada saída)
#   C = ranking cruzado     (produto cartesiano — ranking principal)
# Só executa as combinações do modo escolhido (evita cartesian completo
# quando só se quer E ou S). Imprime e grava CSV só do ranking pedido.
# Arquivo alterado: classificacao.py.


# ---------------------------------------------------------------------------
# V439 — remocao do modo LABORATORIO (L) do prompt de principal.py
# ---------------------------------------------------------------------------
# Pedido anteriormente (mesma sessao), mas nao tinha persistido no arquivo
# que chegou como V438 - reaplicado aqui. Prompt volta a ser so REPLAY/NORMAL
# (R/N); o modo L chamava classificacao.executar() e saia - redundante desde
# que classificacao.py ganhou vida propria (e agora, com a V438, ate pergunta
# qual ranking rodar sozinho). Rodar o laboratorio agora e sempre
# "python classificacao.py" direto, nunca mais via principal.py.
#
# Revisao completa desta rodada (sincronizacao de 15 arquivos recebidos):
#   - V436 (integracao de e-mail): confirmada presente e intacta.
#   - V437 (saida_grok_v6.py, candidata de saida): registrada no historico,
#     mas o ARQUIVO em si nao foi enviado nesta rodada - ainda pendente de
#     revisao real (nao posso validar backtest que nao tenho em maos).
#   - V438 (classificacao.py pergunta E/S/C): testada de ponta a ponta com
#     o dataset oficial, escolhendo "E" - confirmado que roda so as 4
#     combinacoes de entrada (nao as 12 do cruzado completo), resultado
#     identico a toda validacao anterior (176 ops/R$15.966,98 na titular).

# ---------------------------------------------------------------------------
# V440 — narracao enriquecida do lado da SAIDA (espelha o que ja existia so
#        na entrada)
# ---------------------------------------------------------------------------
# Ate aqui, "[CENARIO EM FORMACAO]" so existia para a ENTRADA (chama
# diagnosticar_sinal especulativamente, no candle ainda formando, avisa
# antes de fechar de verdade). Do lado da saida so havia a narracao de
# progresso motor-level ("X% do caminho ate o alvo/stop") - nunca avisava
# quando o CARTUCHO DE SAIDA especificamente estava prestes a antecipar o
# fechamento.
#
# Duas adicoes, mesmo espirito da entrada:
#
# 1. AVISO ESPECULATIVO (com posicao aberta, candle ainda formando): chama
#    avaliar_saida() do cartucho titular com o preco/hora atuais (ainda nao
#    fechados). Se ja fecharia com o dado de agora, narra
#    "[CENARIO EM FORMACAO] <explicacao real, via diagnosticar_saida se
#    disponivel>" - ANTES do candle fechar de verdade. Deduplicado por
#    (candle, horario_entrada) para nao repetir a cada iteracao do loop.
#    Excecao no cartucho nunca trava a narracao - so nao avisa nada.
#
# 2. FECHAMENTO REAL explicado: quando o motivo do fechamento e
#    "SAIDA_CARTUCHO", a narracao de fechamento agora tenta usar
#    diagnosticar_saida() do cartucho para explicar o motivo REAL (ex: "lucro
#    de X pontos, MACD virou contra"), em vez de so cair na frase generica de
#    lucro/prejuizo. Se diagnosticar_saida nao existir, lancar excecao, ou
#    nao devolver string, cai no fallback generico normalmente - sem quebrar
#    nada.
#
# Testado isoladamente (sem loop completo, que depende de DDE ao vivo): 3
# cenarios - especulativo nao dispara com lucro baixo, dispara com explicacao
# real quando lucro alto, e cartucho quebrado nunca trava (cai em None/
# generico). Os 3 se comportaram como esperado.
#
# Arquivo alterado: principal.py.

# ---------------------------------------------------------------------------
# V448 — estratégias isoladas + radar de oportunidades
# ---------------------------------------------------------------------------
# As três antigas portas da entrada titular Grok foram extraídas como
# estratégias candidatas independentes: Retomada MA21, MACD + Estocástico e
# Saída de Extremo. O agregador titular mantém exatamente os mesmos limiares
# e a prioridade histórica 1 -> 2 -> 3, portanto esta etapa não ativa troca
# dinâmica de ordens nem altera deliberadamente o comportamento operacional.
#
# Novo contrato opcional diagnosticar_oportunidades(row): cada estratégia
# informa nome, direção, condições confirmadas, total, faltantes, progresso e
# sinal. MotorRobonildo valida e ordena esse radar; cartuchos antigos seguem
# compatíveis e apenas não oferecem telemetria detalhada.
#
# principal.py passa a exibir a estratégia mais avançada, X/Y confirmações e
# a próxima condição faltante. O quadrado usa o progresso técnico de 0% a
# 100%, não o tempo restante do candle. A narração avisa quando uma estratégia
# ultrapassa 70%, sem prometer entrada. Com posição aberta, a linha principal
# mostra entrada, preço atual, resultado, alvo, stop e distâncias.
#
# Arquivos novos: entrada_retomada_ma21_grok_v1.py,
# entrada_macd_estocastico_grok_v1.py e entrada_saida_extremo_grok_v1.py.
# Arquivos alterados: motor.py, principal.py, entrada_grok_3_v1.py,
# compliance.md, versionamento.py e changelog.md.

# ---------------------------------------------------------------------------
# V449 — linha de posição compacta sem quebra no Prompt
# ---------------------------------------------------------------------------
# Ajuste exclusivamente visual em principal.py. A linha de posição aberta
# abrevia distâncias entre parênteses e remove rótulos redundantes, mantendo
# em uma linha: lado, entrada, preço atual, resultado, alvo, stop e progresso.
# Nenhuma regra de entrada, saída, risco, radar ou envio de ordem foi alterada.

# ---------------------------------------------------------------------------
# V450 — grade da posição alinhada e resultado sem prefixo monetário
# ---------------------------------------------------------------------------
# Ajuste exclusivamente visual em principal.py. Lado, entrada, preço atual,
# resultado, alvo, stop, distâncias e percentual passam a ocupar campos de
# largura fixa, evitando deslocamento das colunas quando os números crescem.
# O prefixo "R$" foi removido e os separadores ganharam espaçamento. Nenhuma
# regra operacional foi alterada.

# ---------------------------------------------------------------------------
# V451 — grade do radar alinhada
# ---------------------------------------------------------------------------
# Ajuste exclusivamente visual em principal.py. Preço, tendência, estratégia,
# confirmações, condição faltante e quadrado passam a ocupar colunas estáveis.
# A condição faltante usa largura fixa para impedir que o quadrado se desloque
# quando a estratégia prioritária muda. Nenhuma regra operacional foi alterada.

# ---------------------------------------------------------------------------
# V452 — caminhos locais e portáveis por instalação
# ---------------------------------------------------------------------------
# configuracao.py passa a derivar a raiz do projeto de __file__. Histórico
# persistente, estado de risco, auditoria, registros e relatórios ficam na
# pasta logs da instalação efetivamente executada, sem referência absoluta à
# antiga D:\DAYTRADE\ROBONILDO. principal.py fornece explicitamente esses
# caminhos ao motor e ao registrador. Nenhuma regra de negociação foi alterada.

# ---------------------------------------------------------------------------
# V453 — candidato de orquestração dinâmica de entradas
# ---------------------------------------------------------------------------
# Novo cartucho entrada_orquestrador_dinamico_v1.py descobre automaticamente
# todos os cartuchos de entrada que oferecem gerar_sinal(row) e
# diagnosticar_oportunidades(row), normaliza prontidão/aderência/confiança e
# escolhe a oportunidade de maior score no contexto corrente. Conflitos de
# direção com scores praticamente empatados bloqueiam a entrada. O cartucho
# entra no ranking oficial como CANDIDATO; não substitui o titular sem vencer
# backtest no mesmo motor. Nenhuma informação futura ou ranking salvo é lido.

# ---------------------------------------------------------------------------
# V441 — [CENARIO EM FORMACAO] agora e FALADO, nao so impresso no log
# ---------------------------------------------------------------------------
# Ate a V440, todo "[CENARIO EM FORMACAO]" (entrada especulativa, expectativa
# perdida, saida especulativa, progresso periodico com/sem posicao) so
# aparecia no terminal via print() - a decisao original da V416 foi
# deliberada ("a voz so relata fatos depois do candle confirmado, nunca
# concorre com o envio de uma ordem"), mas o dono do laboratorio pediu para
# reverter isso: esses cenarios devem ser narrados tambem, nao so
# apresentados no log.
#
# Verificado antes de aplicar: narrar() usa SVSFlagAsync=1 (SAPI), ou seja,
# a fala e genuinamente NAO BLOQUEANTE - chamar narrar() no meio do loop
# especulativo nao atrasa nem compete com o envio de ordem em nenhum sentido
# tecnico (a chamada so enfileira a fala e retorna na hora). A preocupacao
# original da V416 era mais sobre nao falar algo que pode nao se confirmar
# do que sobre travamento - o dono do laboratorio decidiu que a narracao do
# cenario em formacao (deixando claro que pode mudar ate o fechamento) vale
# mais que esse risco.
#
# Adicionado narrar() ao lado de cada print() de "[CENARIO EM FORMACAO]"
# (5 pontos): expectativa de entrada identificada, expectativa de entrada
# perdida, saida especulativa identificada (V440), progresso periodico com
# posicao aberta, e frase periodica sem posicao aberta. Nenhuma logica de
# decisao mudou - so a voz passou a acompanhar o que ja aparecia no log.
#
# Arquivo alterado: principal.py.

# ---------------------------------------------------------------------------
# V442 — email_notificacao.py aceita mais de 1 destinatario
# ---------------------------------------------------------------------------
# EMAIL_NOTIFICACAO_DESTINATARIO (configuracao.py) agora aceita 1 ou mais
# e-mails separados por virgula (ex: "voce@gmail.com, socio@gmail.com").
# Nova funcao _lista_destinatarios() faz o parsing (strip de espaco,
# descarta entrada vazia por virgula sobrando), usada tanto no cabecalho
# "To" quanto na lista real de sendmail(). Se a lista vier vazia, avisa e
# nao tenta enviar (mesmo padrao dos outros avisos do modulo - nunca lanca
# excecao pro chamador). Testado com 1 email, varios, espacos extras,
# virgulas duplicadas e string vazia - todos os casos tratados
# corretamente.
#
# Arquivo alterado: email_notificacao.py.

# ---------------------------------------------------------------------------
# V443 — narracao de entrada identifica "porta X de Y" + confirma disparo
# ---------------------------------------------------------------------------
# Pedido: a narracao deveria deixar mais claro a qual porta a expectativa se
# refere. Esclarecido antes de implementar: NAO e um funil sequencial (a
# estrategia checa Porta 1, 2, 3 em ordem, mas so UMA dispara por candle - as
# outras nem chegam a ser avaliadas naquele caso). Implementado de forma
# honesta com essa realidade:
#
# 1. Novo campo OPCIONAL "total_portas" no dict que diagnosticar_sinal()
#    devolve - se presente, principal.py acrescenta "(porta X de Y)" ao final
#    da explicacao narrada. Estrategias que nao expuserem esse campo
#    continuam funcionando exatamente como antes (sem o sufixo).
# 2. Adicionado ao titular atual (grok_3_portas_assimetrica_v2.py):
#    total_portas=3 no helper _resultado().
# 3. Toda narracao de expectativa de entrada agora termina com "Se
#    confirmado no fechamento, a ordem sera disparada." - centralizado em
#    principal.py (nao depende do texto de cada estrategia individual -
#    reparado que o cartucho novo do Grok tinha deixado essa frase de fora,
#    diferente da V19 antiga que a tinha).
#
# Arquivos alterados: principal.py, estrategia/entrada/titular/
# grok_3_portas_assimetrica_v2.py.

# ---------------------------------------------------------------------------
# V445 — motor deixa de ter formula propria de saida (Regra 1 v8 do compliance)
# ---------------------------------------------------------------------------
# Pedido explicito do dono do laboratorio, esclarecido em duas rodadas: a
# estrategia de saida deve ser INTEIRAMENTE do cartucho de saida titular,
# nao do motor - nem como piso de seguranca, nem como "ponto de partida".
#
# motor.py:
# - calcular_stop_alvo() REMOVIDA por completo - o motor nao calcula mais
#   stop nem alvo em nenhum momento.
# - Sinal.stop/alvo e Posicao.stop/alvo agora Optional[float], nascem None.
# - avaliar_row() / avaliar_candle_via_gerar_sinal() derivam lado (COMPRA/
#   VENDA) diretamente do sinal bruto (1/-1) da estrategia de entrada - nao
#   dependem mais de calcular_stop_alvo para isso.
# - abrir_posicao() agora consulta o cartucho de saida titular JA na
#   abertura da posicao (alem de a cada candle fechado, como sempre) -
#   contrato identico ao de avaliar_saida por candle (row + posicao
#   sintetica com candles_decorridos=0), permitindo definir novo_stop/
#   novo_alvo iniciais.
# - verificar_saida() e verificar_saida_continua() tratam pos.stop/pos.alvo
#   como possivelmente None em toda comparacao - sem isso, a primeira
#   posicao sem nivel definido pelo cartucho quebraria com TypeError.
# - Se o cartucho de saida nunca definir nivel nenhum, a posicao fica sem
#   stop/alvo ate o corte de horario do pregao - comportamento esperado,
#   nao uma falha.
#
# Consequencia encontrada ao testar (classificacao.py, dataset oficial):
# baseline.py sempre devolvia False, o que antes significava "aceito o
# RR=1,55 que o motor ja calculou". Sem essa formula em lugar nenhum,
# devolver False sempre virou, silenciosamente, "segurar ate o corte de
# horario" - drawdown medido piorou de -309,19 para -498,39. Corrigido
# reescrevendo baseline.py para calcular, dentro do proprio arquivo, a
# MESMA formula que antes vivia no motor (stop estrutural via
# row["ohlc_recentes"], janela de SWING_LOOKBACK_CANDLES+1 candles, + RR
# 1,55 fixado uma unica vez na abertura, candles_decorridos==0) - validado
# reproduzindo resultado (R$16.585,04 / 175 ops / DD -309,19) e drawdown
# identicos aos de antes da mudanca de contrato, confirmando migracao
# comportamentalmente neutra.
#
# saida_claude_v3.py (candidata anterior, sem stop inicial) tambem sofria
# do mesmo problema - substituida por saida_claude_v4.py, que soma um
# stop inicial (mesma formula do baseline) ao comportamento de breakeven/
# trailing ja existente na v3. Ainda assim nao supera o baseline no
# dataset oficial (R$5.896,31 vs R$16.585,04) - nao promovida.
#
# compliance.md atualizado para Versao 8 (Regra 1 reescrita, Regra 3
# esclarecida contra importar configuracao.py de dentro de um cartucho).
#
# PARTE 2 (mesma versao): motor ORQUESTRA, cartucho so avalia estrategia/
# lucratividade - fechado o circuito na producao (principal.py), que
# ainda nao tinha sido atualizado para o novo contrato do motor:
# - principal.py: abrir_posicao(sinal) passa a ser abrir_posicao(sinal,
#   row=row_fechamento) - sem isso, o motor nunca perguntava ao cartucho
#   de saida o stop/alvo inicial em producao (so no backtest, via
#   classificacao.py, que ja passava row corretamente). O motor e quem
#   decide QUANDO consultar o cartucho; o cartucho so responde com o
#   nivel/decisao, nunca decide por si so quando ser chamado.
# - registrador.registrar_operacao_aberta(sinal) -> recebe a Posicao
#   (gestor.posicao_aberta), nao o Sinal: Sinal.stop/alvo sao sempre None
#   desde que o motor parou de calcula-los, entao gravar o Sinal geraria
#   stop/alvo vazios sempre, mesmo quando o cartucho definiu um nivel
#   real na abertura.
# - email_notificacao.notificar_abertura(sinal, agora) -> recebe a
#   Posicao pelo mesmo motivo. Corrigido tambem o crash certo que isso
#   causaria: sinal.stop/alvo formatados com "{:.2f}" quebravam com
#   TypeError assim que valessem None (SEMPRE, no fluxo antigo). Agora
#   formata "(ainda não definido pelo cartucho de saída)" quando for None
#   - informativo, nao um erro.
# - principal.py (_progresso_posicao e a narracao periodica de posicao
#   aberta): a exibicao ao vivo ("X% do caminho ate o alvo/stop") tambem
#   fazia aritmetica direta com posicao.stop/posicao.alvo - quebraria com
#   TypeError assim que um cartucho (ex: saida_claude_v4, que nunca
#   define alvo) deixasse um dos dois em None. Corrigido: progresso
#   neutro quando o nivel de referencia nao existe, e a narracao passa a
#   dizer "o cartucho de saída ainda não definiu um alvo/stop" em vez de
#   inventar uma porcentagem contra um nivel inexistente.
# Testado isoladamente (sem loop completo, que depende de DDE ao vivo):
# registrar_operacao_aberta, notificar_abertura e o calculo de progresso,
# cada um com posicao COM e SEM stop/alvo definidos - nenhuma excecao em
# nenhum dos dois casos.
#
# PARTE 3 (mesma versao): corte de horario forcado disparava ~1min02s
# ATRASADO. cfg.HORARIO_LIMITE_ABSOLUTO foi alterado em algum momento de
# "18:20" para "18:20:58" (com segundos, de proposito - reduzir a folga
# de risco), mas as duas comparacoes contra esse valor
# (motor.verificar_corte_final - o corte de seguranca de verdade - e o
# aviso de "mercado encerrado" em principal.py) continuaram comparando
# so por MINUTO (strftime("%H:%M")). Como "18:20" < "18:20:58" em ordem
# lexicografica, o corte so disparava as 18:21:00 - o OPOSTO do que a
# mudanca para segundos pretendia. Corrigido para strftime("%H:%M:%S")
# nos dois lugares - agora dispara exatamente as 18:20:58. Removida
# tambem HORARIO_ULTIMO_CANDLE de configuracao.py (sem uso ha varias
# versoes, so criava confusao sobre qual e "o" horario de corte).
# HORARIO_LIMITE_ABSOLUTO e agora, exclusivamente, o unico horario de
# saida forcada do projeto - documentado como tal em configuracao.py.
# HORARIO_BLOQUEIO_NOVAS_ENTRADAS ("18:20") NAO foi tocado: e uma regra
# diferente (bloqueia ABRIR posicao nova, nao forca fechar uma existente)
# e a comparacao por minuto la e proposital e correta.
#
# PARTE 4 (mesma versao): saida_grok_v6.py (titular do ranking de entrada
# que o dono do laboratorio trouxe) promovido a titular ainda no contrato
# antigo (avaliar_saida -> bool, sem nunca definir stop/alvo) - a logica
# original do autor (Grok) sempre assumiu "stop/alvo do motor continuam
# prioritarios", so ANTECIPA um fechamento lucrativo perto do fim do
# pregao. Sob o motor v10 (Regra 1, PARTE 1 acima), que nao calcula mais
# nenhum stop/alvo proprio, isso deixou TODA posicao sem nenhuma protecao
# de preco - so o corte de horario forcado (18:20:58, ja corrigido na
# PARTE 3) ou o proprio profit-lock do arquivo fechavam uma posicao.
# Constatado pelo dono do laboratorio no ranking ao vivo: drawdown quase
# identico (-498,39) repetido em quase todas as estrategias de entrada
# "3 portas" (variacoes proximas da mesma ideia, correlacionadas, caindo
# no mesmo dia catastrofico sem stop nenhum).
# Corrigido com o mesmo padrao de migracao usado no baseline.py (PARTE 1):
# na abertura da posicao (candles_decorridos == 0) o arquivo agora define
# o MESMO stop estrutural + alvo em RR fixo que o motor calculava antes
# (SWING_LOOKBACK_CANDLES=4, RELACAO_RISCO_RETORNO=1.55, copiados de
# configuracao.py - Regra 3, nao importados). Nas chamadas seguintes o
# arquivo nao redefine mais nada, e a logica original do autor (o
# profit-lock pos-17:30) continua 100% inalterada a partir dai. Contrato
# atualizado de bool para dict (avaliar_saida(row, posicao) -> dict),
# igual ao resto dos cartuchos titulares desde a v10.
# Validado: unit test isolado de _stop_alvo_inicial (COMPRA e VENDA,
# janela insuficiente) e da logica original preservada (fecha/nao fecha/
# antes das 17:30) - sem excecao em nenhum caso. Rodado tambem via
# classificacao.py no dataset oficial (colocado temporariamente como
# titular em estrategia/saida/titular/): resultado 16.336,05 (176 ops),
# drawdown -309,19 - o MESMO numero que baseline.py reproduz (prova de
# que a mesma protecao de preco foi restaurada; o -498,39 desaparece
# porque agora ha stop de verdade desde a abertura). Backtest antigo
# citado no proprio arquivo (score 673,5, medido contra o motor v7,
# stop/alvo fixo do motor) marcado como invalido na propria docstring -
# precisa ser re-testado contra o motor v10 antes de qualquer nova
# comparacao/promocao (Regra 4).
#
# Arquivos alterados: motor.py, estrategia/saida/titular/baseline.py,
# principal.py, registrador.py, email_notificacao.py, analise.py,
# configuracao.py, compliance.md, versionamento.py, changelog.md,
# saida_grok_v6.py.
# Arquivo novo: estrategia/saida/saida_claude_v4.py (candidata, nao
# titular). Arquivo removido do laboratorio: saida_claude_v3.py (superada
# pela v4, mesma ideia com o bug do stop inicial corrigido).

# ---------------------------------------------------------------------------
# V446 — classificacao.py gera log automatico de historico (PR #8)
# ---------------------------------------------------------------------------
# Pedido do dono do laboratorio: "e se cada vez que eu (ou a propria IA)
# rodar o classificacao.py ele gerasse um arquivo de historico/log?" - para
# nao depender de ninguem colar manualmente um resultado no chat ou num PR
# (compliance.md, Regra 4: nenhum resultado vale sem ter sido rodado de novo
# contra o motor atual).
#
# classificacao.py:
# - Nova funcao _git_sha_atual() - devolve o SHA do commit HEAD do
#   repositorio (fallback "sem-git" se rodar fora de um clone git).
# - Novo context manager _capturar_e_imprimir() - deixa o ranking aparecer
#   no terminal normalmente (cores ANSI preservadas) e ao mesmo tempo
#   captura o texto para gravar no log.
# - Nova funcao _registrar_historico(titulo, texto) - remove os codigos
#   ANSI e faz APPEND (nunca sobrescreve) em
#   logs/classificacao_historico.md, carimbado com data/hora e o SHA do
#   commit atual.
# - Os tres pontos de impressao (RANKING ENTRADA, RANKING SAIDA, RANKING
#   CRUZADO) passaram a chamar essas funcoes automaticamente.
#
# Testado: py_compile OK; teste isolado das 3 funcoes novas confirmando SHA
# correto (bate com git rev-parse HEAD), terminal continua colorido, e o
# arquivo de log cresce por append (duas rodadas seguidas coexistiram, nada
# foi apagado).
#
# Arquivo alterado: classificacao.py.

# ---------------------------------------------------------------------------
# V447 — narracao de saida nao confundia mais dict(fechar=False) com "fechar" (PR #9)
# ---------------------------------------------------------------------------
# Bug identificado pelo ChatGPT e confirmado no codigo real de main: em
# principal.py, a narracao especulativa de saida fazia
# "saida_se_aproximando = bool(_modulo_saida.avaliar_saida(...))". Como
# avaliar_saida() sempre devolve um dict (contrato Regra 1 v10), mesmo sem
# fechamento (ex: {"fechar": False, "novo_stop": None, "novo_alvo": None}),
# um dict nao-vazio e truthy em Python - bool(dict) dava sempre True,
# independente do valor real de "fechar". Resultado: o narrador anunciava
# "saida se aproximando" em TODO candle com posicao aberta.
#
# Escopo confirmado antes de mexer: a variavel saida_se_aproximando so
# alimenta a frase de narracao especulativa - nao aparece em mais nenhum
# lugar do arquivo. Nao afeta a entrada, a ordem real enviada ao Profit, nem
# o fechamento efetivo da posicao (essa parte ja usava .get("fechar")
# corretamente). Bug puramente cosmetico na narracao.
#
# Corrigido checando especificamente a chave "fechar" do dict retornado,
# com isinstance() de guarda:
# saida_se_aproximando = (
#     isinstance(decisao_saida_especulativa, dict)
#     and bool(decisao_saida_especulativa.get("fechar", False))
# )
#
# Testado: py_compile OK; logica isolada testada com {"fechar": False, ...}
# -> False, {"fechar": True, ...} -> True, {} -> False, None -> False,
# True (nao-dict) -> False - todos batendo com o esperado.
#
# Arquivo alterado: principal.py.

# ---------------------------------------------------------------------------
# V454 — direção do candle na narração e percentual do radar
# ---------------------------------------------------------------------------
# A narração de fechamento sem sinal deixa de chamar a relação MA21 x MA50
# de direção do candle. Agora informa separadamente a direção efetiva do
# candle (fechamento contra abertura) e a tendência estrutural das médias.
# Exemplo de conflito: "O candle fechou em alta, mas a tendência das médias
# ainda é de baixa. Nenhum sinal de entrada foi confirmado."
#
# O heartbeat do radar passa a mostrar seu progresso técnico em percentual
# ao lado do quadrado colorido, no mesmo padrão visual da posição aberta:
# "50% ■". A lógica de sinais, ordens e classificação não foi alterada.
#
# Arquivos alterados: principal.py, versionamento.py, changelog.md.

# ---------------------------------------------------------------------------
# V455 — radar quantitativo, sustentacao de 100% e DDE silencioso em retry
# ---------------------------------------------------------------------------
# O radar mantem o fechamento visual "100% ■" e passa a quantificar, quando
# o cartucho fornece telemetria, a primeira condicao pendente. Ao atingir
# 100%, mostra tambem por quantos segundos a mesma oportunidade permaneceu
# continuamente confirmada. A perda de qualquer condicao zera a contagem.
#
# O cartucho titular Grok recebeu apenas telemetria opcional (campo detalhe):
# nenhum limiar, prioridade ou retorno de gerar_sinal() foi alterado.
#
# leitor_dde.py deixa de imprimir erros das tentativas 1/3 e 2/3 quando uma
# tentativa seguinte recupera a leitura. Se as tres falharem, continua
# emitindo uma unica mensagem final com o ultimo erro COM e pula o ciclo.
#
# Arquivos alterados: principal.py, leitor_dde.py,
# estrategia/entrada/titular/entrada_grok_3_v1.py, versionamento.py,
# changelog.md.

# ---------------------------------------------------------------------------
# V456 — portao estatistico no classificacao.py (Regra 14)
# ---------------------------------------------------------------------------
# Problema: o ranking apresentava como 1o, 2o e 3o lugares resultados cuja
# diferenca era menor que o ruido da propria amostra. Caso concreto medido em
# 28/09/2026: saida_chatgpt_v4 (R$17.100,57) foi promovida a titular sobre a
# saida_chatgpt_v3 (R$17.044,46) - diferenca de R$56,12 vindo de apenas 5
# operacoes entre as MESMAS 181, contra um erro padrao de R$2.164 no total do
# periodo. A diferenca era 2,6% do ruido, e na primeira metade do historico
# era exatamente R$0,00. Promover por isso e sortear, nao decidir.
#
# classificacao.py:
# - Nova funcao _erro_padrao_total(trades): desvio-padrao amostral do
#   resultado por operacao x sqrt(n) = erro padrao da soma. Devolve nan com
#   menos de 2 operacoes.
# - _resumo() passou a devolver "sd_operacao" e "erro_padrao_total", que o
#   _montar_resultado_par ja propaga via **resumo.
# - Nova funcao _marcar_empates_estatisticos(): escreve a coluna "emp" em
#   cada linha - "1o" no lider, "=" em quem esta dentro da faixa de ruido,
#   vazio em quem esta fora. Usa o MAIOR erro padrao entre o do lider e o da
#   linha comparada (leitura conservadora: so declara vantagem quem a
#   sustenta contra a incerteza dos dois lados).
# - Nova funcao _rodape_portao_estatistico(): imprime o desvio-padrao por
#   operacao, a faixa de ruido em reais e em % do resultado do 1o lugar, e
#   quantas posicoes empatam no topo.
# - Coluna "emp" adicionada ao RANKING PRINCIPAL (cruzado) e aos rankings
#   simples de entrada e saida.
#
# Nenhuma regra operacional mudou: o portao e informativo, nao altera ordem,
# nao filtra ninguem do ranking, nao mexe em motor.py nem em cartucho algum.
# O que ele faz e tornar visivel a incerteza que ja existia.
#
# Medido ao rodar contra o dataset oficial (184 pregoes): desvio-padrao por
# operacao R$160,87, faixa de ruido R$2.164,31 = 12,7% do resultado do 1o
# lugar. No ranking CRUZADO, 133 das 238 combinacoes empatam com a 1a. No
# ranking de SAIDA, 11 dos 17 cartuchos empatam com o 1o.
#
# Testado: py_compile; teste unitario de _erro_padrao_total (0, 1 e 5 trades,
# conferido contra statistics.stdev), de _resumo (campos novos), de
# _marcar_empates_estatisticos (lider, empate, nao-empate, e linha com ruido
# nan caindo no ruido do lider) e do rodape nos dois cenarios; e execucao
# completa nos modos C e S contra o dataset oficial.
#
# Arquivo alterado: classificacao.py.

# ---------------------------------------------------------------------------
# V457 — narracao de expectativa nomeia o horario do fechamento
# ---------------------------------------------------------------------------
# Relato do dono do laboratorio no pregao de 29/09/2026: as 13:30:00 o log
# imprimiu, em sequencia, "Nenhum sinal de entrada foi confirmado" e logo
# abaixo "Se confirmado no fechamento, a ordem sera disparada" - e a leitura
# natural e que a ordem deveria ter saido naquele fechamento.
#
# Nao havia bug. O candle que fecha as 13:30:00 e o candle ROTULADO 13:15
# (row["dt"] e o horario de ABERTURA do candle, ver construir_row em
# motor.py), e a Porta 1 do titular bloqueia "12:00" <= hora <= "13:15" -
# ou seja, aquele era o ultimo candle do bloqueio. A frase de expectativa se
# referia ao fechamento SEGUINTE (13:45), do candle rotulado 13:30, que ja
# esta fora do bloqueio.
#
# Correcao exclusivamente de texto em principal.py: a frase passa a nomear o
# horario - "Se confirmado no fechamento das 13:45, a ordem sera disparada".
# O horario e calculado como candle_atual.horario + TIMEFRAME_MINUTOS.
# A frase alternativa (usada quando o cartucho nao expoe diagnostico) trocou
# "no fechamento deste candle" por "no fechamento do candle em formacao",
# pela mesma razao.
#
# NENHUMA regra operacional mudou: nao ha alteracao de estrategia, de horario
# de bloqueio, de motor ou de cartucho. So a narracao.
#
# Fica REGISTRADA, sem alteracao, uma ambiguidade real encontrada na Porta 1
# do entrada_grok_3_v1: o bloqueio escrito como ate "13:15" se estende, em
# horario de relogio, ate as 13:30, porque o rotulo do candle e a abertura.
# Nao se sabe se foi intencional. Mudar isso e alteracao de estrategia e
# precisa passar pelo classificacao.py nos dois periodos disponiveis
# (2023-2024 e 2026) antes de qualquer decisao - nao foi tocado aqui.
#
# Testado: py_compile; conferencia do calculo do horario para os rotulos
# 13:15 -> 13:30, 13:30 -> 13:45 e 18:00 -> 18:15.
#
# Arquivo alterado: principal.py.


# ---------------------------------------------------------------------------
# V458 — paridade Replay/ao vivo: removidos os dois artificios exclusivos do Replay
# ---------------------------------------------------------------------------
#
# Regra de governanca estabelecida pelo dono do laboratorio em 30/09/2026:
# qualquer artificio que rode somente no Replay e nao reproduza o mesmo
# resultado no mercado ao vivo deve ser removido do robo imediatamente. O
# Replay e o ensaio geral da operacao real; se ele mente, mente no lugar mais
# caro possivel.
#
# Varredura do codigo encontrou DOIS artificios que violavam a regra, e tres
# diferencas de modo que NAO a violam (mantidas, com justificativa).
#
# ARTIFICIO 1 — reconciliacao de OHLC (removido)
#   Era: `_reconciliar_ohlc_replay()` + `RECONCILIAR_OHLC_OFICIAL_NO_REPLAY`.
#   No Replay, o OHLC amostrado pelo DDE era substituido pelo OHLC consolidado
#   do arquivo exportado do Profit, depois do fechamento do candle.
#   Por que viola: ao vivo o robo le somente o campo ULT a cada 2 segundos
#   (1s perto do fechamento), e monta maxima/minima a partir dessas amostras.
#   A maxima/minima amostrada e SEMPRE mais estreita que a verdadeira, nunca
#   mais larga. Como o stop da saida titular e `min(Minimo)` dos ultimos 5
#   candles e o alvo e RR x risco, OHLC diferente produz stop diferente, alvo
#   diferente e %K diferente - logo sinais diferentes.
#   Removido de: principal.py (funcao, bloco de carga, call site, campo de
#   auditoria) e configuracao.py (a chave).
#
# ARTIFICIO 2 — remocao dos limites diarios (removido; era o de maior impacto)
#   Era: ao responder REPLAY, principal.py elevava cfg.MAX_OPERACOES_DIA e
#   cfg.MAX_PERDAS_DIA de 2 para 999.
#   Por que viola: `motor.pode_abrir_posicao()` barra toda entrada por esses
#   dois limites. Um Replay podia abrir dez operacoes num dia em que a operacao
#   real teria parado na segunda. Nao e um detalhe de preco - muda a QUANTIDADE
#   de posicoes, e com ela o resultado do dia inteiro.
#   Agravante: a classificacao.py nao mexe nesses limites, logo roda com 2/2,
#   os mesmos valores do ao vivo. O Replay era o unico dos tres ambientes fora
#   de padrao, divergindo ao mesmo tempo da operacao real E do juiz.
#   Removido de: principal.py (bloco do modo REPLAY). Para observar sem limites,
#   alterar MAX_OPERACOES_DIA/MAX_PERDAS_DIA em configuracao.py explicitamente.
#
# DIFERENCAS DE MODO MANTIDAS (nao sao artificios; nao alteram decisao de trade)
#   a) `if not _MODO_REPLAY and agora.date() < agora_real.date()` — guarda de
#      data velha. Existe PORQUE o Replay roda legitimamente numa data diferente
#      do relogio do computador; mante-la ativa no Replay o tornaria impossivel.
#      E um portao de "aguardando abertura", nao logica de estrategia.
#   b) `verificar_integridade(..., modo_replay=...)` — pula a checagem de deriva
#      de relogio no Replay, pela mesma razao. As checagens de salto implausivel
#      e de preco congelado continuam ativas nos dois modos. E diagnostico.
#   c) `PREFIXO_REPLAY = "[R] "` — qual nome de ativo procurar na coluna A da
#      planilha. Encanamento puro.
#
# DIVERGENCIA RESIDUAL, AGORA EXPLICITA
#   Depois desta versao, Replay e ao vivo usam a mesma fonte de preco (DDE
#   amostrado) e os mesmos limites. A classificacao.py continua lendo OHLC
#   verdadeiro do CSV, porque nao existe dado tick a tick no laboratorio - nao
#   ha como o juiz amostrar a 2s. Essa divergencia e inevitavel, afeta todos os
#   cartuchos na mesma direcao (e por isso tolerevel numa comparacao relativa),
#   e passa a estar DOCUMENTADA em vez de escondida atras de um artificio.
#   Medida do teto do efeito (amostrador de 60s, 30x mais esparso que o real,
#   logo teto e nao estimativa; 4.009 candles de 15M de 2026): estreitamento de
#   118,6 pts = 26,3% da largura do candle, erro de 2,86 pontos de %K em media
#   (25,12 no pior caso), +10,2% de cruzamentos de zona do estocastico.
#
# EFEITO PRATICO ESPERADO: resultados de Replay passam a ser MENOS favoraveis
# que antes, e mais parecidos com o que a operacao real entrega. Qualquer
# comparacao com Replay anterior a V458 esta contaminada pelos dois artificios
# e nao deve ser usada como referencia.
#
# Testado: py_compile em principal.py e configuracao.py; grep confirmando zero
# residuos de ohlc_oficial_replay, _reconciliar_ohlc_replay e
# RECONCILIAR_OHLC_OFICIAL_NO_REPLAY; timedelta e Path seguem em uso.
# NAO testado: execucao em Replay real contra o Profit (exige a planilha DDE).
#
# Arquivos alterados: principal.py, configuracao.py, versionamento.py.


# ---------------------------------------------------------------------------
# V459 — removido MAX_OPERACOES_DIA (teto de contagem de operacoes por pregao)
# ---------------------------------------------------------------------------
#
# Pedido do dono do laboratorio em 30/09/2026, com a premissa de que
# "dificilmente vamos ter um grande numero de oportunidades diarias". Como e
# controle de risco em producao com ENVIAR_ORDENS=True, a premissa foi MEDIDA
# no motor oficial antes de qualquer alteracao, nos dois periodos disponiveis,
# variando somente MAX_OPERACOES_DIA e mantendo MAX_PERDAS_DIA=2 intacto.
#
# OPORTUNIDADES POR PREGAO (par titular, sem teto de contagem)
#
#                     1 op     2 ops    3 ops    4+
#   2026 (137 op.)    67,9%    28,5%     3,6%   nenhum
#   2023-2024 (360)   68,1%    28,1%     3,9%   nenhum
#
# Distribuicao praticamente identica em dois periodos independentes, e nenhum
# pregao chegou a 4 operacoes nem sem teto algum - a estrategia se limita em 3
# por conta propria. A premissa esta confirmada.
#
# CUSTO DO TETO
#   2026      : com teto R$17.100,57 (181 ops) | sem teto R$17.013,59 (186 ops)
#               diferenca -R$86,98 | faixa de ruido R$2.183,60 -> RUIDO
#   2023-2024 : com teto R$-386,92 (475 ops) | sem teto R$-292,89 (489 ops)
#               diferenca +R$94,02 | faixa de ruido R$2.580,25 -> RUIDO
#
# Os dois dentro da faixa, com SINAIS OPOSTOS - assinatura de mudanca sem
# efeito real, coerente com algo que toca ~4% dos pregoes. O teto barrava
# entrada em 5/137 e 14/360 dos pregoes operados.
#
# POR QUE REMOVER NAO AFROUXA A PROTECAO DE CAPITAL
#   MAX_PERDAS_DIA=2 continua. Para o teto de CONTAGEM morder, era preciso ja
#   ter duas operacoes no dia com no maximo UMA perda - senao o limite de
#   perdas teria parado antes. Logo o teto de contagem so barrava a terceira
#   entrada de um pregao que ia BEM. Mordia no dia saudavel e ficava quieto no
#   dia ruim; nunca foi ele que protegia a banca.
#
# ALTERACOES
#   configuracao.py : a constante MAX_OPERACOES_DIA deixou de existir; no lugar
#                     fica o registro da medicao. MAX_PERDAS_DIA intacto.
#   motor.py        : o portao em pode_abrir_posicao() saiu. O contador
#                     operacoes_hoje CONTINUA sendo mantido e persistido, para
#                     relatorio e estado - so nao barra mais entrada.
#   analise.py      : a linha "Limites" do relatorio nao anuncia mais um teto
#                     que nao existe.
#   principal.py    : as duas mensagens de abertura (REPLAY e NORMAL) deixaram
#                     de citar a constante removida.
#
# Nenhum cartucho tocado. Nenhuma pasta titular/ tocada.
#
# EFEITO PRATICO: em ~4% dos pregoes operados o robo podera abrir uma terceira
# operacao onde antes parava em duas. Nos outros 96% nada muda, porque a
# estrategia nao encontra terceira oportunidade. Quem quiser o teto de volta
# precisa trazer medida com efeito FORA da faixa de ruido - a intuicao de que
# mais operacoes e mais risco nao se sustentou nestes dois periodos.
#
# NAO MEDIDO: o efeito sobre os cartuchos candidatos (a medicao cobre o par
# titular). Se alguma candidata gerar muito mais oportunidades por pregao, o
# teto importaria mais para ela - reconferir antes de promover.
#
# Testado: py_compile em motor.py, configuracao.py, principal.py, analise.py e
# classificacao.py; grep confirmando zero residuos de MAX_OPERACOES_DIA fora
# dos comentarios historicos; hasattr(cfg,'MAX_OPERACOES_DIA') == False;
# classificacao.py reexecutada em 2026 confirmando os numeros do cenario sem
# teto (186 operacoes, R$17.013,59).
#
# Ata: conselho/2026-09-30-U.txt
#
# Arquivos alterados: motor.py, configuracao.py, principal.py, analise.py,
# versionamento.py.

# ---------------------------------------------------------------------------
# V460 - COLETA PASSIVA de campos extras do DDE (so grava; nao decide nada)
# ---------------------------------------------------------------------------
# Origem: proposta do DeepSeek (volume/negocios/estocastico do Profit ja
# estariam na planilha DDE) + pedido do dono do laboratorio de implementar.
# NADA do que ele previu foi aceito como ganho: os testes de volume (ata V) nao
# sustentam as previsoes. O que se aproveita e a oportunidade de MEDIR.
#
#   coleta_dde.py   : NOVO. Grava logs/coleta_dde_AAAA-MM-DD.csv por candle, com
#                     quantidade/negocios/volume (acumulados no dia, mais a
#                     diferenca por candle) e o estocastico do Profit.
#   leitor_dde.py   : COLUNAS_EXTRAS_DDE (vazio = desligado) e ler_extras(),
#                     uma leitura por coluna, best-effort, sem excecao.
#   principal.py    : cria a coleta e chama coleta.processar() apos
#                     construtor.nova_leitura().
#
# DESLIGADO POR PADRAO: com COLUNAS_EXTRAS_DDE = {} o comportamento e identico
# ao da V459. Para ligar, mapear nome -> coluna da planilha (conferir na
# planilha DDE; as colunas citadas pelo DeepSeek NAO foram verificadas).
# Motor, estrategias, gestor de risco e executor nao importam a coleta.
#
# Para que serve: validar Quantidade do DDE contra o CSV exportado, comparar o
# %K do Profit com o do motor, e acumular Negocios (inexistente no CSV). So
# depois disso discutir uso na decisao (Regra 4: backtest antes de qualquer
# alegacao). Paridade replay/ao vivo: conferir que o acumulado do DDE se
# comporta igual nos dois modos antes de qualquer uso.
#
# Testado: py_compile; teste unitario da coleta com amostras sinteticas
# (diferenca por candle, primeiro candle sem base, entrada sem extras).
#
# Arquivos alterados: coleta_dde.py (novo), leitor_dde.py, principal.py,
# versionamento.py.

# ---------------------------------------------------------------------------
# V461 - Bloqueio de NOVAS entradas apos buraco nao preenchido no historico
# ---------------------------------------------------------------------------
# Incidente de 01/10/2026: o robo iniciou com historico que nao cobria 29/09,
# 30/09 e a manha de 01/10, AVISOU "MA21/RSI/ATR podem estar incorretos" e
# mesmo assim abriu COMPRA real (Porta 2, Distancia=3006pts) com stop a 3.535
# pts. Agora, se faltarem candles de PREGAO e o arquivo nao cobrir o trecho,
# nao abre posicao nova por CANDLES_AQUECIMENTO_APOS_BURACO (50) candles;
# posicao ja aberta segue gerida.
#
#   construtor_candle.py: candles_faltando() - conta candles de pregao faltando
#                         (fim de semana, feriado e noite nao contam).
#   configuracao.py     : CANDLES_AQUECIMENTO_APOS_BURACO, HORARIO_PRIMEIRO_CANDLE,
#                         HORARIO_ULTIMO_CANDLE, FERIADOS_B3 (manter atualizado).
#   principal.py        : arma o bloqueio no ramo "nao foi possivel preencher",
#                         decrementa a cada candle e barra a entrada.
#
# Motor, cartuchos e classificacao.py intactos NESTA PARTE: sem buraco de pregao
# o comportamento e identico (paridade backtest/replay/ao vivo preservada).
#
# CAUSA DO BURACO (correcao do dono, 01/10, confirmada): ele HAVIA exportado o
# historico antes de iniciar, mas salvou com outro nome
# (WINFUT_F_0_15min_01-01-2026_01-10-2026.csv, 7.081 candles ate 01/10 10:00); o
# robo leu o nome configurado WINFUT_F_0_15min.csv, o export ANTIGO (7.000 candles
# ate 28/09 18:15). Agora: principal._resolver_csv_historico() escolhe o WINFUT*.csv
# mais recente da pasta, ha aviso na carga e o bloqueio acima.
#
# V461 tambem traz o LIMITE DE RISCO POR OPERACAO pedido pelo dono em 01/10:
#   configuracao.py : BANCA_REAL_REAIS = 1490.00 e RISCO_MAXIMO_PCT_BANCA = 0.25
#   motor.py        : validar_risco_inicial() - pergunta o stop ao cartucho de
#                     saida (sem abrir nada) e recusa se risco > 25% da banca
#                     real; usada em avaliar_candle (backtest) e em principal.py
#                     ANTES de enviar a ordem (ao vivo) => paridade.
#   Mensagem: "Oportunidade a frente mas a banca nao ira suportar o tamanho do
#   stop loss (...)". Limite hoje: R$ 372,50 = ~1.862 pts.
#   Medido no motor oficial (titular x saida_chatgpt_v4): 2026 -2 ops, -R$ 1.815
#   (17.013,59 -> 15.198,56; ruido R$ 2.184); 2023-24 -7 ops, +R$ 757 (-292,89 ->
#   +464,20; ruido R$ 2.580). Dentro do ruido nos dois, sinais opostos: e o
#   preco de nao carregar stops que a banca nao suporta.
# NAO implementado: teto de risco por operacao (conflita com Regra 1 v9;
# precisa decisao do dono e medicao previa). Ata: conselho/2026-10-01-W.txt
#
# Testado: py_compile; candles_faltando() com 6 casos (incidente = 80 faltando;
# sexta->segunda = 0; feriado = 0).
#
# Arquivos alterados: construtor_candle.py, configuracao.py, principal.py,
# versionamento.py.

# ---------------------------------------------------------------------------
# V462 - Correcoes da revisao do Manus (ata 2026-10-02-Y) a V461
# ---------------------------------------------------------------------------
#   A) motor.validar_risco_inicial: stop que NAO pode ser verificado (excecao,
#      ausente, nao numerico, NaN/inf, lado errado) agora BLOQUEIA a entrada
#      (cfg.RISCO_FALHA_FECHADA = True). Antes liberava e, com texto, lancava erro.
#   B) historico_csv.py (novo): a escolha do CSV exige mesmo ativo e MESMO
#      timeframe (mediana do intervalo). principal.py passa a importar dele.
#   C) principal.py: o bloqueio apos buraco e decidido DEPOIS de qualquer tentativa
#      de preenchimento, pelo que ainda falta (preenchimento parcial nao libera).
#   D) saida_grok_reverso_v3 le posicao["stop"], que o motor nao entrega: nunca
#      arma o 0,618R (por isso empata ao centavo com a v4). NAO alterada (autor).
#
# Titular x saida_chatgpt_v4 identica ao centavo com fail-closed: 2026 R$ 15.198,56
# (184 ops) e 2023-24 R$ 464,20 (482 ops). tests/ novos (18 testes, unittest).
# Ata: conselho/2026-10-02-Z.txt
#
# Arquivos alterados: motor.py, principal.py, configuracao.py, historico_csv.py
# (novo), tests/test_v461_risco.py e tests/test_v461_historico.py (novos),
# versionamento.py.

# ---------------------------------------------------------------------------
# V464 - Bloqueios de horario explicitos no radar
# ---------------------------------------------------------------------------
# O numero V463 ja identifica no classificacao.py o criterio de pontos diarios
# incorporado a main pelos PRs #50 e #51. Esta entrega usa V464 para evitar
# uma nova colisao de versoes, embora versionamento.py ainda estivesse em V462.
#
# Quando a oportunidade prioritaria esta fora de sua janela operacional, o
# radar deixa de mostrar a expressao ambigua "Falta horario permitido" e passa
# a informar objetivamente ate quando permanece bloqueada. Os horarios exibidos
# sao os do relogio: o candle rotulado 13:15 fecha as 13:30, portanto o bloqueio
# inclusivo ate o rotulo 13:15 aparece como "BLOQUEADA ATE 13:30".
#
# Mensagens cobertas: Retomada MA21 (almoco, tarde e quinta-feira), MACD +
# Estocastico (ate 12:45) e Saida de Extremo (ate 13:30). A grade conserva o
# percentual e o quadrado colorido no final da linha.
#
# Mudanca exclusivamente de telemetria. Nenhum horario, limiar, prioridade,
# sinal, ordem, stop, alvo, motor ou calculo da classificacao foi alterado.
# A copia candidata e a titular de entrada_grok_3_v1 permanecem identicas.
#
# Arquivos alterados: principal.py,
# estrategia/entrada/entrada_grok_3_v1.py,
# estrategia/entrada/titular/entrada_grok_3_v1.py, versionamento.py e
# changelog.md.

# ---------------------------------------------------------------------------
# V465 - Importacao separada do pacote strategies (entrada x saida)
# ---------------------------------------------------------------------------
# O ZIP recebido contem 24 estrategias registradas em outro framework, cujo
# on_bar() devolve OrderIntent com sinal, stop e alvo no mesmo objeto.
#
# NOVE regras exclusivamente OHLC foram convertidas em cartuchos independentes
# de entrada (channel/reversion, EMA pullback e failed break, v1/v2). A memoria
# _last_direction do framework externo foi eliminada: o mesmo efeito e obtido
# comparando a condicao atual com a condicao do candle anterior, portanto as
# chamadas permanecem deterministicas e seguras em classificacoes repetidas.
#
# As nove embutiam a mesma protecao, agora separada em uma unica candidata de
# saida: saida_daytrader_rr2_v1. Stop = max(20 pts, 1,25 x amplitude media dos
# 20 candles anteriores); alvo = max(stop + 5 pts, 2R); sem fechamento
# antecipado adicional.
#
# motor.py passa a fornecer os ultimos 22 candles em ohlc_recentes (eram 12):
# 20 anteriores + candle atual + candle necessario para reproduzir a supressao
# consecutiva. Auditoria dos consumidores confirmou recortes finais explicitos;
# cenario.py foi fixado em [-12:] para preservar exatamente sua calibracao.
#
# NAO ATIVADAS:
# - 14 estrategias dependentes de volume: o volume ainda nao integra de forma
#   pareada o Candle/row do laboratorio e o DDE ao vivo;
# - smc_structure_retest_v3: maquina de estados sem contrato oficial de reset e
#   isolamento por execucao.
# Decoradores e infraestrutura do framework tambem nao viraram cartuchos.
# Nenhum titular foi alterado.
#
# VALIDACAO: nove adaptacoes comparadas candle a candle em 9.394 candles reais,
# com zero divergencias; 7 testes unitarios novos; contrato de saida validado
# para COMPRA e VENDA; suite completa, py_compile e diff-check executados.
# Inventario e motivos: estrategia/IMPORTACAO_STRATEGIES.md.
#
# Arquivos alterados: motor.py, cenario.py, nove entradas candidatas,
# _daytrader_ohlc.py, saida_daytrader_rr2_v1.py,
# tests/test_v465_strategias_importadas.py, estrategia/IMPORTACAO_STRATEGIES.md,
# versionamento.py e changelog.md.

# ---------------------------------------------------------------------------
# V466 - Candidatas Paulinho / metodo Just adaptadas ao WIN de 15 minutos
# ---------------------------------------------------------------------------
# Duas origens percentuais descritas na entrevista viraram entradas separadas:
# fechamento anterior e origem intradiaria, ambas a +/-0,60% para o indice.
# Como o motor decide em candle fechado, o sinal exige rejeicao confirmada da
# faixa em vez de simular a ordem limite intrabar exibida no video.
#
# saida_paulinho_just_rr2_V01 usa stop de 0,20% e alvo de 0,40% do preco de
# entrada, arredondados para fora ao tick de 5 pontos do WIN.
# ohlc_recentes passou de 22 para 96 candles para cobrir a sessao atual e a
# anterior. Nenhum titular foi alterado.
#
# Arquivos: motor.py, estrategia/PAULINHO_JUST.md, _paulinho_just.py, duas
# entradas Paulinho, uma saida Paulinho, tests/test_v466_cartuchos_paulinho.py,
# tests/test_v465_strategias_importadas.py, tests/test_gabriel_compatibilidade.py,
# versionamento.py e changelog.md.

# ---------------------------------------------------------------------------
# V467 - pasta tests/ extinta: testes passam a viver no laboratorio
# ---------------------------------------------------------------------------
# estrategia/entrada e estrategia/saida sao o laboratorio (a peneira para
# chegar a titular); os testes de verificacao ficam ao lado das candidatas, em
# arquivos com prefixo "_test_" (o prefixo "_" os mantem fora da classificacao,
# Regra 7). Divisao: entradas e dados/infra em estrategia/entrada; saidas e o
# limite de risco do stop em estrategia/saida. Nenhum teste foi removido (83
# antes e depois). Nenhum cartucho nem titular alterado.
#
# Rodar: python -m unittest discover -s estrategia/entrada -p "_test_*.py"
#        python -m unittest discover -s estrategia/saida -p "_test_*.py"
#
# CI: a verificacao da Regra 3 passa a ignorar arquivos "_test_*" (testes
# precisam importar motor/classificacao) e o workflow roda as duas suites.
#
# Arquivos: tests/ (removida), 17 arquivos _test_*.py em estrategia/entrada e
# estrategia/saida, .github/workflows/robonildo-v2-ci.yml, historico_csv.py,
# versionamento.py e changelog.md.

# ---------------------------------------------------------------------------
# V479 - novas fontes de retorno para a meta de R$20 mil de acumulado
# ---------------------------------------------------------------------------
# Tres entradas independentes, ainda candidatas e sem alteracao de titular:
# rompimento da faixa de abertura, liberacao de compressao e continuacao de
# gap. Uma saida candidata preserva o stop/alvo da chatgpt_v4 e encerra apos
# quatro candles quando a posicao segue negativa e nunca alcancou 0,45 ATR de
# excursao favoravel. Nenhuma depende de data, evento, preco absoluto, I/O ou
# dado posterior ao candle fechado.
#
# Por compliance Regra 12, nenhum ranking oficial foi executado antes da
# revisao do PR. Validacao feita somente com seis testes sinteticos mais a
# suite integral: 109 testes OK, 6 pulados; py_compile e diff-check OK.
# Nenhum titular, motor, classificacao ou configuracao foi alterado.

# ---------------------------------------------------------------------------
# V468 - Candidatas compostas de laboratorio (entrada e saida)
# ---------------------------------------------------------------------------
# Pedido do dono: reunir o "supra sumo" em uma entrada e uma saida. Metodo:
# desenho em jan-jun/2026, holdout jul-out/2026 (66 pregoes) rodado uma unica
# vez, nenhum limiar novo (todos copiados dos cartuchos de origem).
#
# saida_composta_stop_atr_alvo_ma21_claude_v1: stop estrutural limitado a 1,80
# ATR (stop_atr) + alvo na MA21 com 1R de distancia, senao 1,55R (alvo_media) +
# corte das 18h (corte_18h). Acumulado com entrada grok_3: desenho 11.773
# (chatgpt_v4: 10.273); holdout 3.189 (titular: 4.057) - NAO supera o titular;
# 2023-24: -2.136 (titular -2.418). Obs.: saida_stop_atr, 1a do ranking de
# 2026, tambem fica abaixo do titular no holdout (3.220).
#
# entrada_composta_grok_fim_tarde_claude_v1: as 3 portas da grok_3 (copia
# literal) + rompimento de fim de tarde como 4a porta. Nenhuma outra entrada
# positiva acrescenta sinal a grok_3 (uniao = grok_3). Acumulado com saida
# titular: desenho 10.394 (grok_3: 10.273); holdout 4.016 (4.057); 2023-24
# -660 (grok_3 -2.418).
#
# Nenhum titular alterado; ambas ficam como candidatas (Regra 12 antes de
# qualquer promocao). Testes: _test_composta_grok_fim_tarde.py e
# _test_composta_stop_atr_alvo_ma21.py (96 testes no total).
#
# Arquivos: estrategia/entrada/entrada_composta_grok_fim_tarde_claude_v1.py,
# estrategia/saida/saida_composta_stop_atr_alvo_ma21_claude_v1.py, dois
# _test_*.py, versionamento.py e changelog.md.

# ---------------------------------------------------------------------------
# V469 - descoberta nao depende mais de sublinhado inicial no nome do arquivo
# ---------------------------------------------------------------------------
# Incidente: no disco do dono os arquivos "_*.py" perderam o "_" (copia entre
# pastas), entao "_paulinho_just.py", "_daytrader_ohlc.py" e "_test_*.py"
# apareceram como candidatos INCOMPATIVEIS e os imports "estrategia.entrada._x"
# quebraram (entrada_paulinho_just_fechamento_V01 nao carregou).
#
# Correcao sem depender do prefixo: auxiliares de cartucho foram para
# estrategia/entrada/auxiliar/ (daytrader_ohlc.py, paulinho_just.py; a
# descoberta nunca desce em subpastas) e os testes viraram test_*.py, que o
# classificador agora ignora (alem dos "_*" reservados pela Regra 7, mantida).
# Rodar: python -m unittest discover -s estrategia/entrada   (e estrategia/saida)
#
# Nao ha mudanca de regra de estrategia nem de titular. Suites: 67 + 29 OK.
# Acao do dono: apagar de estrategia/entrada/ os arquivos antigos
# daytrader_ohlc.py e paulinho_just.py (copias sem "_"); os test_*.py antigos
# sao sobrescritos pelos novos e ja sao ignorados.
#
# Arquivos: classificacao.py (_listar_py), 11 cartuchos de entrada (import),
# auxiliar/ (2 movidos), 16 testes renomeados, CI, historico_csv.py,
# versionamento.py e changelog.md.
#
# Merge com a main (commit "atualizacao de estrategias" do dono): mantidas as
# remocoes das estrategias daytrader, gabriel e paulinho_origem; testes que
# dependiam delas foram ajustados (test_daytrader_entradas sem o teste dos nove
# cartuchos; test_gabriel_entradas sem contagem fixa). O diagnostico_cenarios.py
# chegou VAZIO na main (0 linhas) e foi restaurado da V468 porque test_cenario
# depende dele - se o esvaziamento foi intencional, reverter este arquivo.

# ---------------------------------------------------------------------------
# V470 - Modo D (Diagnostico de cenarios) dentro de classificacao.py
# ---------------------------------------------------------------------------
# Pedido do dono: o diagnostico de cenarios deve ser uma opcao do
# classificacao.py. O diagnostico_cenarios.py (que chegou VAZIO na main) foi
# incorporado como modo "D" ao lado de E/S/C/A e o arquivo foi removido.
# So leitura: R$/operacoes de cada entrada (x saida titular) e de cada saida
# (x entrada titular) por cenario, distribuicao de cenarios, matriz de acerto do
# reconhecedor (dados simulados em regimes) e, com --metades, o que se repete
# nas duas metades do periodo. Nunca pergunta cenario (ja separa por cenario).
#   python classificacao.py [csv] --modo D [--metades] [--simular regimes ...]
# Grava logs/diagnostico_cenarios_c001_motor_<versao>[_fonte].csv.
#
# Funcoes: diagnosticar_cenarios, distribuicao_cenarios, matriz_confusao_cenarios,
# acerto_geral_cenarios, nomes_curtos, consistencia_metades. Testes:
# test_modo_diagnostico.py (novo) e test_cenario.py (importa classificacao).
#
# Arquivos: classificacao.py, diagnostico_cenarios.py (removido), dois testes,
# versionamento.py e changelog.md. Nenhuma estrategia ou titular alterado.


# ---------------------------------------------------------------------------
# V471 — classificacao.py nao imprime mais o inventario de cartuchos
# ---------------------------------------------------------------------------
# O bloco "CARTUCHOS NO DISCO (entrada/saida — sem laboratorio)" que abria toda
# execucao foi removido (chamada e funcao imprimir_inventario_cartuchos).
# A descoberta de cartuchos (listar_cartuchos_disco) e o aviso de
# INCOMPATIVEIS no final permanecem iguais. Nenhuma estrategia alterada.


# ---------------------------------------------------------------------------
# V472 — tela do classificacao.py mais enxuta
# ---------------------------------------------------------------------------
# Removidos do inicio da execucao: a linha "Multi = score ABSOLUTO...", os
# titulos [ETAPA 1/2] e [ETAPA 2/2], a lista com o nome de cada saida validada,
# a linha "Saidas compativeis | Combinacoes a executar" e as linhas por
# combinacao. Entra uma unica barra [COMBINACOES] atualizada na mesma linha.
# Incompativeis continuam listados no fim. _progresso() agora apaga o resto da
# linha anterior. Nenhuma estrategia alterada.


# ---------------------------------------------------------------------------
# V473 — classificacao.py so grava arquivo no modo A (Analise)
# ---------------------------------------------------------------------------
# Removidos: logs/classificacao_historico.md, os CSVs classificacao_entrada/
# saida/cruzada, o CSV do modo D e os CSVs do simulador. Modos E, S, C e D
# apenas imprimem. O modo A grava somente o .xlsx, agora em <projeto>/analise
# (..\DAYTRADE\ROBONILDO\analise), sem o antigo destino D:\DAYTRADE\ANALISES
# e sem fallback para logs/. --saida-dir continua permitindo outra pasta.
# Teste do modo D agora confere que nenhum arquivo e criado.
# Nenhuma estrategia alterada.


# ---------------------------------------------------------------------------
# V474 — estrategia/entrada e estrategia/saida so com estrategias candidatas
# ---------------------------------------------------------------------------
# Os 17 arquivos test_*.py foram movidos para estrategia/testes/ (mesma
# profundidade: parents[2] continua sendo a raiz). O unico nome repetido foi
# renomeado: test_entrada_candidatas_cenario.py e test_saida_candidatas_cenario.py.
# Rodar: python -m unittest discover -s estrategia/testes -p 'test_*.py'
# (99 testes). CI atualizado: Regra 3 varre entrada/ e saida/ sem excecao e os
# testes rodam de estrategia/testes. _listar_py continua ignorando test_* como
# rede de seguranca. Nenhuma estrategia alterada.


# ---------------------------------------------------------------------------
# V475 — limpeza: removido o que nao faz parte de classificacao.py nem principal.py
# ---------------------------------------------------------------------------
# Criterio: cadeia de imports de principal.py e classificacao.py + cartuchos
# carregados por eles (entrada/ e saida/ e titulares). Tudo continua no
# historico do git.
# Removidos: classificacao_teste.py (copia antiga do classificador),
# teste_email.py (teste manual avulso), arquivo vazio `python`,
# estrategia/entrada/auxiliar/ (daytrader_ohlc.py, paulinho_just.py; sem uso
# desde que as entradas daytrader/paulinho foram apagadas),
# estrategia/entrada/desclassificada/ (3 entradas fora do ranking),
# estrategia/saida/antigas/ (13 copias identicas das saidas que seguem em
# saida/) e os testes test_daytrader_entradas, test_paulinho_entradas e
# test_gabriel_entradas (testavam codigo removido). Mantidos: documentos
# (compliance, changelog, conselho/, diario/), CI, CODEOWNERS e
# sincronizar_github.bat. Testes: 86 OK (6 pulados). Ranking inalterado
# (18 entradas, 32 saidas).


# ---------------------------------------------------------------------------
# V476 — historico por ano: uma pasta por ano para o backtest
# ---------------------------------------------------------------------------
# Layout: D:\DAYTRADE\HISTORICO\2023, \2024, ... \2026, cada pasta com um ou mais
# .csv (export do Profit, 15 min). configuracao.py: PASTA_HISTORICO_BACKTEST
# (a pasta-base) e CAMINHO_HISTORICO_INICIAL agora aponta para a pasta 2026 —
# e o que o principal.py le (a resolucao do CSV mais recente da pasta, V462,
# continua valendo). classificacao.py: sem csv na linha de comando, descobre as
# pastas de ano sob a pasta-base, pergunta os anos (Enter = todos; 2023; 2023-2025;
# 2022,2024; ultimos 2) ou usa --anos, e funde os csv dos anos escolhidos numa
# serie unica (so candles do proprio ano da pasta, so timeframe de 15 min,
# candle repetido vale o do ultimo arquivo por ordem de nome). Anos nao
# consecutivos: os 3 primeiros pregoes depois do salto so aquecem os indicadores
# (historico_csv.dias_pos_buraco). Sem pastas de ano, cai no arquivo unico de
# sempre. Linha de comando (--modo/--periodo/--simular) nao pergunta: vale todos.
# Funcoes puras em historico_csv.py (listar_anos, csvs_do_ano, interpretar_anos,
# dias_pos_buraco). Teste: estrategia/testes/test_historico_anos.py.
# Nenhuma estrategia alterada.
#
# Desempenho (mesma versao): classificacao.preparar_rows passa a dar a cada linha
# so os ultimos JANELA_INDICADORES=1500 candles em vez do historico inteiro. O
# custo era quadratico no tamanho do historico (anos = dezenas de minutos). As
# linhas saem identicas bit a bit (conferido: 7.049 linhas de 2026, ~6.200 de
# 2023-24 e teste_janela_indicadores.py). Ranking de 2026 inalterado
# (composta 14.697,95 / grok_3 14.617,70), 34 s; 3 pastas de ano (684 pregoes) em 2m27s.


# ---------------------------------------------------------------------------
# V477 — processamento do classificacao.py: fatia O(1) no motor e paralelismo
# ---------------------------------------------------------------------------
# 1) executar_jogo passava candles[:indice+1] ao motor a cada candle (copia O(n);
#    quadratico no historico). Com `row` pronta o motor so le candles[-1]
#    (processar_candle_historico/avaliar_row), entao passa candles[indice:indice+1].
#    Resultado identico; metade do tempo de uma combinacao em 2026 e muito mais
#    com varios anos.
# 2) Modos E/S/C/A rodam em paralelo (multiprocessing, sempre "spawn" como no
#    Windows): o historico e cortado em blocos de pregoes consecutivos (4 por
#    processo); cada processo calcula os indicadores so dos seus dias (janela de
#    1.500 candles para tras), roda todas as combinacoes neles e devolve as
#    operacoes, juntadas em ordem. Vale porque o motor nao carrega nada de um
#    pregao para o outro (posicao, perdas_hoje e operacoes_hoje zeram por dia; a
#    banca so aparece em log) e nenhuma posicao atravessa o fechamento. Nenhuma
#    linha de indicadores trafega entre processos. Cartuchos sao importados em
#    cada processo pelo caminho do arquivo.
#    Padrao: nucleos logicos - 1 (maximo 8); --processos N, --sem-paralelo (= 1);
#    abaixo de 2.500 candles avaliados, ou no modo D, roda em serie.
#    validar_contrato_saida so usa a ultima linha de indicadores: o processo
#    principal calcula apenas ela (_row_de_validacao).
# Conferido: as 576 combinacoes de 2026 dao exatamente as mesmas operacoes em
# serie e em paralelo; teste_paralelo.py repete a conferencia numa serie sintetica.
# Nenhuma estrategia alterada.
# Tambem: removido test_gabriel_saidas.py (as 3 saidas Gabriel foram excluidas da pasta de
# estrategias no commit 'excluido arquivos desclassificados'; o teste exigia os 3 arquivos).


# ---------------------------------------------------------------------------
# V481 — saida ChatGPT estrutural assimetrica validada
# ---------------------------------------------------------------------------
# Nova candidata S001: stop estrutural de quatro candles limitado a 2,10 ATR;
# alvo de 1,90R em COMPRA e 1,55R em VENDA. Nenhum titular alterado.
# Em 2026 ate 24/09: R$16.420,63, DD -R$323,50 e acumulado R$16.097,12
# com entrada_grok_3_v1; primeira colocada no ranking disponivel.
# Validacao segmentada em 150/50/50 pregoes e controle anterior de 183 pregoes.
# Suite: 112 testes OK, 6 pulados. Ata: conselho/2026-10-05-AC.txt.
