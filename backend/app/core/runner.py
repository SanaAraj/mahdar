"""Stage orchestration behind Pipeline: serial stages, the parallel pair, soft-fail analyze."""

import logging
import threading
import time
from collections.abc import Callable

from backend.app.core import stages
from backend.app.core.errors import MahdarError
from backend.app.core.jobs import JobRegistry
from backend.app.core.models import StageState
from backend.app.core.stagekit import PARALLEL_STAGES, STAGE_DEFS, job_log

log = logging.getLogger(__name__)


class StageRunner:
    """Drives one job through convert, the parallel pair, assemble, and analyze."""

    def __init__(self, registry: JobRegistry, job_id: str, stage_map: dict[str, Callable]) -> None:
        self._registry = registry
        self._job_id = job_id
        self._map = stage_map
        self._log = job_log(log, job_id)

    def run_full(self) -> None:
        started = time.monotonic()
        stages.init_stages(self._registry, self._job_id)
        if not self._run_serial("convert"):
            return
        if not self._run_parallel_pair():
            return
        if not self._run_serial("assemble"):
            return
        self.run_analysis()
        self._log.info("finished; total duration %.2fs", time.monotonic() - started)

    def run_analysis(self) -> bool:
        """Analysis is soft-fail: its failure never drops a good transcript."""
        started = stages.begin(self._registry, self._job_id, "analyze")
        try:
            self._map["analyze"]()
        except MahdarError as exc:
            self._soft_fail(exc.message_key, _details(exc), started, _params_for(exc))
            return False
        except Exception as exc:  # noqa: BLE001 - job stays done with a clean transcript
            self._log.exception("stage analyze crashed")
            self._soft_fail("analysis.unexpected", _details(exc), started)
            return False
        stages.set_state(self._registry, self._job_id, "analyze", StageState.DONE, started)
        stages.mark_done(self._registry, self._job_id)
        return True

    def _run_serial(self, key: str) -> bool:
        if stages.stage_state(self._registry, self._job_id, key) in (
            StageState.DONE,
            StageState.SKIPPED,
        ):
            return True
        started = stages.begin(self._registry, self._job_id, key)
        try:
            self._map[key]()
        except MahdarError as exc:
            self._fail_serial(key, exc.message_key, _details(exc), started)
            return False
        except Exception as exc:  # noqa: BLE001 - the UI sees an Arabic message, never a trace
            self._log.exception("stage %s crashed", key)
            self._fail_serial(key, STAGE_DEFS[key].unexpected_key, _details(exc), started)
            return False
        stages.set_state(self._registry, self._job_id, key, StageState.DONE, started)
        return True

    def _run_parallel_pair(self) -> bool:
        pending = [
            k
            for k in PARALLEL_STAGES
            if stages.stage_state(self._registry, self._job_id, k)
            not in (StageState.DONE, StageState.SKIPPED)
        ]
        if not pending:
            return stages.stage_state(self._registry, self._job_id, "transcribe") == StageState.DONE
        started = {k: stages.begin(self._registry, self._job_id, k) for k in pending}
        errors: dict[str, Exception] = {}
        threads = [
            threading.Thread(target=self._capture, args=(key, errors), daemon=True)
            for key in pending
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        for key in pending:
            self._settle_parallel(key, errors.get(key), started[key])
        return errors.get("transcribe") is None

    def _capture(self, key: str, errors: dict[str, Exception]) -> None:
        try:
            self._map[key]()
        except Exception as exc:  # noqa: BLE001 - converted to a stage state by the caller
            if STAGE_DEFS[key].skippable:
                self._log.info("stage %s skipped: %s", key, exc)
            else:
                self._log.warning("stage %s failed: %s", key, exc)
            errors[key] = exc

    def _settle_parallel(self, key: str, exc: Exception | None, started: float) -> None:
        if exc is None:
            stages.set_state(self._registry, self._job_id, key, StageState.DONE, started)
        elif STAGE_DEFS[key].skippable:
            stages.set_state(
                self._registry,
                self._job_id,
                key,
                StageState.SKIPPED,
                started,
                note_key=STAGE_DEFS[key].unexpected_key,
            )
        else:
            self._fail_serial(key, _key_for(exc), _details(exc), started)

    def _fail_serial(self, key: str, message_key: str, technical: str, started: float) -> None:
        stages.set_state(self._registry, self._job_id, key, StageState.ERROR, started)
        stages.mark_failed(self._registry, self._job_id, message_key, technical)

    def _soft_fail(
        self,
        message_key: str,
        technical: str,
        started: float,
        note_params: dict[str, str] | None = None,
    ) -> None:
        stages.set_state(
            self._registry,
            self._job_id,
            "analyze",
            StageState.ERROR,
            started,
            note_key=message_key,
            note_params=note_params,
        )
        self._log.error("stage analyze failed: %s", technical)
        stages.mark_done(self._registry, self._job_id)


def _key_for(exc: Exception) -> str:
    return exc.message_key if isinstance(exc, MahdarError) else "transcription.unexpected"


def _params_for(exc: Exception) -> dict[str, str] | None:
    available = getattr(exc, "available", None)
    return {"available": available} if available else None


def _details(exc: Exception) -> str:
    return getattr(exc, "technical", "") or str(exc)
