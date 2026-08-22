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
    item_tokens = content_overlap(item_text)
    required = min(2, max(1, (len(item_tokens) + 1) // 2))
    return bool(item_tokens) and len(_ground_tokens(item_text) & _ground_tokens(cited)) >= required


def _ground_tokens(text: str) -> frozenset[str]:
    tokens = content_overlap(text)
    return tokens | frozenset(_light_stem(token) for token in tokens)


def _light_stem(token: str) -> str:
    for prefix in ("وال", "بال", "كال", "فال", "لل", "ال"):
        if token.startswith(prefix) and len(token) - len(prefix) >= 3:
            token = token[len(prefix) :]
            break
    for prefix in ("و", "ف", "س", "ن", "ي", "ت", "ا", "م"):
        if token.startswith(prefix) and len(token) >= 5:
            token = token[1:]
            break
    for suffix in ("ات", "ون", "ين", "ان", "ها", "هم", "نا", "ه", "ي"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)]
            break
    return token


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


def _clean[T: SegmentCited](items: Iterable[T], sentences: list[Sentence]) -> tuple[list[T], int]:
    existing = {s.id for s in sentences}
    by_id = {s.id: s.text for s in sentences}
    kept: list[T] = []
    dropped = 0
    for item in items:
        remaining = [sid for sid in item.segment_ids if sid in existing]
        if not remaining:
            dropped += 1
            continue
        clone = item.model_copy(update={"segment_ids": remaining})
        cited = cited_text(item, by_id)
        if not any(has_overlap(surface, cited) for surface in _item_surfaces(item)):
            log.info("Dropped ungrounded item with valid ids: %.80s", _item_text(item))
            dropped += 1
            continue
        kept.append(clone)
    return kept, dropped


def _item_text(item: SegmentCited) -> str:
    return " ".join(_item_surfaces(item))


def _item_surfaces(item: SegmentCited) -> list[str]:
    parts: list[str] = []
    for attr in ("title", "summary", "text", "description"):
        value = getattr(item, attr, None)
        if value:
            parts.append(value)
    return parts


def map_similar(a: SegmentCited, b: SegmentCited) -> bool:

    ta = content_overlap(_item_text(a))
    tb = content_overlap(_item_text(b))
    if not ta or not tb:
        return False
    shared = len(ta & tb)
    smaller = min(len(ta), len(tb))
    if shared >= constants.MAP_OVERLAP_MIN_TOKENS and shared / smaller >= 0.6:
        return True
    return smaller <= constants.MAP_TITLE_OVERLAP_MAX_TOKENS and shared == smaller
