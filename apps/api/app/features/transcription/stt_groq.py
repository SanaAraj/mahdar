import logging
from pathlib import Path

import httpx

from app import constants
from app.config import Settings
from app.shared.audio import probe_duration, split_at_silences
from app.shared.errors import AudioError, TranscriptionError
from app.shared.models import Word
from app.shared.retry import RetryableError, retry_after_seconds, run_with_retries

log = logging.getLogger(__name__)

_LABEL = "Groq STT"
_TEXT_KEYS = ("word", "text", "token", "segment")
_SEGMENT_STAT_KEYS: tuple[str, ...] = ("no_speech_prob", "avg_logprob", "compression_ratio")
_API_URL = constants.GROQ_API_BASE + constants.STT_API_PATH
_FALLBACK_WORD_DURATION_S: float = 1.0


def _dict_items(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _word_span(item: dict, offset: float) -> tuple[float, float] | None:

    try:
        return float(item["start"]) + offset, float(item["end"]) + offset
    except (KeyError, TypeError, ValueError):
        return None


def _duration_of(path: Path) -> float:
    return probe_duration(path)


def _assert_part_span(probed: float, intended: float) -> None:

    if abs(probed - intended) > constants.PART_WORD_OVERLAP_S:
        raise AudioError(
            "audio.split_failed",
            f"part length {probed:.3f}s drifts from intended {intended:.3f}s",
        )


class GroqTranscriber:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def transcribe(self, wav_path: Path, mp3_path: Path) -> list[Word]:
        if not self._settings.groq_api_key:
            raise TranscriptionError("groq.key_missing", "GROQ_API_KEY empty")
        if mp3_path.stat().st_size > constants.MAX_SINGLE_UPLOAD_BYTES:
            return self._transcribe_parts(mp3_path)
        return self._transcribe_file(mp3_path, offset=0.0)

    def _transcribe_parts(self, mp3_path: Path) -> list[Word]:
        parts_dir = mp3_path.parent / "parts"
        parts = split_at_silences(mp3_path, parts_dir, constants.SPLIT_PART_LENGTH_S)
        log.info("Split oversized upload into %d part(s)", len(parts))
        words: list[Word] = []
        cursor = 0.0
        for part, intended_start, intended_end in parts:
            _assert_part_span(_duration_of(part), intended_end - intended_start)
            window_end = cursor + (intended_end - intended_start)
            part_words = self._transcribe_file(part, offset=cursor)
            words.extend(
                w for w in part_words if w.start < window_end + constants.PART_WORD_OVERLAP_S
            )
            cursor = window_end
        return words

    def _transcribe_file(self, mp3_path: Path, offset: float) -> list[Word]:
        def attempt() -> list[Word]:
            payload = self._request(mp3_path)
            return self._payload_to_words(payload, offset)

        return run_with_retries(attempt, _LABEL)

    def _request(self, mp3_path: Path) -> dict:
        data = {
            "model": self._settings.groq_stt_model,
            "response_format": "verbose_json",
            "language": "ar",
            "temperature": "0",
            "timestamp_granularities[]": ["word", "segment"],
        }
        headers = {"Authorization": f"Bearer {self._settings.groq_api_key}"}
        try:
            with mp3_path.open("rb") as fh:
                with httpx.Client(timeout=constants.STT_TIMEOUT_S) as client:
                    resp = client.post(
                        _API_URL,
                        data=data,
                        files={"file": (mp3_path.name, fh, "audio/mpeg")},
                        headers=headers,
                    )
        except httpx.TimeoutException as exc:
            raise RetryableError(TranscriptionError("groq.unavailable", f"timeout {exc}")) from exc
        except httpx.TransportError as exc:
            raise RetryableError(TranscriptionError("groq.unavailable", str(exc))) from exc
        if resp.status_code >= 400:
            raise _http_error(resp)
        try:
            payload = resp.json()
        except ValueError as exc:
            raise TranscriptionError("groq.failed", "invalid json") from exc
        if not payload.get("text") and not payload.get("segments"):
            raise TranscriptionError("transcription.empty", "empty transcript")
        return payload

    def _payload_to_words(self, payload: dict, offset: float) -> list[Word]:
        segments = payload.get("segments")
        words = self._map_words(payload.get("words"), offset, segments)
        if words:
            return words
        return self._map_segments(segments, payload.get("text") or "", offset)

    def _map_words(self, raw_words: object, offset: float, raw_segments: object) -> list[Word]:
        spans = _segment_stat_spans(raw_segments, offset)
        mapped: list[Word] = []
        for item in _dict_items(raw_words):
            text = _first_text(item)
            if (span := _word_span(item, offset)) is None:
                continue
            start, end = span
            if text and end > start:
                stats = _stats_at(spans, (start + end) / 2)
                mapped.append(Word(start=start, end=end, text=text, **stats))
        return mapped

    def _map_segments(self, raw_segments: object, full_text: str, offset: float) -> list[Word]:
        segments = [s for s in _dict_items(raw_segments) if str(s.get("text", "")).strip()]
        if not segments and full_text.strip():
            return [
                Word(
                    start=offset,
                    end=offset + _FALLBACK_WORD_DURATION_S,
                    text=full_text.strip(),
                )
            ]
        mapped: list[Word] = []
        for seg in segments:
            text = str(seg["text"]).strip()
            if (span := _word_span(seg, offset)) is None:
                continue
            start, end = span
            if end <= start:
                continue
            mapped.extend(self._slice_segment(text, start, end, _segment_stats_of(seg)))
        return mapped

    def _slice_segment(
        self, text: str, start: float, end: float, stats: dict[str, float] | None = None
    ) -> list[Word]:

        fields = stats or {}
        tokens = text.split()
        if len(tokens) <= 1:
            return [Word(start=start, end=end, text=text, **fields)] if text else []
        span = end - start
        step = span / len(tokens)
        return [
            Word(start=start + i * step, end=start + (i + 1) * step, text=token, **fields)
            for i, token in enumerate(tokens)
        ]


def _first_text(item: dict) -> str:
    for key in _TEXT_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _segment_stats_of(segment: dict) -> dict[str, float]:

    stats: dict[str, float] = {}
    for key in _SEGMENT_STAT_KEYS:
        value = segment.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            stats[key] = float(value)
    return stats


def _segment_stat_spans(
    raw_segments: object, offset: float
) -> list[tuple[float, float, dict[str, float]]]:
    spans: list[tuple[float, float, dict[str, float]]] = []
    for seg in _dict_items(raw_segments):
        stats = _segment_stats_of(seg)
        if not stats or (span := _word_span(seg, offset)) is None:
            continue
        start, end = span
        spans.append((start, end, stats))
    return spans


def _stats_at(
    spans: list[tuple[float, float, dict[str, float]]], moment: float
) -> dict[str, float]:
    for start, end, stats in spans:
        if start <= moment <= end:
            return stats
    return {}


def _http_error(resp: httpx.Response) -> Exception:
    snippet = resp.text[: constants.ERROR_SNIPPET_CHARS]
    if resp.status_code in (401, 403):
        return TranscriptionError("groq.key_missing", f"auth {resp.status_code}")
    if resp.status_code == 400:
        return TranscriptionError("audio.corrupt", f"400 {snippet}")
    if resp.status_code == 429:
        return RetryableError(
            TranscriptionError("groq.rate_limit", "429 rate limited"),
            retry_after=retry_after_seconds(resp),
        )
    if resp.status_code >= 500:
        return RetryableError(
            TranscriptionError("groq.unavailable", f"{resp.status_code} {snippet}")
        )
    return TranscriptionError("groq.failed", f"{resp.status_code} {snippet}")
