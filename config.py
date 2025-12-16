"""
Configurações globais do Robonildo.
"""

# ==========================
# SISTEMA / PROFIT
# ==========================

# Nome da janela do Profit que deve estar em foco para capturas e envio de ordens
NOME_TELA_PROFIT = "ProfitPro"

# Quando False, apenas simula as ordens sem enviar os atalhos para o Profit
ENVIAR_ORDENS = True


# ==========================
# REPLAY / SEGURANÇA (mantido)
# ==========================
# Obs: Mesmo removendo regras de horário no main.py, mantemos essas flags
# pois são úteis para bloqueios e governança em REPLAY.

# Em modo REPLAY, ignora TODA regra de horário de pregão
IGNORAR_HORARIO_EM_REPLAY = True

# Em modo REPLAY, bloqueia envio de ordens reais (camada extra de segurança)
BLOQUEAR_ORDENS_EM_REPLAY = True


# ==========================
# COMPORTAMENTO ANALÍTICO
# ==========================

# Confiança mínima para o robô "falar" quando NÃO for decisão de trade (AGUARDAR/MANTER)
# (Trade real: COMPRAR/VENDER/ENCERRAR pode falar sempre)
LIMIAR_FALA_CONFIANCA = 0.70

# Timeframe alvo (referência / para mensagens e governança)
# (o main.py pode continuar usando TIMEFRAME_ANALISE="30m")
TIMEFRAME_OPERACAO_PADRAO = "30M"

# Intervalo mínimo entre comentários de andamento (segundos)
# Você pediu: comentar a cada ~5 minutos
INTERVALO_COMENTARIO_ANDAMENTO = 300


# ==========================
# NARRAÇÃO (TTS) - ROBONILDO
# ==========================

# Backend de narração:
# "auto"   = tenta ElevenLabs e cai para OpenAI se falhar (quota/401/rede)
# "eleven" = força ElevenLabs
# "openai" = força OpenAI
NARRACAO_BACKEND = "openai"

# Cache local (evita gerar áudio repetido)
NARRACAO_CACHE_DIR = r"narracao\cache_audio"

# Anti-spam de narração (segundos)
# Regra prática recomendada:
# - deixe 0.0 se você quer que TRADE (comprar/vender/encerrar) sempre fale
# - e controle a fala de "andamento" pelo INTERVALO_COMENTARIO_ANDAMENTO
NARRACAO_MIN_INTERVAL = 0.0


# ==========================
# ELEVENLABS (opcional)
# ==========================

# Voz padrão do ElevenLabs
ELEVEN_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam

ELEVEN_MODEL_ID = "eleven_multilingual_v2"
ELEVEN_OUTPUT_FORMAT = "mp3_44100_128"

"""
Vozes disponíveis no ElevenLabs (referência rápida)

HOMENS
- Adam      : pNInz6obpgDQGcFmaJgB
- George    : JBFqnCBsd6RMkjVDRZzb
- Brian     : nPczCjzI2devNBz1zQrb
- Roger     : CwhRBWXzGAHq8TQ4Fs17
- Charlie   : IKne3meq5aSn9XLyUdCD
- Callum    : N2lVS1w4EtoT3dr4eOWO
- Harry     : SOYHLrjzK2X1ezoPC6cr
- Eric      : cjVigY5qzO86Huf0OWal
- Chris     : iP95p4xoKVk53GoZ742B
- Daniel    : onwK4e9ZLuTAKqWW03F9
- Bill      : pqHfZKP75CvOlQylNhV4
- Will      : bIHbv24MWmeRgasZH58o
- Liam      : TX3LPaxmHKxFdv7VOQHJ

MULHERES
- River     : SAz9YHcvj6GT2YYXdXww
- Sarah     : EXAVITQu4vr4xnSDxMaL
- Laura     : FGY2WhTYpPnrIDTdsKH5
- Alice     : Xb7hH8MSUJpSbSDYk0k2
- Matilda   : XrExE9yKIg1WjnnlVkGX
- Jessica   : cgSgspJ2msm6clMCkdW9
- Lily      : pFZP5JQG7iQjIQuC4Bku
"""


# ==========================
# OPENAI TTS (principal)
# ==========================

# Modelo de Text-to-Speech da OpenAI
OPENAI_TTS_MODEL = "gpt-4o-mini-tts"

# Voz do narrador oficial (ativa) — decisões de trade
OPENAI_TTS_VOICE = "onyx"

# Voz do comentarista — andamento/contexto pontual
OPENAI_TTS_COMENTARISTA_VOICE = "shimmer"


"""
Vozes disponíveis na OpenAI TTS (válidas atualmente)

NEUTRAS / PADRÃO
- alloy   : neutra, profissional (RECOMENDADA)
- sage    : madura, analítica
- cedar   : grave, autoridade

NARRATIVAS
- verse   : storyteller, análise / replay
- ballad : calma, cadenciada
- fable  : suave, narrativa

ENERGÉTICAS / MODERNAS
- nova    : moderna, energética
- ash     : firme, direta
- onyx    : grave, impacto

EXPRESSIVAS (menos indicadas para trade ao vivo)
- shimmer : brilhante, mais feminina
- coral   : amigável
- echo    : clara, levemente aguda
- marin   : equilibrada
"""
