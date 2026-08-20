"""Tests for the prompt builder, the reply cleaner, and the Groq analysis provider
(all network access is mocked)."""

import json
import re

import httpx
import pytest
import respx
from pydantic import ValidationError

from backend.app import constants
from backend.app.config import Settings
from backend.app.core.errors import AnalysisError
from backend.app.core.models import Analysis, MeetingMeta, Sentence, Speaker, Topic
from backend.app.providers import prompts
from backend.app.providers.llm_groq import (
    GroqMinutesExtractor,
    _has_arabic_output,
    _json_object,
    strip_reasoning,
)

META = MeetingMeta(date_gregorian="2026-08-18", date_hijri="1448-03-05", duration_s=125.0)
SENTENCES = [
    Sentence(id="s1", start=0.0, end=4.0, text="نراجع خطة العمل اليوم.", speaker="SPEAKER_00"),
    Sentence(id="s2", start=5.0, end=9.0, text="سأرفع التقرير غدًا.", speaker="SPEAKER_01"),
]
SPEAKERS = [
    Speaker(id="SPEAKER_00", label="المدير", first_start=0.0),
    Speaker(id="SPEAKER_01", label="سارة", first_start=5.0),
]

ANALYSIS_JSON = json.dumps(
    {
        "title": "متابعة خطة العمل",
        "attendees": ["المدير", "سارة"],
        "topics": [],
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


def _settings(key="test-key", model=constants.DEFAULT_LLM_MODEL) -> Settings:
    return Settings(groq_api_key=key, groq_llm_model=model)


def _envelope(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def _models_payload(*ids: str) -> dict:
    return {"data": [{"id": i} for i in ids]}


@pytest.fixture(autouse=True)
def _reset_llm_caches(monkeypatch):
    """Each test starts with a cold models cache and the reasoning flag on."""
    monkeypatch.setattr("backend.app.providers.llm_preflight._models_cache", None)
    monkeypatch.setattr("backend.app.providers.llm_groq._include_reasoning_supported", True)
    monkeypatch.setattr(constants, "HTTP_JITTER_S", 0)  # deterministic sleep assertions
    yield


def _ready_models(model):
    """Make the configured model appear in the preflight listing."""
    respx.get(constants.GROQ_API_BASE + constants.MODELS_API_PATH).mock(
        return_value=httpx.Response(200, json=_models_payload(model))
    )


def _ready_posts(*responses):
    """Register the chat endpoint and return its route for assertions."""
    if len(responses) == 1:
        return respx.post(constants.GROQ_API_BASE + constants.LLM_API_PATH).mock(
            return_value=responses[0]
        )
    return respx.post(constants.GROQ_API_BASE + constants.LLM_API_PATH).mock(
        side_effect=list(responses)
    )


# ---------- building the user message ----------


def test_user_message_header_and_lines():
    msg = prompts.build_user_message(META, SENTENCES, SPEAKERS)
    assert "2026-08-18" in msg and "1448-03-05" in msg
    assert "المدة: 02:05" in msg
    assert "المتحدثون: المدير، سارة" in msg
    assert "[s1] المدير (00:00): نراجع خطة العمل اليوم." in msg
    assert "[s2] سارة (00:05): سأرفع التقرير غدًا." in msg


def test_user_message_without_speakers():
    bare = [
        Sentence(id=f"s{i + 1}", start=float(i * 10), end=float(i * 10) + 5, text=f"جملة {i}.")
        for i in range(2)
    ]
    msg = prompts.build_user_message(META, bare, [])
    assert "المتحدثون: غير محددين (لم يجر فصل المتحدثين)" in msg
    assert "[s1] (00:00): جملة 0." in msg
    # The raw SPEAKER_00 id never leaks when the speaker list is absent.
    assert "SPEAKER_00" not in msg


def test_format_clock_hours():
    assert prompts.format_clock(3661) == "01:01:01"
    assert prompts.format_clock(125) == "02:05"
    assert prompts.format_clock(-3) == "00:00"


def test_system_prompt_holds_hard_rules():
    # The schema field names survive in the English contract.
    for token in ("segment_ids", "raw", "gregorian", "attendees"):
        assert token in prompts.SYSTEM_PROMPT
    # The rules themselves are English (instruction-following surface).
    assert "faithful" in prompts.SYSTEM_PROMPT
    assert "priority" in prompts.SYSTEM_PROMPT


def test_system_prompt_keeps_arabic_exemplars_only():
    # Arabic survives only as embedded exemplars inside the English rules.
    assert "غدًا" in prompts.SYSTEM_PROMPT
    assert "نحتاج إلى رفع التقرير قبل نهاية الشهر" in prompts.SYSTEM_PROMPT
    assert "عالية" in prompts.SYSTEM_PROMPT
    assert "15 شعبان 1448" in prompts.SYSTEM_PROMPT
    # The old Arabic instruction phrases were retired for English rules.
    assert "لا تخترع قرارًا" not in prompts.SYSTEM_PROMPT
    assert "الأولوية" not in prompts.SYSTEM_PROMPT


def test_arabic_output_message_is_english_instruction():
    msg = prompts.build_arabic_output_message()
    assert "Arabic" in msg
    assert "JSON only" in msg


def test_prompt_budget_guard():
    """An over-budget user message raises before any network call."""
    bloated = "س " * 20000
    with pytest.raises(AnalysisError) as exc:
        prompts.ensure_within_budget(bloated)
    assert exc.value.message_key == "analysis.too_long"
    # The estimate that tripped the guard is over the budget, not just nonzero.
    total = prompts.estimate_tokens(prompts.SYSTEM_PROMPT) + prompts.estimate_tokens(bloated)
    assert total > constants.MAX_PROMPT_TOKENS


# ---------- the JSON reply cleaner ----------


def test_think_tags_strip_to_clean_output():
    """Regression: a corrupted _THINK_RE must fail here, not pass silently.

    A reasoning model wraps its chain-of-thought in `<think>...</think>`
    before the JSON object. The stripper must remove the whole tag so the
    cleaner sees only the JSON; any wording or formatting change that breaks
    the pattern would leave literal reasoning text or tags in the result, and
    this test would fail.
    """
    crafted = (
        "<think>I should consider the user's intent carefully.\n"
        "Let me think about the schema on a second line.</think>"
        '{"title": "محضر", "attendees": [], "topics": [], "decisions": [], '
        '"directives": [], "tasks": []}'
    )
    # Feed the crafted reasoning-tagged payload through the stripper itself.
    stripped = strip_reasoning(crafted)
    assert "<think>" not in stripped and "consider" not in stripped
    # And the cleaned output parses to exactly the intended object.
    data = _json_object(crafted)
    assert data["title"] == "محضر"
    assert "think" not in json.dumps(data, ensure_ascii=False).lower()


@pytest.mark.parametrize(
    "content",
    [
        ANALYSIS_JSON,
        f"```json\n{ANALYSIS_JSON}\n```",
        f"<think>أفكر بصوت عالٍ</think>\n{ANALYSIS_JSON}",
        f"<think>...</think>\n```\n{ANALYSIS_JSON}\n```",
        f"مقدمة يتجاهلها المنظف {ANALYSIS_JSON} وخاتمة",
    ],
)
def test_json_object_accepts_noisy_replies(content: str):
    data = _json_object(content)
    assert data["title"] == "متابعة خطة العمل"


@pytest.mark.parametrize("content", ["لا يوجد كائن هنا", "", "<think>فقط</think>"])
def test_json_object_rejects_garbage(content: str):
    with pytest.raises(ValidationError):
        _json_object(content)


# ---------- the model preflight ----------


@respx.mock
def test_preflight_blocks_a_retired_model():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    retired = _settings(model="llama-3.3-70b-versatile")
    with pytest.raises(AnalysisError) as exc:
        GroqMinutesExtractor(retired).extract(META, SENTENCES, SPEAKERS)
    assert exc.value.message_key == "analysis.model_deprecated"
    assert constants.DEFAULT_LLM_MODEL in exc.value.available


@respx.mock
def test_preflight_passes_for_a_present_model():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    _ready_posts(httpx.Response(200, json=_envelope(ANALYSIS_JSON)))
    result = GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert result.title == "متابعة خطة العمل"


@respx.mock
def test_preflight_is_cached_for_the_process():
    models_route = respx.get(constants.GROQ_API_BASE + constants.MODELS_API_PATH).mock(
        return_value=httpx.Response(200, json=_models_payload(constants.DEFAULT_LLM_MODEL))
    )
    _ready_posts(httpx.Response(200, json=_envelope(ANALYSIS_JSON)))
    extractor = GroqMinutesExtractor(_settings())
    extractor.extract(META, SENTENCES, SPEAKERS)
    extractor.extract(META, SENTENCES, SPEAKERS)
    assert len(models_route.calls) == 1


# ---------- GroqMinutesExtractor ----------


@respx.mock
def test_extract_happy_path():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    route = _ready_posts(httpx.Response(200, json=_envelope(ANALYSIS_JSON)))
    result = GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert route.calls.called
    request = route.calls[0].request
    body = json.loads(request.content)
    assert body["model"] == constants.DEFAULT_LLM_MODEL
    assert body["temperature"] == 0.2
    assert body["max_completion_tokens"] == 4000
    assert body["include_reasoning"] is False
    assert body["messages"][0]["role"] == "system"
    assert request.headers["authorization"] == "Bearer test-key"
    assert result.title == "متابعة خطة العمل"
    assert result.tasks[0].segment_ids == ["s2"]


@respx.mock
def test_extract_uses_configured_model_not_default():
    custom = "qwen/qwen3.6-27b"
    _ready_models(custom)
    route = _ready_posts(httpx.Response(200, json=_envelope(ANALYSIS_JSON)))
    GroqMinutesExtractor(_settings(model=custom)).extract(META, SENTENCES, SPEAKERS)
    assert json.loads(route.calls[0].request.content)["model"] == custom


@respx.mock
def test_include_reasoning_is_dropped_and_retried_on_rejection():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    route = _ready_posts(
        httpx.Response(400, text='{"error":"unknown field include_reasoning"}'),
        httpx.Response(200, json=_envelope(ANALYSIS_JSON)),
    )
    result = GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert result.title == "متابعة خطة العمل"
    assert len(route.calls) == 2
    assert "include_reasoning" not in json.loads(route.calls[1].request.content)


@respx.mock
def test_extract_corrects_invalid_schema_once():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    bad = _envelope('{"title": 42, "topics": "ليس قائمة"}')
    route = _ready_posts(
        httpx.Response(200, json=bad),
        httpx.Response(200, json=_envelope(ANALYSIS_JSON)),
    )
    result = GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert result.title == "متابعة خطة العمل"
    assert len(route.calls) == 2
    second = json.loads(route.calls[1].request.content)
    assert second["messages"][-2]["role"] == "assistant"
    assert "الأخطاء المرصودة" in second["messages"][-1]["content"]


@respx.mock
def test_extract_raises_after_two_invalid_replies():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    bad = _envelope('{"title": 42}')
    _ready_posts(httpx.Response(200, json=bad))
    with pytest.raises(AnalysisError) as exc:
        GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert exc.value.message_key == "analysis.failed"


@respx.mock
def test_extract_retries_on_429_then_succeeds(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    _ready_models(constants.DEFAULT_LLM_MODEL)
    route = _ready_posts(
        httpx.Response(429, text="rate limited", headers={"Retry-After": "120"}),
        httpx.Response(200, json=_envelope(ANALYSIS_JSON)),
    )
    result = GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert result.title == "متابعة خطة العمل"
    assert len(route.calls) == 2
    # The hinted 120s waits out the tokens-per-minute window but is capped.
    assert slept == [constants.RETRY_AFTER_MAX_S]


@respx.mock
def test_extract_429_without_retry_after_uses_backoff(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    _ready_models(constants.DEFAULT_LLM_MODEL)
    _ready_posts(
        httpx.Response(429, text="rate limited"),
        httpx.Response(200, json=_envelope(ANALYSIS_JSON)),
    )
    GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert slept == [constants.RETRY_BACKOFF_BASE_S**1]


@respx.mock
def test_extract_exhausts_retries_on_5xx(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    _ready_models(constants.DEFAULT_LLM_MODEL)
    _ready_posts(httpx.Response(503, text="down"))
    with pytest.raises(AnalysisError) as exc:
        GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert exc.value.message_key == "groq.unavailable"


@respx.mock
def test_extract_auth_error_is_not_retried():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    route = _ready_posts(httpx.Response(401, text="unauthorized"))
    with pytest.raises(AnalysisError) as exc:
        GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert exc.value.message_key == "groq.key_missing"
    assert len(route.calls) == 1


def test_extract_missing_key_fails_before_network():
    with pytest.raises(AnalysisError) as exc:
        GroqMinutesExtractor(_settings(key="")).extract(META, SENTENCES, SPEAKERS)
    assert exc.value.message_key == "groq.key_missing"


@respx.mock
def test_extract_overlong_prompt_enters_map_reduce(monkeypatch):
    """An over-budget prompt no longer fails: it dispatches to map-reduce.

    The dispatch itself is asserted in tests/test_map_reduce.py; here we only
    pin that the single fast path is bypassed and a window call is attempted.
    """
    _ready_models(constants.DEFAULT_LLM_MODEL)
    calls: list[str] = []
    monkeypatch.setattr(
        GroqMinutesExtractor,
        "_extract_in_windows",
        lambda self, m, s, sp, job_id=None: calls.append("map") or Analysis(title="via windows"),
    )
    sentence = Sentence(id="s1", start=0.0, end=1.0, text="نص طويل جدًا " * 500)
    result = GroqMinutesExtractor(_settings()).extract(META, [sentence] * 20, SPEAKERS)
    assert calls == ["map"]
    assert result.title == "via windows"


def test_correction_message_trims_whitespace():
    msg = prompts.build_correction_message("  أخطاء   كثيرة\n\nومتفرقة  ")
    assert re.search(r"\s{2,}", msg) is None  # consecutive spaces are removed


# ---------- the Arabic-output guard ----------

# An English-only reply: schema-valid, but no Arabic in title or topic summaries.
ENGLISH_ONLY_JSON = json.dumps(
    {
        "title": "Work plan review",
        "attendees": ["The Manager", "Sara"],
        "topics": [{"title": "Plan", "summary": "Review of the work plan", "segment_ids": ["s1"]}],
        "decisions": [],
        "directives": [],
        "tasks": [
            {
                "description": "Raise the report",
                "owner": "Sara",
                "due": {"raw": "tomorrow", "gregorian": "2026-08-19"},
                "priority": None,
                "segment_ids": ["s2"],
            }
        ],
    },
    ensure_ascii=False,
)


@respx.mock
def test_english_only_reply_retries_once_then_succeeds_when_arabic():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    route = _ready_posts(
        httpx.Response(200, json=_envelope(ENGLISH_ONLY_JSON)),
        httpx.Response(200, json=_envelope(ANALYSIS_JSON)),
    )
    result = GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert result.title == "متابعة خطة العمل"
    assert len(route.calls) == 2  # exactly one retry, then success
    # The retry carried the English corrective line, not the schema correction.
    second = json.loads(route.calls[1].request.content)
    assert second["messages"][-2]["role"] == "assistant"
    assert "Arabic" in second["messages"][-1]["content"]
    assert "الأخطاء المرصودة" not in second["messages"][-1]["content"]


@respx.mock
def test_english_only_again_after_retry_raises():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    route = _ready_posts(
        httpx.Response(200, json=_envelope(ENGLISH_ONLY_JSON)),
        httpx.Response(200, json=_envelope(ENGLISH_ONLY_JSON)),
    )
    with pytest.raises(AnalysisError) as exc:
        GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert exc.value.message_key == "analysis.failed"
    assert len(route.calls) == 2  # one retry, then the second failure raises


@respx.mock
def test_english_only_retry_that_returns_schema_invalid_raises():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    route = _ready_posts(
        httpx.Response(200, json=_envelope(ENGLISH_ONLY_JSON)),
        httpx.Response(200, json=_envelope('{"title": 42}')),
    )
    with pytest.raises(AnalysisError) as exc:
        GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert exc.value.message_key == "analysis.failed"
    assert len(route.calls) == 2


@respx.mock
def test_arabic_reply_does_not_trigger_a_second_post():
    _ready_models(constants.DEFAULT_LLM_MODEL)
    route = _ready_posts(httpx.Response(200, json=_envelope(ANALYSIS_JSON)))
    GroqMinutesExtractor(_settings()).extract(META, SENTENCES, SPEAKERS)
    assert len(route.calls) == 1  # a grounded Arabic reply needs no retry


def test_has_arabic_output_detects_language():
    arabic = Analysis(title="متابعة خطة العمل", topics=[Topic(title="خطة", summary="مراجعة")])
    english = Analysis(title="Work plan review", topics=[Topic(title="Plan", summary="Review")])
    assert _has_arabic_output(arabic) is True
    assert _has_arabic_output(english) is False
    # A title alone in Arabic is enough; topics may be empty.
    assert _has_arabic_output(Analysis(title="اجتماع", topics=[])) is True
