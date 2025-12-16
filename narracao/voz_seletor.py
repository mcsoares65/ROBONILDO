import os
import time
import traceback
import config

from narracao.voz_openai import OpenAITTS
from narracao.voz_elevenlabs import ElevenLabsTTS


def _is_quota_or_auth_error(exc: Exception) -> bool:
    msg = repr(exc).lower()
    return (
        "quota_exceeded" in msg
        or ("status_code" in msg and "401" in msg)
        or "unauthorized" in msg
        or "forbidden" in msg
    )


class VozSeletor:
    """
    Seleciona backend de narração baseado no config.py
    Estrutura PLANA (sem backends/)

    Importante:
    - falar() agora aceita force=True (para compatibilidade com Narrador / main).
    """

    def __init__(self):
        self.backend = (getattr(config, "NARRACAO_BACKEND", "auto") or "auto").strip().lower()
        self.cache_dir = getattr(config, "NARRACAO_CACHE_DIR", r"narracao\cache_audio")
        self.min_interval = float(getattr(config, "NARRACAO_MIN_INTERVAL", 0.0) or 0.0)
        self._last_play = 0.0

        self.openai = None
        self.eleven = None

        # -------- OpenAI --------
        if self.backend in ("auto", "openai"):
            try:
                self.openai = OpenAITTS(
                    model=config.OPENAI_TTS_MODEL,
                    voice=config.OPENAI_TTS_VOICE,
                    cache_dir=self.cache_dir,
                )
                print(f"[NARRADOR] OpenAI inicializado (voz={config.OPENAI_TTS_VOICE})")
            except Exception:
                print("[NARRADOR][ERRO] Falha REAL ao inicializar OpenAI TTS:")
                traceback.print_exc()
                self.openai = None

        # -------- ElevenLabs --------
        if self.backend in ("auto", "eleven"):
            try:
                self.eleven = ElevenLabsTTS(
                    api_key=os.getenv("ELEVEN_API_KEY"),
                    voice_id=config.ELEVEN_VOICE_ID,
                    model_id=config.ELEVEN_MODEL_ID,
                    output_format=config.ELEVEN_OUTPUT_FORMAT,
                    cache_dir=self.cache_dir,
                )
                print("[NARRADOR] ElevenLabs inicializado")
            except Exception:
                print("[NARRADOR][ERRO] Falha REAL ao inicializar ElevenLabs:")
                traceback.print_exc()
                self.eleven = None

        # -------- Validação --------
        if self.backend == "openai" and not self.openai:
            raise RuntimeError("Backend openai selecionado, mas OpenAI TTS não inicializou.")

        if self.backend == "eleven" and not self.eleven:
            raise RuntimeError("Backend eleven selecionado, mas ElevenLabs não inicializou.")

        if self.backend == "auto" and not self.openai and not self.eleven:
            raise RuntimeError("Modo auto: nenhum backend de narração inicializou.")

    def _hot_reload_openai(self):
        """
        Se você muda config.OPENAI_TTS_VOICE durante a execução (onyx/shimmer/sage),
        isso atualiza a instância sem precisar recriar.
        """
        if not self.openai:
            return
        try:
            self.openai.set_voice(config.OPENAI_TTS_VOICE)
            self.openai.set_model(config.OPENAI_TTS_MODEL)
        except Exception:
            pass

    def falar(self, texto: str, force: bool = False, **_kwargs):
        """
        force=True ignora anti-spam do min_interval.
        **_kwargs absorve parâmetros extras (evita quebrar chamadas antigas).
        """
        if not texto:
            return

        # Anti-spam opcional (exceto force)
        if (not force) and self.min_interval > 0:
            now = time.time()
            if (now - self._last_play) < self.min_interval:
                return
            self._last_play = now
        else:
            # mesmo com force, atualiza relógio para evitar flood involuntário
            self._last_play = time.time()

        # Atualiza voz/model se mudou no config
        self._hot_reload_openai()

        if self.backend == "openai":
            return self.openai.falar(texto)

        if self.backend == "eleven":
            return self.eleven.falar(texto)

        # auto
        if self.openai:
            try:
                return self.openai.falar(texto)
            except Exception as e:
                if self.eleven and _is_quota_or_auth_error(e):
                    return self.eleven.falar(texto)
                raise

        if self.eleven:
            return self.eleven.falar(texto)
