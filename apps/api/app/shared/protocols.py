"""Provider protocols; the exception types they raise live in core/errors.py.

The concrete exceptions (TranscriptionError, DiarizationError, AnalysisError)
are imported from the single hierarchy in core/errors so providers, pipeline,
and the API boundary all speak one error language.
"""

from pathlib import Path
from typing import Protocol

from app.shared.errors import AnalysisError, DiarizationError, TranscriptionError
from app.shared.models import (
    Analysis,
    MeetingMeta,
    Sentence,
    Speaker,
    Turn,
    Word,
)

__all__ = [
    "AnalysisError",
    "DiarizationError",
    "Diarizer",
    "MinutesExtractor",
    "Transcriber",
    "TranscriptionError",
]


class Transcriber(Protocol):
    def transcribe(self, wav_path: Path, mp3_path: Path) -> list[Word]: ...


class Diarizer(Protocol):
    def diarize(self, wav_path: Path) -> list[Turn]: ...


class MinutesExtractor(Protocol):
    def extract(
        self,
        meta: MeetingMeta,
        sentences: list[Sentence],
        speakers: list[Speaker],
        job_id: str | None = None,
    ) -> Analysis: ...
