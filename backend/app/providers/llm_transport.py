"""Shared OpenAI-compatible chat transport for minutes extraction: Groq and local Ollama."""

import logging

import httpx

from backend.app import constants
from backend.app.core.errors import AnalysisError
from backend.app.providers.llm_parse import content_from
from backend.app.providers.retry import RetryableError, retry_after_seconds, run_with_retries

log = logging.getLogger(__name__)

_GROQ_LABEL = "Groq LLM"
_LOCAL_LABEL = "Local LLM"


class ChatConfig:
    """One chat endpoint's knobs; include_reasoning_support is a shared mutable [bool] cell."""

    def __init__(
        self,
        *,
        label: str,
        failure_error_cls: type,
        error_key: str,
        include_reasoning_support: list[bool] | None,
    ) -> None:
        self.label = label
        self.failure_error_cls = failure_error_cls
        self.error_key = error_key
        self.include_reasoning_support = include_reasoning_support

    def key_or_none(self) -> str | None:  # pragma: no cover - overridden
        raise NotImplementedError

    def url(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def model(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError


class GroqChatConfig(ChatConfig):
    """The cloud default: Groq's chat endpoint under Bearer auth."""

    def __init__(self, settings, include_reasoning_support: list[bool] | None = None) -> None:
        super().__init__(
            label=_GROQ_LABEL,
            failure_error_cls=AnalysisError,
            error_key="groq",
            include_reasoning_support=include_reasoning_support,
        )
        self._settings = settings

    def key_or_none(self) -> str | None:
        return self._settings.groq_api_key

    def url(self) -> str:
        return constants.GROQ_API_BASE + constants.LLM_API_PATH

    def model(self) -> str:
        return self._settings.groq_llm_model


class LocalChatConfig(ChatConfig):
    """The offline fallback: a local Ollama server, reachable with no key."""

    def __init__(self, settings, include_reasoning_support: list[bool] | None = None) -> None:
        super().__init__(
            label=_LOCAL_LABEL,
            failure_error_cls=AnalysisError,  # routed to local copy by the key prefix
            error_key="local_llm",
            include_reasoning_support=include_reasoning_support,
        )
        self._settings = settings

    def key_or_none(self) -> None:
        return None  # Ollama serves with no auth

    def url(self) -> str:
        return self._settings.ollama_url.rstrip("/") + constants.LLM_API_PATH

    def model(self) -> str:
        return self._settings.local_llm_model


class ChatProviderTransport:
    """One OpenAI-compatible chat client; the request the cloud and local share."""

    def __init__(self, config: ChatConfig) -> None:
        self._c = config

    def send(self, messages: list[dict]) -> str:
        return run_with_retries(lambda: self._post(messages), self._c.label)

    def _post(self, messages: list[dict]) -> str:
        body = {
            "model": self._c.model(),
            "temperature": constants.LLM_TEMPERATURE,
            "max_completion_tokens": constants.MAX_COMPLETION_TOKENS,
            "messages": messages,
        }
        flag_cell = self._c.include_reasoning_support
        if flag_cell is not None and flag_cell[0]:
            body["include_reasoning"] = False
        key = self._c.key_or_none()
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        try:
            with httpx.Client(timeout=constants.LLM_TIMEOUT_S) as client:
                resp = client.post(self._c.url(), json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise RetryableError(self._fail("unavailable", f"timeout {exc}")) from exc
        except httpx.TransportError as exc:
            raise RetryableError(self._fail("unavailable", str(exc))) from exc
        if flag_cell is not None and _is_param_rejection(resp, "include_reasoning"):
            self._drop_reasoning_flag()
            return self._post(messages)
        if resp.status_code >= 400:
            raise self._http_error(resp)
        _log_usage(resp, self._c.label)
        return content_from(resp)

    def _drop_reasoning_flag(self) -> None:
        cell = self._c.include_reasoning_support
        if cell is None:
            return
        if cell[0]:
            log.info("include_reasoning rejected by the API; dropping it for this process")
            cell[0] = False

    def _fail(self, suffix: str, technical: str):
        return self._c.failure_error_cls(self._c.error_key + "." + suffix, technical)

    def _http_error(self, resp: httpx.Response):
        snippet = resp.text[: constants.ERROR_SNIPPET_CHARS]
        code = resp.status_code
        if code == 429:
            return RetryableError(
                self._fail("rate_limit", "429 rate limited"),
                retry_after=retry_after_seconds(resp),
            )
        if code >= 500:
            return RetryableError(self._fail("unavailable", f"{code} {snippet}"))
        if code in (401, 403):
            return self._fail("key_missing", f"auth {code}")
        return self._fail("failed", f"{code} {snippet}")


def _is_param_rejection(resp: httpx.Response, param: str) -> bool:
    if resp.status_code != 400:
        return False
    return param in resp.text.lower()


def _log_usage(resp: httpx.Response, label: str) -> None:
    """Log the API's measured token usage: ground truth for the prompt-size estimates."""
    try:
        usage = resp.json().get("usage") or {}
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        total = usage.get("total_tokens")
        if prompt is not None:
            log.info(
                "%s used tokens prompt=%s completion=%s total=%s",
                label,
                prompt,
                completion,
                total,
            )
    except (ValueError, AttributeError):
        pass
