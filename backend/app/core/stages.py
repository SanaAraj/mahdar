"""Per-stage state transitions on the persisted MeetingJob.

Small, single-responsibility helpers that the Pipeline composes. Keeping them
here keeps pipeline.py focused on orchestration order rather than bookkeeping.
"""

import logging
import time

from backend.app import strings
from backend.app.core.jobs import JobRegistry
from backend.app.core.models import JobStatus, Stage, StageState
from backend.app.core.stagekit import STAGE_DEFS, STAGE_INDEX, STAGE_ORDER

log = logging.getLogger(__name__)


def init_stages(registry: JobRegistry, job_id: str) -> None:
    with registry.locked(job_id) as current:
        if current is not None and not current.stages:
            current.stages = [
                Stage(key=key, label_ar=strings.resolve(STAGE_DEFS[key].label_key))
                for key in STAGE_ORDER
            ]


def stage_state(registry: JobRegistry, job_id: str, key: str) -> StageState:
    job = registry.get(job_id)
    return job.stages[STAGE_INDEX[key]].state if job else StageState.PENDING


def begin(registry: JobRegistry, job_id: str, key: str) -> float:
    """Mark a stage RUNNING on the wire and return a monotonic start time."""
    with registry.locked(job_id) as current:
        if current is not None:
            current.status = STAGE_DEFS[key].wire_status
            current.stages[STAGE_INDEX[key]].state = StageState.RUNNING
    return time.monotonic()


def set_state(
    registry: JobRegistry,
    job_id: str,
    key: str,
    state: StageState,
    started: float,
    note_key: str | None = None,
    note_params: dict[str, str] | None = None,
) -> None:
    """Set a stage's terminal state, log its duration, optionally leave a note."""
    with registry.locked(job_id) as current:
        if current is not None:
            stage = current.stages[STAGE_INDEX[key]]
            stage.state = state
            if note_key is not None:
                stage.note_ar = strings.resolve(note_key, params=note_params)
    log.info("job %s stage %s=%s in %.2fs", job_id, key, state, time.monotonic() - started)


def mark_done(registry: JobRegistry, job_id: str) -> None:
    """Return the job to DONE without disturbing a FAILED status."""
    with registry.locked(job_id) as current:
        if current is not None and current.status != JobStatus.FAILED:
            current.status = JobStatus.DONE


def mark_failed(registry: JobRegistry, job_id: str, message_key: str, technical: str) -> None:
    with registry.locked(job_id) as current:
        if current is not None:
            current.status = JobStatus.FAILED
            current.error_ar = strings.resolve(message_key)
    log.error("job %s failed: %s", job_id, technical)
