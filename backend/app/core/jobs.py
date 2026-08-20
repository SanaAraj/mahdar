import json
import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from backend.app.core.models import MeetingJob

log = logging.getLogger(__name__)

_STATE_FILE = "state.json"


class JobRegistry:
    """Thread-safe job registry; persists each job to disk and reloads on boot."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._jobs: dict[str, MeetingJob] = {}
        self._lock = threading.Lock()
        self._load_all()

    def _load_all(self) -> None:
        if not self._data_dir.exists():
            return
        for child in sorted(self._data_dir.iterdir()):
            state_path = child / _STATE_FILE
            if child.is_dir() and state_path.exists():
                try:
                    job = MeetingJob.model_validate_json(state_path.read_text("utf-8"))
                except (ValueError, OSError):
                    log.warning("Skipping unreadable state file: %s", state_path)
                    continue
                self._jobs[job.id] = job
        if self._jobs:
            log.info("Reloaded %d job(s) from %s", len(self._jobs), self._data_dir)

    def create(self, job_id: str) -> MeetingJob:
        with self._lock:
            job = MeetingJob(id=job_id)
            self._jobs[job_id] = job
            self._persist_locked(job)
            return job

    def get(self, job_id: str) -> MeetingJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def job_dir(self, job_id: str) -> Path:
        return self._data_dir / job_id

    def rename_speakers(self, job_id: str, mapping: dict[str, str]) -> bool:
        """Update speaker labels and persist; True when the job exists."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            for speaker in job.speakers:
                if speaker.id in mapping:
                    speaker.label = mapping[speaker.id]
            self._persist_locked(job)
            return True

    @contextmanager
    def locked(self, job_id: str) -> Iterator[MeetingJob | None]:
        """Lock the registry and auto-persist the job on block exit."""
        with self._lock:
            job = self._jobs.get(job_id)
            try:
                yield job
            finally:
                if job is not None:
                    self._persist_locked(job)

    def _persist_locked(self, job: MeetingJob) -> None:
        job_dir = self._data_dir / job.id
        job_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = job_dir / (_STATE_FILE + ".tmp")
        tmp_path.write_text(
            json.dumps(job.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(job_dir / _STATE_FILE)
