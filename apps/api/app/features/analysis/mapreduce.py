import logging
import time
from collections.abc import Callable

from app import constants
from app.features.analysis import citations, prompts
from app.features.analysis.windows import split_into_windows
from app.pipeline.stagekit import job_log
from app.shared.models import Analysis, MeetingMeta, SegmentCited, Sentence, Speaker

log = logging.getLogger(__name__)


def analyze_long(
    meta: MeetingMeta,
    sentences: list[Sentence],
    speakers: list[Speaker],
    extract_once: Callable[[MeetingMeta, list[Sentence], list[Speaker]], Analysis],
    reduce_once: Callable[[list[str]], Analysis],
    job_id: str | None = None,
) -> Analysis:

    jlog = job_log(log, job_id) if job_id else log
    windows = split_into_windows(sentences)
    jlog.info("map-reduce over %d window(s) of %d sentences", len(windows), len(sentences))
    partials: list[Analysis] = []
    for index, window in enumerate(windows, start=1):
        started = time.monotonic()
        part = extract_once(meta, window, speakers)
        jlog.info(
            "analysis window %d/%d: %d sentences in %.2fs",
            index,
            len(windows),
            len(window),
            time.monotonic() - started,
        )
        partials.append(_ground_window_ids(part, window))
    summaries = [_window_summary(part) for part in partials]
    merged = reduce_once(_cap_summaries(summaries, jlog))
    return _merge_fallback(merged, partials)


def _cap_summaries(summaries: list[str], jlog=None) -> list[str]:

    logger = jlog if jlog is not None else log
    if len(summaries) > constants.REDUCE_SUMMARY_MAX_ITEMS:
        logger.warning(
            "reduce input has %d window summaries, capping to %d",
            len(summaries),
            constants.REDUCE_SUMMARY_MAX_ITEMS,
        )
        summaries = summaries[: constants.REDUCE_SUMMARY_MAX_ITEMS]
    joined = "\n".join(summaries)
    if prompts.estimate_tokens(joined) > constants.REDUCE_TOKEN_BUDGET:
        logger.warning("reduce input preview: %.*s", constants.REDUCE_ITEM_PREVIEW_CHARS, joined)
    return summaries


def _ground_window_ids(part: Analysis, window: list[Sentence]) -> Analysis:

    valid = {sentence.id for sentence in window}

    def fix(ids: list[str]) -> list[str]:
        seen: list[str] = []
        for raw in ids:
            if raw in valid and raw not in seen:
                seen.append(raw)
        return seen

    def ground(items: list[SegmentCited]) -> list:
        return [item.model_copy(update={"segment_ids": fix(item.segment_ids)}) for item in items]

    return part.model_copy(
        update={
            "attendees": list(part.attendees),
            "topics": ground(part.topics),
            "decisions": ground(part.decisions),
            "directives": ground(part.directives),
            "tasks": ground(part.tasks),
        }
    )


def _window_summary(part: Analysis) -> str:

    lines: list[str] = [
        f"TITLE: {part.title}",
        "ATTENDEES: " + (constants.ARABIC_COMMA + " ").join(part.attendees),
    ]
    for topic in part.topics:
        lines.append(f"TOPIC [{_ids(topic)}]: {topic.title} | {topic.summary}")
    for item in part.decisions:
        lines.append(f"DECISION [{_ids(item)}]: {item.text}")
    for item in part.directives:
        lines.append(f"DIRECTIVE [{_ids(item)}]: {item.text}")
    for task in part.tasks:
        lines.append(f"TASK [{_ids(task)}]: {task.description}")
    return "\n".join(lines)


def _ids(item: SegmentCited) -> str:
    return ",".join(item.segment_ids)


_SEGMENT_IDS = "segment_ids"


def _merge_fallback(merged: Analysis, partials: list[Analysis]) -> Analysis:

    return Analysis(
        title=merged.title,
        attendees=_union_attendees(partials, merged.attendees),
        topics=_merge_items(merged.topics),
        decisions=_merge_items(merged.decisions),
        directives=_merge_items(merged.directives),
        tasks=_merge_items(merged.tasks),
    )


def _union_attendees(partials: list[Analysis], reduced: list[str]) -> list[str]:
    seen: list[str] = []
    for name in [*reduced, *(name for part in partials for name in part.attendees)]:
        if name and name not in seen:
            seen.append(name)
    return seen


def _merge_items(reduced_items: list) -> list:

    kept: list = []
    for item in reduced_items:
        match = next((k for k in kept if citations.map_similar(k, item)), None)
        if match is None:
            kept.append(item)
        else:
            union = _union_ids(match.segment_ids, item.segment_ids)
            kept[kept.index(match)] = match.model_copy(update={_SEGMENT_IDS: union})
    return kept


def _union_ids(a: list[str], b: list[str]) -> list[str]:
    seen: list[str] = []
    for raw in [*a, *b]:
        if raw not in seen:
            seen.append(raw)
    return sorted(seen, key=_id_sort_key)


def _id_sort_key(raw: str) -> tuple[int, int | str]:
    suffix = raw[1:] if raw[:1].isalpha() else raw
    return (0, int(suffix)) if suffix.isdigit() else (1, raw)
