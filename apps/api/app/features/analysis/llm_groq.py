import logging

from pydantic import ValidationError

from app import constants
from app.config import Settings
from app.features.analysis import mapreduce, prompts
from app.features.analysis.llm_parse import has_arabic_output as _has_arabic_output
from app.features.analysis.llm_parse import json_object as _json_object
from app.features.analysis.llm_parse import strip_reasoning as strip_reasoning
from app.features.analysis.llm_preflight import available_models, suggest_models
from app.features.analysis.llm_transport import ChatProviderTransport, GroqChatConfig
from app.pipeline.stagekit import job_log
from app.shared.errors import AnalysisError
from app.shared.models import Analysis, MeetingMeta, Sentence, Speaker

log = logging.getLogger(__name__)


_LABEL = "Groq LLM"


_include_reasoning_support: list[bool] = [True]


_include_reasoning_supported: bool = True


class GroqMinutesExtractor:
    def __init__(self, settings: Settings, transport: ChatProviderTransport | None = None) -> None:
        self._settings = settings

        _include_reasoning_support[0] = _include_reasoning_supported
        self._transport = transport or ChatProviderTransport(
            GroqChatConfig(settings, _include_reasoning_support)
        )

    def extract(
        self,
        meta: MeetingMeta,
        sentences: list[Sentence],
        speakers: list[Speaker],
        job_id: str | None = None,
    ) -> Analysis:
        self._require_key()
        self._assert_model_available()
        user_message = prompts.build_user_message(meta, sentences, speakers)
        if (
            prompts.estimate_tokens(prompts.SYSTEM_PROMPT) + prompts.estimate_tokens(user_message)
            > constants.MAX_PROMPT_TOKENS
        ):
            return self._extract_in_windows(meta, sentences, speakers, job_id)
        return self._extract_once(meta, sentences, speakers)

    def _extract_once(
        self, meta: MeetingMeta, sentences: list[Sentence], speakers: list[Speaker]
    ) -> Analysis:

        user_message = prompts.build_user_message(meta, sentences, speakers)
        prompts.ensure_within_budget(user_message)
        messages = [
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        return self._complete(messages, f"{_LABEL} extract")

    def _extract_window(
        self, meta: MeetingMeta, sentences: list[Sentence], speakers: list[Speaker]
    ) -> Analysis:

        user_message = prompts.build_user_message(meta, sentences, speakers)
        prompts.ensure_within_budget(user_message)
        messages = [
            {"role": "system", "content": prompts.SYSTEM_PROMPT + "\n" + prompts.WINDOW_SCOPE_LINE},
            {"role": "user", "content": user_message},
        ]
        return self._complete(messages, f"{_LABEL} map")

    def _reduce_windows(self, window_summaries: list[str]) -> Analysis:

        message = prompts.build_reduce_message(window_summaries)
        messages = [
            {"role": "system", "content": prompts.REDUCE_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        return self._complete(messages, f"{_LABEL} reduce")

    def _extract_in_windows(
        self,
        meta: MeetingMeta,
        sentences: list[Sentence],
        speakers: list[Speaker],
        job_id: str | None = None,
    ) -> Analysis:
        jlog = job_log(log, job_id) if job_id else log
        jlog.info("transcript exceeds MAX_PROMPT_TOKENS; switching to map-reduce windows")
        return mapreduce.analyze_long(
            meta, sentences, speakers, self._extract_window, self._reduce_windows, job_id=job_id
        )

    def _correct_schema(self, messages: list[dict], first: str, exc: ValidationError) -> Analysis:

        log.warning("analysis schema mismatch, asking for one correction: %s", exc)
        messages.append({"role": "assistant", "content": first})
        messages.append({"role": "user", "content": prompts.build_correction_message(str(exc))})
        return self._parse_or_raise(self._send(messages))

    def _require_arabic(
        self, messages: list[dict], first: str, first_analysis: Analysis
    ) -> Analysis:

        if _has_arabic_output(first_analysis):
            return first_analysis
        log.warning("analysis reply had no Arabic values, asking for one Arabic retry")
        messages.append({"role": "assistant", "content": first})
        messages.append({"role": "user", "content": prompts.build_arabic_output_message()})
        second = self._parse_or_raise(self._send(messages))
        if _has_arabic_output(second):
            return second
        raise AnalysisError("analysis.failed", "second reply still had no Arabic values")

    def _parse_or_raise(self, content: str) -> Analysis:

        try:
            return self._parse(content)
        except ValidationError as second:
            raise AnalysisError(
                "analysis.failed", f"second validation failure: {second}"
            ) from second

    def _require_key(self) -> None:
        if not self._settings.groq_api_key:
            raise AnalysisError("groq.key_missing", "GROQ_API_KEY empty")

    def _assert_model_available(self) -> None:
        available = available_models(self._settings)
        if not available:
            return
        configured = self._settings.groq_llm_model
        if configured in available:
            return
        named = suggest_models(available)
        raise AnalysisError(
            "analysis.model_deprecated",
            f"configured model {configured!r} absent from /models",
        ).with_available(named)

    def _parse(self, content: str) -> Analysis:
        return Analysis.model_validate(_json_object(content))

    def _complete(self, messages: list[dict], label: str) -> Analysis:

        first = self._send(messages)
        try:
            first_analysis = self._parse(first)
        except ValidationError as exc:
            return self._correct_schema(messages, first, exc)
        return self._require_arabic(messages, first, first_analysis)

    def _send(self, messages: list[dict]) -> str:
        return self._transport.send(messages)
