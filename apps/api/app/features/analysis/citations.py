import logging
import re
from collections.abc import Iterable

from app import constants
from app.shared.models import Analysis, SegmentCited, Sentence

log = logging.getLogger(__name__)


_MARKS_RE = re.compile(constants.ARABIC_DIACRITICS_AND_PUNCT_PATTERN, re.UNICODE)
_ALEF_RE = re.compile(f"[{constants.ARABIC_ALEF_FORMS}]")
_HAMZA_FORMS_RE = re.compile(f"[{constants.ARABIC_HAMZA_FORMS}]")
_TA_MARBUTA_RE = re.compile(constants.ARABIC_TA_MARBUTA)
_WHITESPACE_RE = re.compile(r"\s+")


def content_overlap(text: str) -> frozenset[str]:

    text = _MARKS_RE.sub("", text)
    text = _ALEF_RE.sub(constants.ARABIC_ALEF_CANONICAL, text)
    text = _HAMZA_FORMS_RE.sub(constants.ARABIC_HAMZA_CANONICAL, text)
    text = _TA_MARBUTA_RE.sub(constants.ARABIC_TA_CANONICAL, text)
    tokens = _WHITESPACE_RE.split(text)
    return frozenset(t for t in tokens if len(t) >= constants.CITATION_MIN_TOKEN_CHARS)


def cited_text(item: SegmentCited, sentences_by_id: dict[str, str]) -> str:

    return " ".join(text for sid, text in sentences_by_id.items() if sid in set(item.segment_ids))


def has_overlap(item_text: str, cited: str) -> bool:

    return bool(content_overlap(item_text) & content_overlap(cited))


def validate(analysis: Analysis, sentences: list[Sentence]) -> tuple[Analysis, int]:

    topics, d_topics = _clean(analysis.topics, sentences)
    decisions, d_decisions = _clean(analysis.decisions, sentences)
    directives, d_directives = _clean(analysis.directives, sentences)
    tasks, d_tasks = _clean(analysis.tasks, sentences)
    cleaned = Analysis(
        title=analysis.title,
        attendees=list(analysis.attendees),
        topics=topics,
        decisions=decisions,
        directives=directives,
        tasks=tasks,
    )
    return cleaned, d_topics + d_decisions + d_directives + d_tasks


def _clean(
    items: Iterable[SegmentCited], sentences: list[Sentence]
) -> tuple[list[SegmentCited], int]:
    existing = {s.id for s in sentences}
    by_id = {s.id: s.text for s in sentences}
    kept: list[SegmentCited] = []
    dropped = 0
    for item in items:
        remaining = [sid for sid in item.segment_ids if sid in existing]
        if not remaining:
            dropped += 1
            continue
        clone = item.model_copy(update={"segment_ids": remaining})
        if not has_overlap(_item_text(item), cited_text(item, by_id)):
            log.info("Dropped ungrounded item with valid ids: %.80s", _item_text(item))
            dropped += 1
            continue
        kept.append(clone)
    return kept, dropped


def _item_text(item: SegmentCited) -> str:

    parts: list[str] = []
    for attr in ("title", "summary", "text", "description"):
        value = getattr(item, attr, None)
        if value:
            parts.append(value)
    return " ".join(parts)


def map_similar(a: SegmentCited, b: SegmentCited) -> bool:

    ta = content_overlap(_item_text(a))
    tb = content_overlap(_item_text(b))
    if not ta or not tb:
        return False
    shared = len(ta & tb)
    if shared >= constants.MAP_OVERLAP_MIN_TOKENS:
        return True
    smaller = min(len(ta), len(tb))
    return smaller <= constants.MAP_TITLE_OVERLAP_MAX_TOKENS and shared == smaller
