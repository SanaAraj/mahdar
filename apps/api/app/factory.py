import logging

from app.config import Settings
from app.features.analysis.llm_groq import GroqMinutesExtractor
from app.features.analysis.llm_local import LocalMinutesExtractor
from app.features.transcription.stt_cohere import CohereTranscriber
from app.features.transcription.stt_groq import GroqTranscriber
from app.features.transcription.stt_local import LocalTranscriber
from app.shared.errors import AnalysisError, TranscriptionError
from app.shared.protocols import MinutesExtractor, Transcriber

log = logging.getLogger(__name__)

_VALID_STT_PROVIDERS: frozenset[str] = frozenset({"groq", "cohere", "local"})
_VALID_LLM_PROVIDERS: frozenset[str] = frozenset({"groq", "local"})


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
    if provider == "cohere":
        return CohereTranscriber(settings)
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


def validate_providers(settings: Settings) -> None:

    for key, value, valid in (
        ("STT_PROVIDER", settings.stt_provider, _VALID_STT_PROVIDERS),
        ("LLM_PROVIDER", settings.llm_provider, _VALID_LLM_PROVIDERS),
    ):
        if value.strip().lower() not in valid:
            log.error(
                "%s has unknown value %r; expected one of %s",
                key,
                value,
                ", ".join(sorted(valid)),
            )
