"""Tests for the shared retry helper: Retry-After handling and exhaustion."""

import httpx
import pytest

from app import constants
from app.shared.errors import TranscriptionError
from app.shared.retry import RetryableError, retry_after_seconds, run_with_retries


@pytest.fixture(autouse=True)
def _no_jitter(monkeypatch):
    """Pin jitter to zero so each asserted sleep is deterministic."""
    monkeypatch.setattr(constants, "HTTP_JITTER_S", 0)
    yield


def _attempt(failures: list[Exception], result: str = "ok"):
    state = {"calls": 0}

    def operation() -> str:
        state["calls"] += 1
        if failures:
            raise failures.pop(0)
        return result

    return operation, state


def test_429_with_retry_after_sleeps_the_hint_once(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    public = TranscriptionError("groq.rate_limit", "429")
    resp = httpx.Response(429, headers={"Retry-After": "40"}, text="limited")
    operation, state = _attempt([RetryableError(public, retry_after=retry_after_seconds(resp))])
    assert run_with_retries(operation, "test") == "ok"
    assert slept == [40.0]
    assert state["calls"] == 2


def test_retry_after_is_capped_at_max(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    public = TranscriptionError("groq.rate_limit", "429")
    retryable = RetryableError(public, retry_after=3600.0)
    operation, _ = _attempt([retryable])
    run_with_retries(operation, "test")
    assert slept == [constants.RETRY_AFTER_MAX_S]


def test_no_retry_after_falls_back_to_backoff(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    public = TranscriptionError("groq.unavailable", "down")
    operation, _ = _attempt([RetryableError(public)])
    run_with_retries(operation, "test")
    assert slept == [constants.RETRY_BACKOFF_BASE_S**1]


def test_unreadable_retry_after_header_falls_back(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    public = TranscriptionError("groq.rate_limit", "429")
    resp = httpx.Response(429, headers={"Retry-After": "soon"}, text="limited")
    operation, _ = _attempt([RetryableError(public, retry_after=retry_after_seconds(resp))])
    run_with_retries(operation, "test")
    assert slept == [constants.RETRY_BACKOFF_BASE_S**1]


def test_backoff_carries_jitter(monkeypatch):
    """With jitter enabled an exponential wait grows by up to HTTP_JITTER_S."""
    monkeypatch.setattr(constants, "HTTP_JITTER_S", 0.5)
    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", sleeps.append)
    monkeypatch.setattr("random.uniform", lambda lo, hi: hi)  # max jitter, deterministic
    public = TranscriptionError("groq.unavailable", "down")
    operation, _ = _attempt([RetryableError(public)])
    run_with_retries(operation, "test")
    assert sleeps == [constants.RETRY_BACKOFF_BASE_S**1 + 0.5]


def test_exhaustion_raises_the_public_error(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    public = TranscriptionError("groq.rate_limit", "429")
    operation, state = _attempt([RetryableError(public) for _ in range(constants.HTTP_RETRIES + 1)])
    with pytest.raises(TranscriptionError) as exc:
        run_with_retries(operation, "test")
    assert exc.value.message_key == "groq.rate_limit"
    assert state["calls"] == constants.HTTP_RETRIES + 1


def test_non_retryable_error_propagates_immediately(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    operation, state = _attempt([TranscriptionError("groq.failed", "400")])
    with pytest.raises(TranscriptionError):
        run_with_retries(operation, "test")
    assert state["calls"] == 1
    assert slept == []
