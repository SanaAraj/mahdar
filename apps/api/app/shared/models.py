from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from hijridate import Gregorian
from pydantic import BaseModel, Field

RIYADH_TZ = "Asia/Riyadh"


class JobStatus(StrEnum):
    RECEIVED = "received"
    CONVERTING = "converting"
    TRANSCRIBING = "transcribing"
    DIARIZING = "diarizing"
    ASSEMBLING = "assembling"
    ANALYZING = "analyzing"
    DONE = "done"
    FAILED = "failed"


class StageState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"
    ERROR = "error"


class Stage(BaseModel):
    key: str
    label_ar: str
    state: StageState = StageState.PENDING
    note_ar: str | None = None


class Sentence(BaseModel):
    id: str
    start: float
    end: float
    text: str
    speaker: str | None = None


class Word(BaseModel):
    start: float
    end: float
    text: str
    no_speech_prob: float | None = None
    avg_logprob: float | None = None
    compression_ratio: float | None = None


class Turn(BaseModel):
    start: float
    end: float
    speaker: str


class Speaker(BaseModel):
    id: str
    label: str
    first_start: float


class SegmentCited(BaseModel):
    segment_ids: list[str] = Field(default_factory=list)

    def cited_ids(self) -> list[str]:
        return list(self.segment_ids)


class Topic(SegmentCited):
    title: str
    summary: str


class Decision(SegmentCited):
    text: str


class Directive(SegmentCited):
    text: str


class DueDate(BaseModel):
    raw: str | None = None
    gregorian: str | None = None
    hijri: str | None = None


class TaskItem(SegmentCited):
    description: str
    owner: str | None = None
    due: DueDate = Field(default_factory=DueDate)

    priority: Literal["عالية", "متوسطة", "منخفضة"] | None = None


class Analysis(BaseModel):
    title: str
    attendees: list[str] = Field(default_factory=list)
    topics: list[Topic] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    directives: list[Directive] = Field(default_factory=list)
    tasks: list[TaskItem] = Field(default_factory=list)


def gregorian_hijri(gregorian_iso: str) -> str | None:

    try:
        iso = gregorian_iso[:10]
        day = date(int(iso[0:4]), int(iso[5:7]), int(iso[8:10]))
        return Gregorian(day.year, day.month, day.day).to_hijri().isoformat()
    except (ValueError, IndexError, OverflowError):
        return None


class MeetingMeta(BaseModel):
    date_gregorian: str
    date_hijri: str
    duration_s: float | None = None


class MeetingJob(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.now)
    status: JobStatus = JobStatus.RECEIVED
    stages: list[Stage] = Field(default_factory=list)
    duration_s: float | None = None
    error_ar: str | None = None
    sentences: list[Sentence] = Field(default_factory=list)
    speakers: list[Speaker] = Field(default_factory=list)
    analysis: Analysis | None = None
    date_gregorian: str | None = None
    date_hijri: str | None = None


class ExportMeta(BaseModel):
    id: str
    created_at: datetime
    date_gregorian: str | None = None
    date_hijri: str | None = None
    duration_s: float | None = None


class ExportMeeting(BaseModel):
    meta: ExportMeta
    speakers: list[Speaker]
    sentences: list[Sentence]
    analysis: Analysis | None = None
