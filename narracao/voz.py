# ARQUIVO: narracao/voz.py
# ROBONILDO_100 — Driver de voz oficial (Adam / ElevenLabs)

    # HOMENS
    #("Adam",    "pNInz6obpgDQGcFmaJgB"),
    #("George",  "JBFqnCBsd6RMkjVDRZzb"),
    #("Brian",   "nPczCjzI2devNBz1zQrb"),
    #("Roger",   "CwhRBWXzGAHq8TQ4Fs17"),
    #("Charlie", "IKne3meq5aSn9XLyUdCD"),
    #("Callum",  "N2lVS1w4EtoT3dr4eOWO"),
    #("Harry",   "SOYHLrjzK2X1ezoPC6cr"),
    #("Eric",    "cjVigY5qzO86Huf0OWal"),
    #("Chris",   "iP95p4xoKVk53GoZ742B"),
    #("Daniel",  "onwK4e9ZLuTAKqWW03F9"),
    #("Bill",    "pqHfZKP75CvOlQylNhV4"),
    #("Will",    "bIHbv24MWmeRgasZH58o"),
    #("Liam",    "TX3LPaxmHKxFdv7VOQHJ"),

    # MULHERES
    #("River",   "SAz9YHcvj6GT2YYXdXww"),
    #("Sarah",   "EXAVITQu4vr4xnSDxMaL"),
    #("Laura",   "FGY2WhTYpPnrIDTdsKH5"),
    #("Alice",   "Xb7hH8MSUJpSbSDYk0k2"),
    #("Matilda", "XrExE9yKIg1WjnnlVkGX"),
    #("Jessica", "cgSgspJ2msm6clMCkdW9"),
    #("Lily",    "pFZP5JQG7iQjIQuC4Bku"),


import os
from elevenlabs.client import ElevenLabs
from elevenlabs import play


class Voz:
    def __init__(self):
        api_key = os.getenv("ELEVEN_API_KEY")
        if not api_key:
            raise RuntimeError("Variável ELEVEN_API_KEY não definida.")

        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam
        #self.voice_id = "SAz9YHcvj6GT2YYXdXww"   # River

    def falar(self, texto: str):
        if not texto:
            return

        audio = self.client.text_to_speech.convert(
            text=texto,
            voice_id=self.voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        play.play(audio)
