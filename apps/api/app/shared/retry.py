import logging
import random
import time
from collections.abc import Callable

from app import constants
from app.shared.errors import MahdarError

log = logging.getLogger(__name__)


class RetryableError(Exception):
    def __init__(
        self, public: MahdarError, retry_after: float | None = None, technical: str = ""
    ) -> None:
        super().__init__(technical or public.message_key)
        self.public = public
        self.retry_after = retry_after


def run_with_retries[T](operation: Callable[[], T], label: str) -> T:
    attempts = constants.HTTP_RETRIES + 1
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except RetryableError as exc:
            if attempt > constants.HTTP_RETRIES:
                raise exc.public from exc
            wait = _wait_seconds(exc, attempt)
            log.warning("%s retry %d of %d in %.0fs: %s", label, attempt, attempts, wait, exc)
            time.sleep(wait)
    raise AssertionError("run_with_retries: exhausted without error")  # pragma: no cover


def _wait_seconds(exc: RetryableError, attempt: int) -> float:

    if exc.retry_after is not None:
        return min(exc.retry_after, constants.RETRY_AFTER_MAX_S) + _jitter()
    return constants.RETRY_BACKOFF_BASE_S**attempt + _jitter()


def _jitter() -> float:

    return random.uniform(0, constants.HTTP_JITTER_S)


def retry_after_seconds(response: object) -> float | None:

    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw = headers.get(constants.RETRY_AFTER_HEADER)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None
