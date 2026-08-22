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

    for task in analysis.tasks:
        due = task.due
        normalized = dates.normalize(due.raw, anchor)
        if normalized is not None:
            due.gregorian = normalized.isoformat()
            due.hijri = gregorian_hijri(normalized.isoformat())
            continue
        if due.raw is None:
            due.gregorian = None
            due.hijri = None
            continue
        due.gregorian = None
        due.hijri = None
