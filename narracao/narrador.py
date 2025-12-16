# narracao/narrador.py
import time

class Narrador:
    """
    Narrador com controle de cooldown.
    Suporta múltiplas instâncias (ex: NARRADOR, TECNICO, FLUXO).
    """

    def __init__(self, voz, cooldown: float = 2.0, nome: str = "NARRADOR"):
        self.voz = voz
        self.cooldown = float(cooldown)
        self.nome = nome
        self._ultimo_ts = 0.0

    def falar(self, texto: str, force: bool = False):
        if not texto:
            return

        agora = time.time()

        if not force:
            if self.cooldown > 0 and (agora - self._ultimo_ts) < self.cooldown:
                return

        self._ultimo_ts = agora

        try:
            print(f"[{self.nome}] {texto}")
            # IMPORTANTE: VozSeletor NÃO recebe kwargs
            self.voz.falar(texto)
        except Exception as e:
            print(f"[{self.nome}][ERRO_TTS] {repr(e)}")
