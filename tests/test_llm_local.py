"""The Ollama local extractor against a mocked OpenAI-compatible endpoint.

The local extractor must reuse every shared guard (schema retry, Arabic-output
retry, reasoning stripper, budgets) while skipping the Groq key and the live
/models preflight. All HTTP is respx-mocked; no model is ever downloaded.
"""

import json

import httpx
import pytest
import respx

from backend.app.core.errors import AnalysisError
from backend.app.core.models import Analysis, MeetingMeta, Sentence, Speaker, Topic
from backend.app.providers.llm_local import LocalMinutesExtractor

META = MeetingMeta(date_gregorian="2026-08-18", date_hijri="1448-03-05", duration_s=95.0)
SENTENCES = [
    Sentence(id="s1", start=0.0, end=4.0, text="نراجع خطة العمل اليوم.", speaker="SPEAKER_00"),
    Sentence(id="s2", start=5.0, end=9.0, text="سأرفع التقرير غدًا.", speaker="SPEAKER_01"),
]
SPEAKERS = [
    Speaker(id="SPEAKER_00", label="المدير", first_start=0.0),
    Speaker(id="SPEAKER_01", label="سارة", first_start=5.0),
]

ARABIC_JSON = json.dumps(
    {
        "title": "متابعة خطة العمل",
        "attendees": ["المدير", "سارة"],
        "topics": [
            {"title": "خطة العمل", "summary": "مراجعة خطة العمل اليومية", "segment_ids": ["s1"]}
        ],
        "decisions": [],
        "directives": [],
        "tasks": [
            {
                "description": "رفع التقرير",
                "owner": "سارة",
                "due": {"raw": "غدًا", "gregorian": "2026-08-19"},
                "priority": None,
                "segment_ids": ["s2"],
            }
        ],
    },
    ensure_ascii=False,
)

ENGLISH_ONLY_JSON = json.dumps(
    {
        "title": "Work plan review",
        "attendees": ["Manager"],
        "topics": [{"title": "Plan", "summary": "Review of the plan", "segment_ids": ["s1"]}],
        "decisions": [],
        "directives": [],
        "tasks": [],
    },
    ensure_ascii=False,
)

BASE_URL = "http://ollama:11434/v1"
CHAT_URL = BASE_URL + "/chat/completions"


def _settings(**overrides):
    base = {"llm_provider": "local", "local_llm_model": "qwen3:8b", "ollama_url": BASE_URL}
    base.update(overrides)
    from backend.app.config import Settings

    return Settings(**base)


def _envelope(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


@respx.mock
def test_local_extract_hits_ollama_without_auth_or_preflight():
    route = respx.post(CHAT_URL).mock(return_value=httpx.Response(200, json=_envelope(ARABIC_JSON)))
    models_route = respx.get(f"{BASE_URL}/models").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    result = LocalMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert result.title == "متابعة خطة العمل"
    assert route.called, "the local chat endpoint must be called"
    request = route.calls[0].request
    assert "authorization" not in request.headers  # Ollama serves with no auth
    body = json.loads(request.content)
    assert body["model"] == "qwen3:8b"
    assert "include_reasoning" not in body  # local endpoint never got the flag
    assert not models_route.called  # no /models preflight on the local path


@respx.mock
def test_local_extractor_runs_no_network_before_a_post():
    """Unlike Groq, extract must not gate on a key or a preflight listing."""
    route = respx.post(CHAT_URL).mock(return_value=httpx.Response(200, json=_envelope(ARABIC_JSON)))
    # No /models route registered at all: any preflight would raise ConnectError.
    LocalMinutesExtractor(_settings(groq_api_key="")).extract(META, SENTENCES, SPEAKERS)
    assert route.called


@respx.mock
def test_local_arabic_guard_retries_once_then_fails():
    route = respx.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(200, json=_envelope(ENGLISH_ONLY_JSON)),
            httpx.Response(200, json=_envelope(ENGLISH_ONLY_JSON)),
        ]
    )
    with pytest.raises(AnalysisError) as exc:
        LocalMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert exc.value.message_key == "analysis.failed"
    assert len(route.calls) == 2


@respx.mock
def test_local_schema_retry_then_success():
    route = respx.post(CHAT_URL).mock(
        side_effect=[
            httpx.Response(200, json=_envelope('{"title": 42}')),
            httpx.Response(200, json=_envelope(ARABIC_JSON)),
        ]
    )
    result = LocalMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert result.title == "متابعة خطة العمل"
    assert len(route.calls) == 2


@respx.mock
def test_local_reasoning_tags_are_stripped():
    content = "<think>some chain of thought</think>" + ARABIC_JSON
    respx.post(CHAT_URL).mock(return_value=httpx.Response(200, json=_envelope(content)))
    result = LocalMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert isinstance(result, Analysis)
    assert result.title == "متابعة خطة العمل"


@respx.mock
def test_local_unreachable_maps_to_clear_message():
    respx.post(CHAT_URL).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(AnalysisError) as exc:
        LocalMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert exc.value.message_key == "local_llm.unavailable"


@respx.mock
def test_local_5xx_maps_to_unavailable():
    three_500s = [httpx.Response(500), httpx.Response(500), httpx.Response(500)]
    respx.post(CHAT_URL).mock(side_effect=three_500s)
    with pytest.raises(AnalysisError) as exc:
        LocalMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert exc.value.message_key == "local_llm.unavailable"


def test_has_arabic_output_guard_semantics_unchanged():
    # The guard the local path reuses treats an Arabic title as grounded.
    assert_ = Analysis(title="اجتماع", topics=[Topic(title="خطة", summary="مراجعة")])
    from backend.app.providers.llm_parse import has_arabic_output

    assert has_arabic_output(assert_) is True
