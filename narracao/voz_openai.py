import os
import time
import threading
import traceback
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import config

# OpenAI SDK (novo)
from openai import OpenAI


# =========================
# PLAYER GLOBAL (pygame)
# =========================

_PYGAME_OK = False
_PYGAME_ERR = None
_PYGAME_LOCK = threading.Lock()
_LAST_TEMP_FILES = []  # limpeza best-effort


def _ensure_pygame():
    global _PYGAME_OK, _PYGAME_ERR
    if _PYGAME_OK:
        return True
    if _PYGAME_ERR is not None:
        return False

    try:
        import pygame

        # mixer pré-inicializado tende a ser mais estável
        # (sem parâmetros = deixa pygame escolher melhor driver)
        pygame.mixer.init()
        _PYGAME_OK = True
        print("[AUDIO] pygame.mixer inicializado com sucesso.")
        return True
    except Exception as e:
        _PYGAME_ERR = e
        print("[AUDIO][ERRO] Falha ao inicializar pygame.mixer:")
        traceback.print_exc()
        return False


def _cleanup_temp_files(max_keep=10):
    """
    Evita acumular arquivos temporários no cache.
    Mantém somente os últimos `max_keep`.
    """
    try:
        while len(_LAST_TEMP_FILES) > max_keep:
            p = _LAST_TEMP_FILES.pop(0)
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
    except Exception:
        pass


def _play_mp3_file(path_mp3: Path):
    """
    Toca o MP3 via arquivo (mais estável que BytesIO no Windows).
    """
    if not _ensure_pygame():
        return

    try:
        import pygame

        with _PYGAME_LOCK:
            try:
                # se algo estiver tocando, interrompe para não empilhar
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
            except Exception:
                pass

            pygame.mixer.music.load(str(path_mp3))
            pygame.mixer.music.play()
    except Exception:
        print("[AUDIO][ERRO] Falha ao tocar MP3:")
        traceback.print_exc()


def _play_mp3_bytes_async(mp3_bytes: bytes, cache_dir: str):
    """
    Salva bytes -> arquivo temp -> toca -> remove.
    Thread NÃO daemon para permitir testes simples (script finalizar) ainda tocar.
    """
    def _job():
        try:
            cache_path = Path(cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)

            tmp_name = f"tts_{uuid4().hex}.mp3"
            tmp_path = cache_path / tmp_name

            # grava arquivo
            tmp_path.write_bytes(mp3_bytes)

            # registra p/ limpeza
            _LAST_TEMP_FILES.append(tmp_path)
            _cleanup_temp_files(max_keep=25)

            # toca
            _play_mp3_file(tmp_path)

            # espera terminar para remover (best-effort)
            try:
                import pygame
                t0 = time.time()
                while True:
                    with _PYGAME_LOCK:
                        busy = pygame.mixer.music.get_busy()
                    if not busy:
                        break
                    # hard timeout de segurança (evita travar thread para sempre)
                    if (time.time() - t0) > 30:
                        break
                    time.sleep(0.05)
            except Exception:
                pass

            # remove
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass

        except Exception:
            print("[AUDIO][ERRO] Exceção no worker de áudio:")
            traceback.print_exc()

    th = threading.Thread(target=_job, daemon=False)
    th.start()


def _norm_text(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    # evita textos gigantes (trade ao vivo)
    if len(s) > 350:
        s = s[:350].rstrip() + "..."
    return s


class OpenAITTS:
    """
    TTS via OpenAI.
    Usa pygame para playback local.
    """

    def __init__(self, model: str, voice: str, cache_dir: str):
        self.model = model
        self.voice = voice
        self.cache_dir = cache_dir
        self.client = OpenAI()

    def set_voice(self, voice: str):
        if voice:
            self.voice = str(voice).strip()

    def set_model(self, model: str):
        if model:
            self.model = str(model).strip()

    def falar(self, texto: str):
        texto = _norm_text(texto)
        if not texto:
            return

        try:
            speech = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=texto,
            )

            mp3_bytes = speech.read()

            # toca async (mas thread NÃO-daemon, então teste não morre antes)
            _play_mp3_bytes_async(mp3_bytes, cache_dir=self.cache_dir)

        except Exception:
            print("[TTS][ERRO] Falha ao gerar/tocar TTS OpenAI:")
            traceback.print_exc()
