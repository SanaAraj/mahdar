import logging
import threading
from pathlib import Path

from app.config import Settings
from app.shared.errors import TranscriptionError
from app.shared.models import Word

log = logging.getLogger(__name__)

_model = None
_lock = threading.Lock()


def _model_cache_dir(settings: Settings) -> Path:
    return settings.data_dir / "hf"


class LocalTranscriber:
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
    from faster_whisper import WhisperModel

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
