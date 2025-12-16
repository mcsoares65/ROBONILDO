from narracao.voz_seletor import VozSeletor
import config

config.OPENAI_TTS_VOICE = "onyx"
voz = VozSeletor()
voz.falar("Teste de áudio do Robonildo. Se você ouvir isso, está tudo certo.")
