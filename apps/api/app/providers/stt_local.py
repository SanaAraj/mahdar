"""Local speech-to-text via faster-whisper (offline fallback for Groq STT).

The model (LOCAL_STT_MODEL, default large-v3-turbo) runs on CPU at int8 with
word-level timestamps, fixed to Arabic, and with the VAD filter on so local
silence no longer feeds Whisper's hallucination failure mode the way a cloud
upload does. Word structure matches what the pipeline consumes from Groq, so
sentence assembly and speaker overlap assign unchanged. faster_whisper imports
lazily inside the build so app startup and the test suite never touch the
package when a real run is not requested.
"""

import logging
import threading
from pathlib import Path

from app.config import Settings
from app.core.errors import TranscriptionError
from app.core.models import Word

log = logging.getLogger(__name__)

_model = None
_lock = threading.Lock()


def _model_cache_dir(settings: Settings) -> Path:
    return settings.data_dir / "hf"


class LocalTranscriber:
    """Transcribes the 16 kHz mono WAV locally through faster-whisper.

    The cloud transcriber's per-file cap and silence-splitting exist only
    because Groq enforces a 25 MB upload limit; a local engine reads the file
    directly, so no split happens here and the one wav path is used.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def transcribe(self, wav_path: Path, mp3_path: Path) -> list[Word]:
        model = self._load()
        try:
            segments, _info = model.transcribe(
                str(wav_path),
                language="ar",
                word_timestamps=True,
                vad_filter=True,
            )
            words = [
                Word(start=round(w.start, 3), end=round(w.end, 3), text=w.word.strip())
                for segment in segments
                for w in (segment.words or [])
                if w.word and w.word.strip() and w.end > w.start
            ]
        except Exception as exc:
            raise TranscriptionError("local_stt.failed", f"faster-whisper: {exc}") from exc
        if not words:
            raise TranscriptionError("transcription.empty", "no words from local STT")
        return words

    def _load(self):
        global _model
        if _model is not None:
            return _model
        with _lock:
            if _model is None:
                _model = _build_model(self._settings)
        return _model


def _build_model(settings: Settings):
    from faster_whisper import WhisperModel  # lazy import keeps startup fast

    cache = _model_cache_dir(settings)
    cache.mkdir(parents=True, exist_ok=True)
    try:
        model = WhisperModel(
            settings.local_stt_model,
            device="cpu",
            compute_type="int8",
            download_root=str(cache),
        )
    except Exception as exc:
        raise TranscriptionError("local_stt.failed", f"model load: {exc}") from exc
    log.info("Local STT model loaded: %s", settings.local_stt_model)
    return model
