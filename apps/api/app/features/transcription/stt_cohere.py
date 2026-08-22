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

_LABEL = "Cohere STT"
_API_URL = constants.COHERE_API_BASE + constants.STT_API_PATH


class CohereTranscriber:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def transcribe(self, wav_path: Path, mp3_path: Path) -> list[Word]:
        if not self._settings.cohere_api_key:
            raise TranscriptionError("cohere.key_missing", "COHERE_API_KEY empty")
        if mp3_path.stat().st_size > constants.MAX_SINGLE_UPLOAD_BYTES:
            return self._transcribe_parts(mp3_path)
        return self._transcribe_file(mp3_path, 0.0, probe_duration(wav_path))

    def _transcribe_parts(self, mp3_path: Path) -> list[Word]:
        parts_dir = mp3_path.parent / "parts"
        parts = split_at_silences(mp3_path, parts_dir, constants.SPLIT_PART_LENGTH_S)
        log.info("Split oversized upload into %d part(s)", len(parts))
        words: list[Word] = []
        for part, start, end in parts:
            duration = end - start
            probed = probe_duration(part)
            if abs(probed - duration) > constants.PART_WORD_OVERLAP_S:
                raise AudioError(
                    "audio.split_failed",
                    f"part length {probed:.3f}s drifts from intended {duration:.3f}s",
                )
            words.extend(self._transcribe_file(part, start, duration))
        return words

    def _transcribe_file(self, mp3_path: Path, offset: float, duration: float) -> list[Word]:
        def attempt() -> list[Word]:
            return self._text_to_words(self._request(mp3_path), offset, duration)

        return run_with_retries(attempt, _LABEL)

    def _request(self, mp3_path: Path) -> str:
        data = {"model": self._settings.cohere_stt_model, "language": "ar"}
        headers = {"Authorization": f"Bearer {self._settings.cohere_api_key}"}
        try:
            with mp3_path.open("rb") as fh:
                with httpx.Client(timeout=constants.STT_TIMEOUT_S) as client:
                    response = client.post(
                        _API_URL,
                        data=data,
                        files={"file": (mp3_path.name, fh, "audio/mpeg")},
                        headers=headers,
                    )
        except httpx.TimeoutException as exc:
            raise RetryableError(
                TranscriptionError("cohere.unavailable", f"timeout {exc}")
            ) from exc
        except httpx.TransportError as exc:
            raise RetryableError(TranscriptionError("cohere.unavailable", str(exc))) from exc
        if response.status_code >= 400:
            raise _http_error(response)
        try:
            text = response.json().get("text", "").strip()
        except (AttributeError, ValueError) as exc:
            raise TranscriptionError("cohere.failed", "invalid json") from exc
        if not text:
            raise TranscriptionError("transcription.empty", "empty transcript")
        return text

    def _text_to_words(self, text: str, offset: float, duration: float) -> list[Word]:
        tokens = text.split()
        if not tokens:
            raise TranscriptionError("transcription.empty", "empty transcript")
        step = duration / len(tokens)
        return [
            Word(
                start=offset + index * step,
                end=offset + (index + 1) * step,
                text=token,
            )
            for index, token in enumerate(tokens)
        ]


def _http_error(response: httpx.Response) -> Exception:
    snippet = response.text[: constants.ERROR_SNIPPET_CHARS]
    if response.status_code in (401, 403):
        return TranscriptionError("cohere.key_missing", f"auth {response.status_code}")
    if response.status_code == 400:
        return TranscriptionError("audio.corrupt", f"400 {snippet}")
    if response.status_code == 429:
        return RetryableError(
            TranscriptionError("cohere.rate_limit", "429 rate limited"),
            retry_after=retry_after_seconds(response),
        )
    if response.status_code >= 500:
        return RetryableError(
            TranscriptionError("cohere.unavailable", f"{response.status_code} {snippet}")
        )
    return TranscriptionError("cohere.failed", f"{response.status_code} {snippet}")
