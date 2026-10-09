"""
ROBONILDO - configuracao.py

Parametros da estrategia MA_v2, validada com backtest de 12 meses (WINFUT, candle 15min)
e confirmada com teste treino/teste (unica, entre 11 hipoteses testadas, que se manteve
estavel fora da amostra).

NAO alterar estes valores sem rodar novo backtest isolado e validacao treino/teste.
Mudar um numero aqui sem validar de novo e o mesmo erro que gerou 107 versoes sem prova
de resultado no projeto original.
"""

# ---------- Ativo e timeframe ----------
# Historico completo de versoes em versionamento.py (era um bloco de 200+
# linhas de comentario aqui, poluindo este arquivo - agora so a versao
# corrente, importada de la).
import os
from pathlib import Path

from versionamento import VERSAO

# Raiz descoberta pela localizacao deste arquivo. Os dados gerados pelo robo
# permanecem junto da instalacao em uso, independentemente do diretorio atual
# do Prompt de Comando.
RAIZ_PROJETO = Path(__file__).resolve().parent
# V506: logs e analises ficam FORA da pasta do robo (que e substituida a cada atualizacao do codigo).
PASTA_DAYTRADE = Path(r"D:\DAYTRADE")
PASTA_LOGS = PASTA_DAYTRADE / "LOGS"          # D:\DAYTRADE\LOGS
PASTA_ANALISE = PASTA_DAYTRADE / "ANALISE"    # D:\DAYTRADE\ANALISE (planilhas do classificacao.py modo A)
PASTA_LOGS_ANTIGA = RAIZ_PROJETO / "logs"     # local ate a V505: copiado 1 vez para PASTA_LOGS na partida

ATIVO = "WINV26"          # contrato vigente - ATUALIZAR a cada rolagem (bimestral, meses pares)
TIMEFRAME_MINUTOS = 15
NOME_TELA_PROFIT = "ProfitPro"  # usado para confirmar foco antes de enviar ordem
# V476 - historico por ano: uma pasta por ano (...\HISTORICO\2023, \2024, ... \2026).
# O ROBO (principal.py) le so a pasta do ano corrente; o BACKTEST (classificacao.py)
# le as pastas de ano sob PASTA_HISTORICO_BACKTEST e deixa escolher os anos.
PASTA_HISTORICO_BACKTEST = r"D:\DAYTRADE\HISTORICO"
CAMINHO_HISTORICO_INICIAL = r"D:\DAYTRADE\HISTORICO\2026\WINFUT_F_0_15min.csv"  # so para a carga UNICA inicial
# V499: o historico que o robo acumula candle a candle fica FORA da pasta do robo, numa pasta
# fixa da maquina. Assim, rodar o script de outra pasta (copia de seguranca, versao de teste)
# usa e alimenta o MESMO historico, sem buraco ao trocar de pasta. Nao use o mesmo arquivo em
# dois robos AO MESMO TEMPO (ordens duplicadas e gravacao concorrente).
PASTA_HISTORICO_ACUMULADO = r"D:\DAYTRADE\HISTORICO\ACUMULADO"
CAMINHO_HISTORICO_PERSISTENTE = str(Path(PASTA_HISTORICO_ACUMULADO) / "historico_acumulado.csv")  # o robo mantem sozinho
CAMINHO_HISTORICO_PERSISTENTE_LEGADO = str(PASTA_LOGS_ANTIGA / "historico_acumulado.csv")  # local antigo (V498 e antes): copiado 1 vez
CAMINHO_ESTADO_RISCO = str(PASTA_LOGS / "estado_risco.json")
GAP_MAXIMO_HORAS_HISTORICO = 48   # se o robo ficar parado mais que isso, o historico
                                   # acumulado e descartado (misturar cenarios de
                                   # mercado tao distantes na mesma media nao faz
                                   # sentido - melhor recomecar do zero)
MODO_TESTE_REPLAY = False  # False = comportamento correto para operacao real continua
                            # (historico acumulado preservado entre execucoes). So mudar
                            # para True manualmente aqui se for fazer teste/replay repetido
                            # do mesmo dia, e lembrar de voltar para False depois.

# V458: RECONCILIAR_OHLC_OFICIAL_NO_REPLAY foi REMOVIDA. A chave trocava, no
# Replay, o OHLC amostrado pelo DDE pelo OHLC consolidado do arquivo - um
# artificio sem equivalente no mercado ao vivo, que fazia o Replay entregar um
# resultado irreproduzivel na operacao real. Em Replay e ao vivo, os candles
# agora vem sempre das leituras do DDE. Ver conselho/2026-09-30-T.txt.

# ---------- Auditoria da execução ao vivo ----------
AUDITORIA_EXECUCAO_ATIVA = True
REGISTRO_PLANILHA_ATIVO = True   # V507: robo escreve cada operacao na aba REGISTRO_OPERACOES (nunca no replay)
PASTA_LOGS_AUDITORIA = str(PASTA_LOGS)

# ---------- Estrategia (regra congelada MA_v2) ----------
MA_RAPIDA = 21            # aritmetica (SMA) - confirmado no Profit
MA_LENTA = 50              # aritmetica (SMA) - confirmado no Profit
TOLERANCIA_TOQUE_PONTOS = 40   # |Fechamento - MA21| <= 40 para considerar "tocou"
BEEP_QUANTIDADE = 3        # V514: quantos beeps seguidos tocar no alerta de pre-entrada
BEEP_SEGUNDOS_ANTES = 5   # toca beep de alerta quando faltar isso (ou menos) para o
                           # fechamento do candle, se o preco ja estiver dentro da faixa
NARRACAO_ANTES_FECHAMENTO_SEGUNDOS = 10  # narra o acompanhamento (tendencia/posicao)
                                          # nos ultimos N segundos antes de CADA fechamento
                                          # de candle, uma vez por candle - nao mais por tempo fixo
                                    # em voz (alem dos eventos de abertura/fechamento)
ALERTA_SAIDA_INTERVALO_SEGUNDOS = 60   # V520/V534: com exaustao sustentada, repete o aviso a cada N segundos (era 10)
ALERTA_SAIDA_ESTABILIDADE_SEGUNDOS = 15   # V534: a voz so anuncia mudanca de nivel que ficou estavel por N segundos
SWING_LOOKBACK_CANDLES = 4      # candles de 15min (1h) usados para o stop estrutural
RELACAO_RISCO_RETORNO = 1.55    # mesmo MIN_RR usado na homologacao da V19 titular

# ---------- Filtros de horario ----------
JANELAS_BLOQUEADAS = [
    ("09:00", "09:20"),   # abertura do pregao
    ("10:15", "10:45"),   # abertura de Nova York
]
HORARIO_BLOQUEIO_NOVAS_ENTRADAS = "18:20"  # so daqui em diante bloqueia ABRIR posicao
                                            # nova - antes disso, mesmo as 18:15, uma
                                            # entrada nova ainda e permitida (tem tempo
                                            # ate o limite real de 18:20)
HORARIO_LIMITE_ABSOLUTO = "18:20:58"   # UNICO horario de saida forcada do projeto -
                                     # forca fechamento aqui, mesmo no prejuizo, e em
                                     # NENHUM outro momento. ATENCAO: sem folga para
                                     # latencia de rede/processamento - risco residual
                                     # de a ordem sair alguns segundos apos o limite
                                     # real da corretora, se a conexao ou o processo
                                     # atrasar. As comparacoes contra este valor
                                     # (motor.verificar_corte_final, o aviso de
                                     # "mercado encerrado" em principal.py) usam
                                     # strftime("%H:%M:%S") - com segundos, igual a
                                     # este valor - nunca "%H:%M" (bug corrigido na
                                     # V445: comparar so por minuto atrasava o corte
                                     # em quase 1 minuto e 2 segundos).
# HORARIO_ULTIMO_CANDLE removida (V445): estava sem uso ha varias versoes (o
# proprio comentario dizia "NAO USADO MAIS") e so criava confusao sobre qual
# horario e "o" corte de saida forcada - a resposta e sempre
# HORARIO_LIMITE_ABSOLUTO, exclusivamente.

# ---------- Gestao de risco (banca atual: R$200 - ajustar conforme o extrato real) ----------
BANCA_ATUAL_REAIS = 200.00   # contador inicial do estado de risco (acumula resultado; persistido em estado_risco.json)
# V461: BANCA REAL na corretora, informada pelo dono em 01/10/2026. E a base do
# limite de risco por operacao (abaixo) - NAO e o contador acima.
BANCA_REAL_REAIS = 1490.00
# V461: se o stop inicial (distancia entrada-stop em reais, + custo) passar desta
# fracao da banca real, a entrada NAO acontece e o robo avisa. Vale tambem no
# backtest (motor.validar_risco_inicial), para ao vivo e laboratorio decidirem
# igual. 0 desliga. Incidente de 01/10: stop de 3.535 pts = R$ 707 (47% da banca
# real, 354% da banca configurada de R$ 200).
# V483: DESLIGADA por decisao do dono (05/10/2026): no backtest 2020-2026 a trava
# custou mais do que evitou (titular: R$ 21.826 com 25% vs R$ 23.679 sem; em 2026
# R$ 15.066 vs R$ 17.494). Risco assumido: uma perda isolada de ate ~R$ 700 (~47%
# da banca real, como em 01/10). Para religar, ponha 0.25 (ou 0.35 / 0.5).
RISCO_MAXIMO_PCT_BANCA = 0
# V462 (achado A do Manus, ata 2026-10-02-Y): quando o stop inicial NAO PODE ser
# verificado (cartucho falhou, nao propôs stop, NaN/inf, texto, ou stop do lado
# errado do preco) o padrao agora e BLOQUEAR a entrada (fail-closed): numa ordem
# real, risco desconhecido nao e risco aceito. False volta ao comportamento da
# V461 (libera). Decisao do dono; vale igual no ao vivo e no backtest.
RISCO_FALHA_FECHADA = True
# V459: MAX_OPERACOES_DIA foi REMOVIDA. Era um teto de CONTAGEM de operacoes
# (2 por pregao) que, medido no motor oficial nos dois periodos, praticamente
# nunca mordia - a estrategia simplesmente nao gera tantas oportunidades:
#
#              pregoes com 1 op   com 2 ops   com 3 ops   4+
#   2026            67,9%           28,5%        3,6%     nenhum
#   2023-2024       68,1%           28,1%        3,9%     nenhum
#
# O teto barrava entrada em 3,6% (5/137) e 3,9% (14/360) dos pregoes operados,
# e a diferenca de resultado ficou dentro da faixa de ruido da Regra 14 nos
# dois periodos, com sinais OPOSTOS: -R$86,98 em 2026 (ruido R$2.183,60) e
# +R$94,02 em 2023-2024 (ruido R$2.580,25). Nenhum pregao chegou a 4 operacoes
# nem sem teto algum - a propria estrategia se limita em 3.
#
# MAX_PERDAS_DIA CONTINUA e e o controle que de fato protege capital: num dia
# ruim o robo ainda para na segunda perda. O teto de contagem so mordia em
# dias que iam BEM (duas operacoes com no maximo uma perda), ou seja, barrava
# justamente a terceira entrada de um pregao saudavel.
# Ver conselho/2026-09-30-U.txt.
MAX_PERDAS_DIA = 2         # ATUALIZADO de 1 para 2: a CLAUDE_HIBRIDA_3_PORTAS_v2
                            # foi validada no laboratorio com MAX_PERDAS_DIA=2 (N=314,
                            # PF=1.89) - rodar com 1 testaria uma regra diferente da
                            # validada. Se trocar de estrategia titular no futuro,
                            # reconferir qual limite foi usado na validacao dela.
VALOR_PONTO_REAIS = 0.20  # fixo, WIN

# V461 - BLOQUEIO DE ENTRADA APOS BURACO NO HISTORICO. Se ao fechar um candle
# faltarem candles do pregao entre o ultimo conhecido e ele, e o arquivo de
# historico nao cobrir o trecho, MA21/MA50/MACD/RSI/ATR/estocastico e o stop
# estrutural ficam calculados sobre uma serie descontinua. Incidente de
# 01/10/2026 (ver conselho/2026-10-01-W.txt): sinal da Porta 2 gerado com
# "Distancia=3006pts" e stop a 3.535 pts (R$ 707) da entrada. Enquanto a
# janela do indicador mais longo (MA50) nao se renovar, NAO abre posicao nova
# (posicao ja aberta continua sendo gerida normalmente).
CANDLES_AQUECIMENTO_APOS_BURACO = 50
BURACO_MAX_CANDLES_PREENCHER = 38   # V498: buraco ate este tamanho (1 pregao = 38 candles) e PREENCHIDO por aproximacao
                                    # (reta entre os precos antes e depois) e as entradas seguem liberadas.
                                    # Acima disso (robo desligado por dias) nao ha base: bloqueia por
                                    # CANDLES_AQUECIMENTO_APOS_BURACO. Para nunca bloquear, ponha um valor enorme.
LEMBRETE_BLOQUEIO_SEGUNDOS = 300   # V498: enquanto as entradas estiverem bloqueadas por buraco, a voz
                                    # lembra a cada 5 min (30 min era pouco: o dono perdeu um dia esperando)
HORARIO_PRIMEIRO_CANDLE = "09:00"   # rotulo do 1o candle do pregao regular
HORARIO_ULTIMO_CANDLE = "18:15"     # rotulo do ultimo candle do pregao regular
# Dias sem pregao em dia util (conferir/atualizar a cada ano). Sem isso, um
# feriado e visto como "pregao inteiro faltando" e bloqueia a 1a entrada depois.
FERIADOS_B3 = {"2026-11-20", "2026-12-25"}

# ---------- Custos reais (Santander Corretora, confirmado na documentacao oficial) ----------
CORRETAGEM_ENCERRAMENTO_AUTOMATICO_APP = 0.00   # gratis, desde que NAO seja via Mesa de Operacoes
EMOLUMENTOS_B3_IDA_VOLTA_REAIS = 0.50
CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS = 0.50

# ---------- Laboratório e classificação V420 ----------
# A pasta principal fica dentro do Robonildo. Durante a migração, a pasta
# antiga também pode ser lida; arquivos com o mesmo nome não são duplicados.
PASTA_ESTRATEGIAS_LABORATORIO = r"laboratorio/estrategias"
PASTA_ESTRATEGIAS_LEGADO = r"D:\DAYTRADE\LABORATORIO\estrategias"
LAB_DIAS_TESTE = 20           # pregões finais usados como bloco recente
LAB_JANELA_PREGOES = 20       # tamanho das janelas móveis de robustez
LAB_PASSO_JANELA = 10         # deslocamento entre janelas
MARGEM_WIN_LABORATORIO = 156.0
LAB_PESO_LONGO = 0.50
LAB_PESO_MENSAL = 0.30
LAB_PESO_DIARIO = 0.20
LAB_MIN_MESES_LONGO = 6
LAB_MIN_MESES_MENSAL = 2
LAB_MIN_PREGOES_MENSAL = 20
LAB_CAMINHO_HISTORICO_AQUECIMENTO = CAMINHO_HISTORICO_PERSISTENTE

# ---------- Notificação por e-mail (abertura/fechamento de posição) ----------
EMAIL_NOTIFICACAO_ATIVO = True   # False = desligado por padrao (opt-in). So liga
                                   # depois de preencher os campos abaixo e testar.
EMAIL_NOTIFICACAO_DESTINATARIO = "marciocubasoares@gmail.com, roselipsoares@gmail.com"  # 
                                                            # resumo de cada operacao vai
EMAIL_NOTIFICACAO_REMETENTE = "marciocubasoares@gmail.com"   # PREENCHER - conta que ENVIA
# Nunca grave senha no arquivo. No Windows, antes de iniciar o robô, use:
#   set ROBONILDO_EMAIL_SENHA_APP=sua_nova_senha_de_app
# A credencial anteriormente presente neste arquivo deve ser revogada.
EMAIL_NOTIFICACAO_SENHA_APP = os.environ.get("ROBONILDO_EMAIL_SENHA_APP", "").strip()
EMAIL_NOTIFICACAO_SERVIDOR_SMTP = "smtp.gmail.com"  # trocar se usar outro provedor
EMAIL_NOTIFICACAO_PORTA_SMTP = 587
EMAIL_NOTIFICACAO_TIMEOUT_SEGUNDOS = 10  # nunca deixa o robo esperando a rede por
                                          # muito tempo - roda em thread separada de
                                          # qualquer forma, mas um timeout curto evita
                                          # a thread ficar pendurada indefinidamente

# ---------- Seguranca operacional ----------
ENVIAR_ORDENS = True
# ATENCAO: este projeto NUNCA envia ordens reais nesta fase.
# Ligar execucao real exige escrever codigo novo em principal.py, nao so mudar este valor.
# Antes disso: validar o robo em paralelo ao acompanhamento manual, confirmar leitura
# de posicao real via DDE (campo CAB), e ter um watchdog independente rodando.
