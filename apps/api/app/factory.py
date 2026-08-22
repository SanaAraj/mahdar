import logging

from app.config import Settings
from app.features.analysis.llm_groq import GroqMinutesExtractor
from app.features.analysis.llm_local import LocalMinutesExtractor
from app.features.transcription.stt_groq import GroqTranscriber
from app.features.transcription.stt_local import LocalTranscriber
from app.shared.errors import AnalysisError, TranscriptionError
from app.shared.protocols import MinutesExtractor, Transcriber

log = logging.getLogger(__name__)

_VALID_PROVIDERS: frozenset[str] = frozenset({"groq", "local"})


class _UnknownTranscriber:
    def __init__(self, value: str) -> None:
        self._value = value

    def transcribe(self, wav_path, mp3_path):
        raise TranscriptionError("config.unknown_provider", f"STT_PROVIDER={self._value!r}")


class _UnknownExtractor:
    def __init__(self, value: str) -> None:
        self._value = value

    def extract(self, meta, sentences, speakers, job_id=None):
        raise AnalysisError("config.unknown_provider", f"LLM_PROVIDER={self._value!r}")


def build_transcriber(settings: Settings) -> Transcriber:
    provider = settings.stt_provider.strip().lower()
    if provider == "groq":
        return GroqTranscriber(settings)
    if provider == "local":
        return LocalTranscriber(settings)
    log.error("Unknown STT_PROVIDER %r; the transcribe stage will fail", settings.stt_provider)
    return _UnknownTranscriber(settings.stt_provider)


def build_extractor(settings: Settings) -> MinutesExtractor:
    provider = settings.llm_provider.strip().lower()
    if provider == "groq":
        return GroqMinutesExtractor(settings)
    if provider == "local":
        return LocalMinutesExtractor(settings)
    log.error("Unknown LLM_PROVIDER %r; the analyze stage will fail", settings.llm_provider)
    return _UnknownExtractor(settings.llm_provider)


def _validate_providers(settings: Settings) -> None:

    for key, value in (
        ("STT_PROVIDER", settings.stt_provider),
        ("LLM_PROVIDER", settings.llm_provider),
    ):
        if value.strip().lower() not in _VALID_PROVIDERS:
            log.error("%s has unknown value %r; expected one of groq or local", key, value)
