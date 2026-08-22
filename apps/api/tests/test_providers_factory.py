import logging

import pytest

from app import factory
from app.config import Settings
from app.features.analysis.llm_groq import GroqMinutesExtractor
from app.features.analysis.llm_local import LocalMinutesExtractor
from app.features.transcription.stt_cohere import CohereTranscriber
from app.features.transcription.stt_groq import GroqTranscriber
from app.features.transcription.stt_local import LocalTranscriber
from app.shared.errors import AnalysisError, TranscriptionError


def _settings(**overrides) -> Settings:
    base = {"groq_api_key": "key", "stt_provider": "groq", "llm_provider": "groq"}
    base.update(overrides)
    return Settings(**base)


def test_defaults_select_groq():
    transcriber = factory.build_transcriber(_settings())
    extractor = factory.build_extractor(_settings())
    assert isinstance(transcriber, GroqTranscriber)
    assert isinstance(extractor, GroqMinutesExtractor)


def test_local_selects_local_providers():
    s = _settings(stt_provider="local", llm_provider="local")
    assert isinstance(factory.build_transcriber(s), LocalTranscriber)
    extractor = factory.build_extractor(s)
    assert isinstance(extractor, LocalMinutesExtractor)
    assert isinstance(extractor, GroqMinutesExtractor)


def test_cohere_selects_cohere_stt_and_keeps_groq_llm():
    settings = _settings(stt_provider="cohere", cohere_api_key="key")
    assert isinstance(factory.build_transcriber(settings), CohereTranscriber)
    assert isinstance(factory.build_extractor(settings), GroqMinutesExtractor)


def test_selection_is_case_insensitive_and_trimmed():
    s = _settings(stt_provider="  LOCAL ")
    assert isinstance(factory.build_transcriber(s), LocalTranscriber)


def test_unknown_stt_provider_raises_in_the_stage():
    transcriber = factory.build_transcriber(_settings(stt_provider="acme-stt"))
    with pytest.raises(TranscriptionError) as exc:
        transcriber.transcribe(None, None)
    assert exc.value.message_key == "config.unknown_provider"


def test_unknown_llm_provider_raises_in_the_stage():
    extractor = factory.build_extractor(_settings(llm_provider="acme-llm"))
    with pytest.raises(AnalysisError) as exc:
        extractor.extract(None, [], [])
    assert exc.value.message_key == "config.unknown_provider"


def test_validate_providers_logs_unknown_values(caplog):
    with caplog.at_level(logging.ERROR, logger="app.factory"):
        factory.validate_providers(_settings(stt_provider="bad", llm_provider="bad2"))
    assert "STT_PROVIDER" in caplog.text and "LLM_PROVIDER" in caplog.text


def test_validate_providers_is_quiet_for_valid(caplog):
    with caplog.at_level(logging.ERROR, logger="app.factory"):
        factory.validate_providers(_settings())
        factory.validate_providers(_settings(stt_provider="cohere"))
    assert caplog.text == ""
