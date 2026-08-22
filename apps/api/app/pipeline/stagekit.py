import logging
from dataclasses import dataclass

from app.shared.models import JobStatus


class JobLogger(logging.LoggerAdapter):
    def process(self, msg: str, kwargs) -> tuple[str, dict]:
        return f"job {self.extra['job_id']} {msg}", kwargs


def job_log(logger: logging.Logger, job_id: str) -> JobLogger:
    return JobLogger(logger, {"job_id": job_id})


@dataclass(frozen=True)
class StageDef:
    key: str
    wire_status: JobStatus
    label_key: str
    unexpected_key: str
    skippable: bool = False


_STAGE_DATA = (
    ("convert", JobStatus.CONVERTING, "stage.convert", "audio.corrupt", False),
    ("transcribe", JobStatus.TRANSCRIBING, "stage.transcribe", "transcription.unexpected", False),
    ("diarize", JobStatus.DIARIZING, "stage.diarize", "diarize.skipped", True),
    ("assemble", JobStatus.ASSEMBLING, "stage.assemble", "assembly.failed", False),
    ("analyze", JobStatus.ANALYZING, "stage.analyze", "analysis.unexpected", False),
)

STAGE_ORDER: tuple[str, ...] = tuple(d[0] for d in _STAGE_DATA)
STAGE_DEFS: dict[str, StageDef] = {
    key: StageDef(key, status, label, unexpected, skippable)
    for key, status, label, unexpected, skippable in _STAGE_DATA
}
STAGE_INDEX: dict[str, int] = {key: i for i, key in enumerate(STAGE_ORDER)}


PARALLEL_STAGES: tuple[str, ...] = ("transcribe", "diarize")
