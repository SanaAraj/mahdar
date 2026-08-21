"""The ordered pipeline stages, their labels, and how each one fails.

STAGE_ORDER is the single source of truth for both the registry and the
runner; STAGE_DEFS holds the per-stage wire status, Arabic label key, the
message key used when a stage raises an unexpected exception, and whether a
DIARIZE-stage failure degrades to SKIPPED instead of failing the job.
"""

import logging
from dataclasses import dataclass

from app.core.models import JobStatus


class JobLogger(logging.LoggerAdapter):
    """Log lines prefixed with the job id, at the caller's severity.

    Non-job lines (provider retries, startup reload) stay on the plain module
    logger; anything about one job goes through this adapter so the pipeline
    log is traceable per job with no message-format drift.
    """

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

# Stages that run as a parallel pair after conversion.
PARALLEL_STAGES: tuple[str, ...] = ("transcribe", "diarize")
