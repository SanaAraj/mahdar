"""Assemble the analysis stage: extraction, citation cleaning, and date fill.

Kept apart from pipeline.py so the orchestrator stays linear; these are the
helpers the analyze stage composes, all operating on plain models.
"""

import json
from datetime import date
from zoneinfo import ZoneInfo

from app.features.analysis import citations, dates
from app.shared.errors import AudioError
from app.shared.models import (
    RIYADH_TZ,
    Analysis,
    MeetingMeta,
    Sentence,
    Turn,
    Word,
    gregorian_hijri,
)


def build_meeting_meta(created_at, duration_s: float | None) -> MeetingMeta:
    anchor = anchor_date_of(created_at)
    return MeetingMeta(
        date_gregorian=anchor.isoformat(),
        date_hijri=gregorian_hijri(anchor.isoformat()) or "",
        duration_s=duration_s,
    )


def anchor_date_of(created_at) -> date:
    return created_at.astimezone(ZoneInfo(RIYADH_TZ)).date()


def clean_citations(analysis: Analysis, sentences: list[Sentence]) -> tuple[Analysis, int]:
    """Drop analysis items without a real sentence source or a wording overlap."""
    return citations.validate(analysis, sentences)


def write_models(path, models: list) -> None:
    path.write_text(
        json.dumps([m.model_dump() for m in models], ensure_ascii=False), encoding="utf-8"
    )


def read_words(job_dir) -> list[Word]:
    path = job_dir / "words.json"
    if not path.exists():
        raise AudioError("assembly.failed", "words.json missing")
    return [Word.model_validate(item) for item in json.loads(path.read_text("utf-8"))]


def read_turns(job_dir) -> list[Turn]:
    path = job_dir / "turns.json"
    if not path.exists():
        return []
    return [Turn.model_validate(item) for item in json.loads(path.read_text("utf-8"))]


def apply_meeting_task_dates(analysis: Analysis, anchor) -> None:
    """Resolve relative dates against the meeting date and fill Hijri from Gregorian.

    The deterministic normalization layer wins over the model's own date when
    it understands the phrase; whatever it cannot parse keeps the model's value
    if valid, otherwise stays null.
    """
    for task in analysis.tasks:
        due = task.due
        normalized = dates.normalize(due.raw, anchor)
        if normalized is not None:
            # The deterministic layer wins: the model's own date is ignored.
            due.gregorian = normalized.isoformat()
            due.hijri = gregorian_hijri(normalized.isoformat())
            continue
        if due.raw is None:
            # The no-invention rule: no date was said, so the UI shows none.
            due.gregorian = None
            due.hijri = None
            continue
        if due.gregorian:
            due.hijri = gregorian_hijri(due.gregorian)
        elif due.hijri:
            due.gregorian = dates.gregorian_from_hijri(due.hijri)
