"""Tests for the map-reduce analysis path: window budgeting, per-window mapping,
id remapping, the reduce merge, and the dispatch between the two paths (all
network access is mocked)."""

import json
from datetime import date

import httpx
import pytest
import respx

from backend.app import constants
from backend.app.config import Settings
from backend.app.core import analysis as core_analysis
from backend.app.core import mapreduce
from backend.app.core.errors import AnalysisError
from backend.app.core.models import (
    Analysis,
    Decision,
    DueDate,
    MeetingMeta,
    Sentence,
    Speaker,
    TaskItem,
    Topic,
)
from backend.app.processing import citations
from backend.app.processing.analysis_windows import sentence_estimated_tokens, split_into_windows
from backend.app.providers import prompts
from backend.app.providers.llm_groq import GroqMinutesExtractor

META = MeetingMeta(date_gregorian="2026-08-18", date_hijri="1448-03-05", duration_s=125.0)
SPEAKERS = [Speaker(id="SPEAKER_00", label="المدير", first_start=0.0)]


def _settings(key="test-key", model=constants.DEFAULT_LLM_MODEL) -> Settings:
    return Settings(groq_api_key=key, groq_llm_model=model)


def _envelope(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def _sentence(sid: str, tokens: int, start: float) -> Sentence:
    return Sentence(id=sid, start=start, end=start + 2.0, text=" ".join(["كلمة"] * tokens))


def _tokens_of(sentences: list[Sentence]) -> int:
    return sum(sentence_estimated_tokens(s) for s in sentences)


@pytest.fixture(autouse=True)
def _reset_llm_caches(monkeypatch):
    monkeypatch.setattr("backend.app.providers.llm_preflight._models_cache", None)
    monkeypatch.setattr("backend.app.providers.llm_groq._include_reasoning_supported", True)
    monkeypatch.setattr(constants, "HTTP_JITTER_S", 0)
    yield


def _ready_models(model):
    respx.get(constants.GROQ_API_BASE + constants.MODELS_API_PATH).mock(
        return_value=httpx.Response(200, json={"data": [{"id": model}]})
    )


def _post_route():
    return respx.post(constants.GROQ_API_BASE + constants.LLM_API_PATH)


# ---------- the pure window builder ----------


def test_windows_split_on_sentence_boundaries_never_inside():
    # Each sentence estimates over the per-window budget used here, so a budget
    # of 1200 can hold only one 280-word sentence per window and must yield ten
    # ordered windows, each a whole sentence.
    sentences = [_sentence(f"s{i + 1}", 280, float(i) * 3.0) for i in range(10)]
    budget = 1200
    windows = split_into_windows(sentences, budget=budget)
    assert len(windows) == 10
    assert [s.id for w in windows for s in w] == [s.id for s in sentences]
    assert all(_tokens_of(w) <= budget for w in windows)


def test_windows_respect_exact_budget_boundary():
    # Each sentence estimates exactly 100 tokens by padding; a budget of 200
    # packs exactly two per window with no overlap onto a third.
    sentences = []
    cursor = 0.0
    for i in range(5):
        base = sentence_estimated_tokens(_sentence("s", 0, cursor))
        word_count = max(0, int((100 - base) * constants.CHARS_PER_TOKEN / len("كلمة ")))
        sentences.append(_sentence(f"s{i + 1}", word_count, cursor))
        cursor += 3.0
    windows = split_into_windows(sentences, budget=200)
    assert [len(w) for w in windows] == [2, 2, 1]


def test_windows_single_sentence_under_budget_stays_one_call():
    sentences = [_sentence("s1", 10, 0.0)]
    assert len(split_into_windows(sentences)) == 1


def test_windows_oversize_single_sentence_raises_budget_error():
    # A sentence longer than the whole window budget cannot be split further.
    sentences = [_sentence("s1", 6000, 0.0)]
    with pytest.raises(AnalysisError) as exc:
        split_into_windows(sentences)
    assert exc.value.message_key == "analysis.too_long"


# ---------- the fused-pair similarity helper ----------


def test_map_similar_fuses_near_identical_wording():
    a = Decision(text="رفع التقرير الأسبوعي غدًا", segment_ids=["s1"])
    b = Decision(text="رفع التقرير الأسبوعي يوم غد", segment_ids=["s2"])
    assert citations.map_similar(a, b) is True


def test_map_similar_fuses_heading_in_body_containment():
    a = Topic(title="الخطة", summary="", segment_ids=["s1"])
    b = Decision(text="اعتماد الخطة السنوية للمشروع", segment_ids=["s2"])
    assert citations.map_similar(a, b) is True


def test_map_similar_keeps_distinct_items_separate():
    a = Decision(text="اعتماد ميزانية التسويق", segment_ids=["s1"])
    b = Decision(text="تعيين مدير جديد للفرع", segment_ids=["s2"])
    assert citations.map_similar(a, b) is False


# ---------- the two-window mocked end-to-end merge ----------


def _two_window_analysis(decision_text: str, sids: list[str], title: str) -> str:
    return json.dumps(
        {
            "title": title,
            "attendees": ["المدير"],
            "topics": [],
            "decisions": [{"text": decision_text, "segment_ids": sids}],
            "directives": [],
            "tasks": [],
        },
        ensure_ascii=False,
    )


def test_two_window_merge_deduplicates_and_unions_ids():
    # Two windows that each cite their own first line as s1; the remap unifies
    # the real ids before the reduce collects them, and the near-identical
    # ruling fuses into one decision.
    window_a = [_sentence("s1", 3, 0.0), _sentence("s2", 3, 3.0)]
    window_b = [_sentence("s3", 3, 6.0), _sentence("s4", 3, 9.0)]
    part_a = Analysis.model_validate_json(_two_window_analysis("اعتماد الخطة", ["s1"], "اجتماع"))
    part_b = Analysis.model_validate_json(
        _two_window_analysis("اعتماد الخطة الجديدة", ["s1"], "اجتماع")
    )

    remapped_a = mapreduce._remap_window_ids(part_a, window_a)
    remapped_b = mapreduce._remap_window_ids(part_b, window_b)
    assert remapped_a.decisions[0].segment_ids == ["s1"]
    # The second window's local s1 becomes the real s3, not a duplicate of s1.
    assert remapped_b.decisions[0].segment_ids == ["s3"]

    merged = mapreduce._merge_fallback(
        Analysis(
            title="اجتماع",
            attendees=["المدير"],
            decisions=[
                Decision(text="اعتماد الخطة", segment_ids=["s1"]),
                Decision(text="اعتماد الخطة الجديدة", segment_ids=["s3"]),
            ],
        ),
        [remapped_a, remapped_b],
    )
    assert len(merged.decisions) == 1
    assert merged.decisions[0].segment_ids == ["s1", "s3"]


# ---------- the single-window bypass proof ----------


@respx.mock
def test_single_window_stays_on_the_fast_path(monkeypatch):
    """A transcript under budget never touches the window or reduce prompts."""
    _ready_models(constants.DEFAULT_LLM_MODEL)
    route = _post_route().mock(
        return_value=httpx.Response(
            200,
            json=_envelope(
                json.dumps(
                    {
                        "title": "متابعة قصيرة",
                        "attendees": ["المدير"],
                        "topics": [],
                        "decisions": [],
                        "directives": [],
                        "tasks": [],
                    },
                    ensure_ascii=False,
                )
            ),
        )
    )
    sentences = [_sentence("s1", 3, 0.0)]
    result = GroqMinutesExtractor(_settings()).extract(META, sentences, SPEAKERS)
    assert result.title == "متابعة قصيرة"
    assert len(route.calls) == 1  # exactly one POST: no windows, no reduce


# ---------- the mocked two-window HTTP flow ----------


@respx.mock
def test_over_budget_transcript_routes_through_windows_and_reduce(monkeypatch):
    """Two over-budget sentences run as two map calls, then one reduce call."""
    _ready_models(constants.DEFAULT_LLM_MODEL)
    # Route to a lambda that always answers the merged reduce payload; the
    # number of map calls equals the window count, asserted below.
    route = _post_route().mock(
        return_value=httpx.Response(
            200, json=_envelope(_two_window_analysis("اعتماد الخطة", ["s1"], "ا"))
        )
    )
    # A tiny patched window budget holds one 280-word sentence per window. A
    # 280-word sentence estimates ~1152 tokens, so six of them (~6912 plus the
    # header) clear MAX_PROMPT_TOKENS and become six single-sentence windows.
    monkeypatch.setattr(constants, "WINDOW_TOKEN_BUDGET", 1200)
    sentences = [_sentence(f"s{i + 1}", 280, float(i) * 3.0) for i in range(6)]
    result = GroqMinutesExtractor(_settings()).extract(META, sentences, SPEAKERS)
    # The merged reply came back; six map calls plus one reduce call.
    assert result.title == "ا"
    assert len(route.calls) == 7
    # The reduce message carries the window summaries, never the transcript.
    last = json.loads(route.calls[-1].request.content)
    user = last["messages"][1]["content"]
    assert "[w1]" in user and "[w6]" in user
    assert "DECISION" in user


# ---------- the reduce-overflow guard ----------


def test_reduce_input_over_budget_fails_before_network():
    huge = ["TOPIC [s1]: " + "كلمة " * 9000]
    with pytest.raises(AnalysisError) as exc:
        prompts.build_reduce_message(huge)
    assert exc.value.message_key == "analysis.too_long"


# ---------- the deterministic date layer runs on the merged result ----------


def test_reduce_result_still_passes_the_date_and_citation_layer():
    analysis = Analysis(
        title="محضر",
        attendees=["المدير"],
        tasks=[
            TaskItem(
                description="رفع تقرير",
                owner=None,
                due=DueDate(raw="غدًا", gregorian=None, hijri=None),
                priority=None,
                segment_ids=["s7"],
            )
        ],
    )
    core_analysis.apply_meeting_task_dates(analysis, date(2026, 8, 18))
    assert analysis.tasks[0].due.gregorian == "2026-08-19"
    assert analysis.tasks[0].due.hijri is not None


# ---------- regression: budget splits stay under the real API bound ----------


def test_max_window_plus_overhead_stays_under_max_prompt_tokens():
    """A maximally packed window plus measured prompt overhead must clear MAX.

    Regression for the A8 failure where window transcripts were sized against an
    un-adorned MAX while each map call also paid for the shared system prompt,
    header, and scope line. Deduct them here so the budgets can never diverge.
    """
    sentences = [_sentence(f"s{i + 1}", 24, float(i) * 3.0) for i in range(500)]
    for window in split_into_windows(sentences, budget=constants.WINDOW_TOKEN_BUDGET):
        packed = _tokens_of(window)
        with_overhead = (
            packed
            + constants.PROMPT_OVERHEAD_EST_TOKENS
            + prompts.estimate_tokens(prompts.WINDOW_SCOPE_LINE)
        )
        assert with_overhead < constants.MAX_PROMPT_TOKENS


def test_realistic_long_meeting_packs_into_windows_that_pass():
    """A 37-minute A8-style transcript splits into over-budget-sized windows."""
    sentences = [_sentence(f"s{i + 1}", 800, float(i) * 3.0) for i in range(130)]
    windows = split_into_windows(sentences, budget=constants.WINDOW_TOKEN_BUDGET)
    # Each 800-word sentence estimates 3224 tokens on its own, so one lands per
    # 5000-token window and every sentence keeps its own window.
    assert len(windows) == 130
    assert sum(len(w) for w in windows) == 130
    for window in windows:
        assert _tokens_of(window) <= constants.WINDOW_TOKEN_BUDGET
    # each map call (window + system prompt + scope line) clears the real bound
    for window in windows:
        assert (
            _tokens_of(window) + constants.PROMPT_OVERHEAD_EST_TOKENS < constants.MAX_PROMPT_TOKENS
        )


def test_reduce_max_input_plus_overhead_stays_under_max_prompt_tokens():
    """The largest allowed reduce input still fits beside its system prompt."""
    block = "TOPIC [s1]: " + " ".join(["كلمة"] * 120)
    n_ok = constants.REDUCE_TOKEN_BUDGET // prompts.estimate_tokens(block)
    summaries = [block] * n_ok
    estimate = prompts.estimate_tokens("\n\n".join(summaries))
    assert estimate <= constants.REDUCE_TOKEN_BUDGET
    assert estimate + constants.REDUCE_PROMPT_OVERHEAD_EST_TOKENS < constants.MAX_PROMPT_TOKENS
