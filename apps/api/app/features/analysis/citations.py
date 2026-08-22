"""Citation cleaning: no analysis item survives without a transcript source.

Two guards run per item. The id guard drops citations whose sentence ids do
not exist. The faithfulness guard then drops the item itself when its wording
shares not a single normalized content token with the sentences it claims to
rest on: a fabricated item always fails this test even when it invents ids
that happen to exist. Normalization (diacritics stripped, alef and hamza
forms unified, ta marbuta folded, punctuation removed) is for matching only
and never alters stored text.
"""

import logging
import re
from collections.abc import Iterable

from app import constants
from app.shared.models import Analysis, SegmentCited, Sentence

log = logging.getLogger(__name__)

# Diacritics and Quranic marks, tatweel, and every punctuation character. The
# Arabic character data lives in constants (chartered); this module builds the
# compiled matchers from it and never holds Arabic literals of its own.
_MARKS_RE = re.compile(constants.ARABIC_DIACRITICS_AND_PUNCT_PATTERN, re.UNICODE)
_ALEF_RE = re.compile(f"[{constants.ARABIC_ALEF_FORMS}]")
_HAMZA_FORMS_RE = re.compile(f"[{constants.ARABIC_HAMZA_FORMS}]")
_TA_MARBUTA_RE = re.compile(constants.ARABIC_TA_MARBUTA)
_WHITESPACE_RE = re.compile(r"\s+")


def content_overlap(text: str) -> frozenset[str]:
    """Normalized content tokens of a text, for faithfulness matching only."""
    text = _MARKS_RE.sub("", text)
    text = _ALEF_RE.sub(constants.ARABIC_ALEF_CANONICAL, text)
    text = _HAMZA_FORMS_RE.sub(constants.ARABIC_HAMZA_CANONICAL, text)
    text = _TA_MARBUTA_RE.sub(constants.ARABIC_TA_CANONICAL, text)
    tokens = _WHITESPACE_RE.split(text)
    return frozenset(t for t in tokens if len(t) >= constants.CITATION_MIN_TOKEN_CHARS)


def cited_text(item: SegmentCited, sentences_by_id: dict[str, str]) -> str:
    """Concatenated text of the item's cited sentences, in transcript order."""
    return " ".join(text for sid, text in sentences_by_id.items() if sid in set(item.segment_ids))


def has_overlap(item_text: str, cited: str) -> bool:
    """True when item and its sources share at least one content token."""
    return bool(content_overlap(item_text) & content_overlap(cited))


def validate(analysis: Analysis, sentences: list[Sentence]) -> tuple[Analysis, int]:
    """Trim segment_ids to existing ones and drop any item with no source left.

    Items whose remaining sources share no content token with the item's own
    wording are dropped as fabricated. Builds a fresh copy of each kept item
    and never touches the original.
    """
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
    """All wording the overlap guard checks: every content field the item has.

    A Topic splits its content across title and summary; a grounded title must
    count even when the summary paraphrases or is empty, so both fields are
    checked together rather than one being chosen over the other.
    """
    parts: list[str] = []
    for attr in ("title", "summary", "text", "description"):
        value = getattr(item, attr, None)
        if value:
            parts.append(value)
    return " ".join(parts)


def map_similar(a: SegmentCited, b: SegmentCited) -> bool:
    """True when two mapped items are near-identical and should fuse in reduce.

    Reuses the same normalized content tokens as the faithfulness guard. Two
    items fuse when they share at least MAP_OVERLAP_MIN_TOKENS tokens, or when
    one wording is a heading-length fragment (at most MAP_TITLE_OVERLAP_MAX_TOKENS
    tokens) fully contained in the other, matching how the same decision or task
    is phrased tersely in one window and fully in another.
    """
    ta = content_overlap(_item_text(a))
    tb = content_overlap(_item_text(b))
    if not ta or not tb:
        return False
    shared = len(ta & tb)
    if shared >= constants.MAP_OVERLAP_MIN_TOKENS:
        return True
    smaller = min(len(ta), len(tb))
    return smaller <= constants.MAP_TITLE_OVERLAP_MAX_TOKENS and shared == smaller
