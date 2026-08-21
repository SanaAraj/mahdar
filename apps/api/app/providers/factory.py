"""Provider factory: selects the concrete providers from the env selectors.

STT_PROVIDER and LLM_PROVIDER each accept "groq" (the cloud default) or
"local" (the offline fallback). An unknown value never crashes app startup:
the factory returns a stub whose stage call raises the config error, so the
pipeline records a clear Arabic message on the failed stage exactly like any
other stage failure.
"""

import logging

from app.config import Settings
from app.core.errors import AnalysisError, TranscriptionError
from app.providers.base import MinutesExtractor, Transcriber
from app.providers.llm_groq import GroqMinutesExtractor
from app.providers.llm_local import LocalMinutesExtractor
from app.providers.stt_groq import GroqTranscriber
from app.providers.stt_local import LocalTranscriber

log = logging.getLogger(__name__)

_VALID_PROVIDERS: frozenset[str] = frozenset({"groq", "local"})


class _UnknownTranscriber:
    """Stage-facing stub for an unrecognized STT_PROVIDER value."""

    def __init__(self, value: str) -> None:
        self._value = value

    def transcribe(self, wav_path, mp3_path):
        raise TranscriptionError("config.unknown_provider", f"STT_PROVIDER={self._value!r}")


class _UnknownExtractor:
    """Stage-facing stub for an unrecognized LLM_PROVIDER value."""

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
    """Boot-time log line so an unknown selector is visible before any job runs."""
    for key, value in (
        ("STT_PROVIDER", settings.stt_provider),
        ("LLM_PROVIDER", settings.llm_provider),
    ):
        if value.strip().lower() not in _VALID_PROVIDERS:
            log.error("%s has unknown value %r; expected one of groq or local", key, value)
