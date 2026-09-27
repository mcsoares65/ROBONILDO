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

from versionamento import VERSAO
ATIVO = "WINV26"          # contrato vigente - ATUALIZAR a cada rolagem (bimestral, meses pares)
TIMEFRAME_MINUTOS = 15
NOME_TELA_PROFIT = "ProfitPro"  # usado para confirmar foco antes de enviar ordem
CAMINHO_HISTORICO_INICIAL = r"D:\DAYTRADE\HISTORICO\WINFUT_F_0_15min.csv"  # so para a carga UNICA inicial
CAMINHO_HISTORICO_PERSISTENTE = r"D:\DAYTRADE\ROBONILDO\logs\historico_acumulado.csv"  # o robo mantem sozinho
GAP_MAXIMO_HORAS_HISTORICO = 48   # se o robo ficar parado mais que isso, o historico
                                   # acumulado e descartado (misturar cenarios de
                                   # mercado tao distantes na mesma media nao faz
                                   # sentido - melhor recomecar do zero)
MODO_TESTE_REPLAY = False  # False = comportamento correto para operacao real continua
                            # (historico acumulado preservado entre execucoes). So mudar
                            # para True manualmente aqui se for fazer teste/replay repetido
                            # do mesmo dia, e lembrar de voltar para False depois.

# Atua somente quando a pergunta inicial for respondida com REPLAY. Em NORMAL,
# os candles continuam sendo montados pelas leituras ao vivo do DDE.
RECONCILIAR_OHLC_OFICIAL_NO_REPLAY = True

# ---------- Auditoria da execução ao vivo ----------
AUDITORIA_EXECUCAO_ATIVA = True
PASTA_LOGS_AUDITORIA = "logs"

# ---------- Estrategia (regra congelada MA_v2) ----------
MA_RAPIDA = 21            # aritmetica (SMA) - confirmado no Profit
MA_LENTA = 50              # aritmetica (SMA) - confirmado no Profit
TOLERANCIA_TOQUE_PONTOS = 40   # |Fechamento - MA21| <= 40 para considerar "tocou"
BEEP_SEGUNDOS_ANTES = 5   # toca beep de alerta quando faltar isso (ou menos) para o
                           # fechamento do candle, se o preco ja estiver dentro da faixa
NARRACAO_ANTES_FECHAMENTO_SEGUNDOS = 10  # narra o acompanhamento (tendencia/posicao)
                                          # nos ultimos N segundos antes de CADA fechamento
                                          # de candle, uma vez por candle - nao mais por tempo fixo
                                    # em voz (alem dos eventos de abertura/fechamento)
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
BANCA_ATUAL_REAIS = 200.00
MAX_OPERACOES_DIA = 2      # padrao de seguranca - a pergunta feita no inicio do
MAX_PERDAS_DIA = 2         # script (ambiente REAL/SIMULADO) pode ampliar isso
                            # ATUALIZADO de 1 para 2: a CLAUDE_HIBRIDA_3_PORTAS_v2
                            # foi validada no laboratorio com MAX_PERDAS_DIA=2 (N=314,
                            # PF=1.89) - rodar com 1 testaria uma regra diferente da
                            # validada. Se trocar de estrategia titular no futuro,
                            # reconferir qual limite foi usado na validacao dela.
                            # temporariamente so na sessao atual, sem alterar
                            # este arquivo nem exigir lembrar de reverter nada
VALOR_PONTO_REAIS = 0.20  # fixo, WIN

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
EMAIL_NOTIFICACAO_DESTINATARIO = "marciocubasoares@gmail.com, roselipsoares@gmail.com, marcosalink@gmail.com"  # PREENCHER - para onde o
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
