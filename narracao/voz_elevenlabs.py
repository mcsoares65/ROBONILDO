import re
import hashlib
import threading
from pathlib import Path

from elevenlabs.client import ElevenLabs
from playsound import playsound


def _norm_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _playsound_async(path: str):
    def run():
        try:
            playsound(path)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


class ElevenLabsTTS:
    def __init__(self, api_key: str, voice_id: str, model_id: str, output_format: str, cache_dir: str):
        if not api_key:
            raise RuntimeError("ELEVEN_API_KEY não definido.")

        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id
        self.model_id = model_id
        self.output_format = output_format

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, texto: str) -> Path:
        h = hashlib.md5(f"eleven|{self.voice_id}|{texto}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"eleven_{self.voice_id}_{h}.mp3"

    def falar(self, texto: str):
        texto = _norm_text(texto)
        if not texto:
            return

        p = self._cache_path(texto)
        if p.exists() and p.stat().st_size > 0:
            _playsound_async(str(p))
            return

        audio_stream = self.client.text_to_speech.convert(
            text=texto,
            voice_id=self.voice_id,
            model_id=self.model_id,
            output_format=self.output_format,
        )

        data = b"".join(audio_stream)  # pode lançar ApiError (quota/401 etc)
        p.write_bytes(data)
        _playsound_async(str(p))
