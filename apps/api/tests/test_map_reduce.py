import json
import re
from datetime import date

import httpx
import pytest
import respx

from app import constants
from app.config import Settings
from app.features.analysis import citations, mapreduce, prompts
from app.features.analysis import service as core_analysis
from app.features.analysis.llm_groq import GroqMinutesExtractor
from app.features.analysis.windows import sentence_estimated_tokens, split_into_windows
from app.shared.errors import AnalysisError
from app.shared.models import (
    Analysis,
    Decision,
    DueDate,
    MeetingMeta,
    Sentence,
    Speaker,
    TaskItem,
    Topic,
)

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
    monkeypatch.setattr("app.features.analysis.llm_preflight._models_cache", None)
    monkeypatch.setattr("app.features.analysis.llm_groq._reasoning_support.enabled", True)
    monkeypatch.setattr(constants, "HTTP_JITTER_S", 0)
    yield


def _ready_models(model):
    respx.get(constants.GROQ_API_BASE + constants.MODELS_API_PATH).mock(
        return_value=httpx.Response(200, json={"data": [{"id": model}]})
    )


def _post_route():
    return respx.post(constants.GROQ_API_BASE + constants.LLM_API_PATH)


def test_windows_split_on_sentence_boundaries_never_inside():

    sentences = [_sentence(f"s{i + 1}", 280, float(i) * 3.0) for i in range(10)]
    budget = 1200
    windows = split_into_windows(sentences, budget=budget)
    assert len(windows) == 10
    assert [s.id for w in windows for s in w] == [s.id for s in sentences]
    assert all(_tokens_of(w) <= budget for w in windows)


def test_windows_respect_exact_budget_boundary():

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

    sentences = [_sentence("s1", 6000, 0.0)]
    with pytest.raises(AnalysisError) as exc:
        split_into_windows(sentences)
    assert exc.value.message_key == "analysis.too_long"


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


def test_map_similar_does_not_merge_long_items_on_three_generic_tokens():
    a = Decision(
        text="اعتماد خطة العمل الجديدة لفريق التسويق في الرياض",
        segment_ids=["s1"],
    )
    b = Decision(
        text="اعتماد خطة العمل السنوية لفريق التقنية في جدة",
        segment_ids=["s2"],
    )
    assert citations.map_similar(a, b) is False


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

    window_a = [_sentence("s1", 3, 0.0), _sentence("s2", 3, 3.0)]
    window_b = [_sentence("s3", 3, 6.0), _sentence("s4", 3, 9.0)]
    part_a = Analysis.model_validate_json(_two_window_analysis("اعتماد الخطة", ["s1"], "اجتماع"))
    part_b = Analysis.model_validate_json(
        _two_window_analysis("اعتماد الخطة الجديدة", ["s3", "s1"], "اجتماع")
    )

    grounded_a = mapreduce._ground_window_ids(part_a, window_a)
    grounded_b = mapreduce._ground_window_ids(part_b, window_b)
    assert grounded_a.decisions[0].segment_ids == ["s1"]

    assert grounded_b.decisions[0].segment_ids == ["s3"]

    merged = mapreduce._merge_fallback(
        Analysis(
            title="اجتماع",
            attendees=["المدير"],
            decisions=[
                Decision(text="اعتماد الخطة", segment_ids=["s1"]),
                Decision(text="اعتماد الخطة الجديدة", segment_ids=["s3"]),
            ],
        ),
        [grounded_a, grounded_b],
    )
    assert len(merged.decisions) == 1
    assert merged.decisions[0].segment_ids == ["s1", "s3"]


@respx.mock
def test_single_window_stays_on_the_fast_path(monkeypatch):

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
    assert len(route.calls) == 1


@respx.mock
def test_over_budget_transcript_routes_through_windows_and_reduce(monkeypatch):

    _ready_models(constants.DEFAULT_LLM_MODEL)

    route = _post_route().mock(side_effect=_cite_shown_ids_reply)

    monkeypatch.setattr(constants, "WINDOW_TOKEN_BUDGET", 1200)
    sentences = [_sentence(f"s{i + 1}", 280, float(i) * 3.0) for i in range(6)]
    result = GroqMinutesExtractor(_settings()).extract(META, sentences, SPEAKERS)

    assert result.title == "اجتماع طويل"
    assert len(route.calls) == 7

    last = json.loads(route.calls[-1].request.content)
    user = last["messages"][1]["content"]
    assert "[w1]" in user and "[w6]" in user
    assert "DECISION" in user


def _cite_shown_ids_reply(request) -> httpx.Response:

    body = json.loads(request.content)
    system = body["messages"][0]["content"]
    user = body["messages"][1]["content"]
    if "reducer" in system:
        cited = [
            sid
            for block in re.findall(r"DECISION \[([^\]]*)\]", user)
            for sid in block.split(",")
            if sid
        ]
        decisions = [{"text": "اعتماد الخطة", "segment_ids": sorted(set(cited))}] if cited else []
    else:
        shown = re.findall(r"^\[(s\d+)\]", user, flags=re.MULTILINE)
        decisions = [{"text": "اعتماد الخطة", "segment_ids": [shown[-1]]}]
    payload = {
        "title": "اجتماع طويل",
        "attendees": ["المدير"],
        "topics": [],
        "decisions": decisions,
        "directives": [],
        "tasks": [],
    }
    return httpx.Response(200, json=_envelope(json.dumps(payload, ensure_ascii=False)))


@respx.mock
def test_later_window_citation_survives_into_the_merge(monkeypatch):

    _ready_models(constants.DEFAULT_LLM_MODEL)
    _post_route().mock(side_effect=_cite_shown_ids_reply)
    monkeypatch.setattr(constants, "WINDOW_TOKEN_BUDGET", 1200)
    sentences = [_sentence(f"s{i + 1}", 280, float(i) * 3.0) for i in range(6)]
    result = GroqMinutesExtractor(_settings()).extract(META, sentences, SPEAKERS)
    cited = {sid for decision in result.decisions for sid in decision.segment_ids}
    assert "s6" in cited


def test_reduce_input_over_budget_fails_before_network():
    huge = ["TOPIC [s1]: " + "كلمة " * 9000]
    with pytest.raises(AnalysisError) as exc:
        prompts.build_reduce_message(huge)
    assert exc.value.message_key == "analysis.too_long"


def test_reduce_window_limit_fails_instead_of_dropping_later_windows():
    summaries = [f"TOPIC [s{index}]: بند" for index in range(61)]
    with pytest.raises(AnalysisError) as exc:
        mapreduce._cap_summaries(summaries)
    assert exc.value.message_key == "analysis.too_long"


def test_reduce_input_near_budget_passes_without_double_counting_the_prompt():

    word = "كلمة "
    count = (constants.REDUCE_TOKEN_BUDGET - 100) // prompts.estimate_tokens(word)
    message = prompts.build_reduce_message([word * count])
    tokens = prompts.estimate_tokens(message)
    assert tokens > constants.REDUCE_TOKEN_BUDGET - constants.REDUCE_PROMPT_OVERHEAD_EST_TOKENS
    assert tokens <= constants.REDUCE_TOKEN_BUDGET


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


def test_max_window_plus_overhead_stays_under_max_prompt_tokens():

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

    sentences = [_sentence(f"s{i + 1}", 800, float(i) * 3.0) for i in range(130)]
    windows = split_into_windows(sentences, budget=constants.WINDOW_TOKEN_BUDGET)

    assert len(windows) == 130
    assert sum(len(w) for w in windows) == 130
    for window in windows:
        assert _tokens_of(window) <= constants.WINDOW_TOKEN_BUDGET

    for window in windows:
        assert (
            _tokens_of(window) + constants.PROMPT_OVERHEAD_EST_TOKENS < constants.MAX_PROMPT_TOKENS
        )


def test_reduce_overhead_constant_covers_the_actual_prompt():

    actual = prompts.estimate_tokens(prompts.REDUCE_SYSTEM_PROMPT)
    assert actual <= constants.REDUCE_PROMPT_OVERHEAD_EST_TOKENS


def test_reduce_prompt_anchors_the_lowercase_schema():

    for token in ("segment_ids", '"title"', '"summary"', '"description"'):
        assert token in prompts.REDUCE_SYSTEM_PROMPT


def test_reduce_max_input_plus_overhead_stays_under_max_prompt_tokens():

    block = "TOPIC [s1]: " + " ".join(["كلمة"] * 120)
    n_ok = constants.REDUCE_TOKEN_BUDGET // prompts.estimate_tokens(block)
    summaries = [block] * n_ok
    estimate = prompts.estimate_tokens("\n\n".join(summaries))
    assert estimate <= constants.REDUCE_TOKEN_BUDGET
    assert estimate + constants.REDUCE_PROMPT_OVERHEAD_EST_TOKENS < constants.MAX_PROMPT_TOKENS
