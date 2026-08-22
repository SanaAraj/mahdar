from pathlib import Path

import httpx
import pytest
import respx

from app import constants
from app.config import Settings
from app.features.transcription.stt_cohere import CohereTranscriber
from app.shared.errors import TranscriptionError

_URL = constants.COHERE_API_BASE + constants.STT_API_PATH


def _settings(**overrides) -> Settings:
    values = {"cohere_api_key": "test-key", "stt_provider": "cohere"}
    values.update(overrides)
    return Settings(**values)


def _audio(tmp_path: Path) -> tuple[Path, Path]:
    wav = tmp_path / "audio.wav"
    mp3 = tmp_path / "audio.mp3"
    wav.write_bytes(b"wav")
    mp3.write_bytes(b"mp3")
    return wav, mp3


@respx.mock
def test_transcribe_maps_text_to_approximate_word_timings(monkeypatch, tmp_path: Path):
    wav, mp3 = _audio(tmp_path)
    monkeypatch.setattr("app.features.transcription.stt_cohere.probe_duration", lambda _: 6.0)
    route = respx.post(_URL).mock(httpx.Response(200, json={"text": "مرحبا بكم اليوم"}))

    words = CohereTranscriber(_settings()).transcribe(wav, mp3)

    assert [word.text for word in words] == ["مرحبا", "بكم", "اليوم"]
    assert [(word.start, word.end) for word in words] == [
        (0.0, 2.0),
        (2.0, 4.0),
        (4.0, 6.0),
    ]
    request = route.calls[0].request
    assert b"cohere-transcribe-arabic-07-2026" in request.content
    assert b'name="language"\r\n\r\nar' in request.content


def test_missing_key_fails_before_reading_audio(tmp_path: Path):
    wav, mp3 = _audio(tmp_path)
    with pytest.raises(TranscriptionError) as exc:
        CohereTranscriber(_settings(cohere_api_key="")).transcribe(wav, mp3)
    assert exc.value.message_key == "cohere.key_missing"


@pytest.mark.parametrize(
    ("status", "message_key"),
    [
        (401, "cohere.key_missing"),
        (400, "audio.corrupt"),
        (422, "cohere.failed"),
    ],
)
@respx.mock
def test_non_retryable_errors(monkeypatch, tmp_path: Path, status: int, message_key: str):
    wav, mp3 = _audio(tmp_path)
    monkeypatch.setattr("app.features.transcription.stt_cohere.probe_duration", lambda _: 1.0)
    respx.post(_URL).mock(httpx.Response(status, text="failure"))
    with pytest.raises(TranscriptionError) as exc:
        CohereTranscriber(_settings()).transcribe(wav, mp3)
    assert exc.value.message_key == message_key


@respx.mock
def test_rate_limit_retries_and_honors_retry_after(monkeypatch, tmp_path: Path):
    wav, mp3 = _audio(tmp_path)
    slept: list[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    monkeypatch.setattr(constants, "HTTP_JITTER_S", 0)
    monkeypatch.setattr("app.features.transcription.stt_cohere.probe_duration", lambda _: 1.0)
    route = respx.post(_URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "3"}),
            httpx.Response(200, json={"text": "مرحبا"}),
        ]
    )

    words = CohereTranscriber(_settings()).transcribe(wav, mp3)

    assert words[0].text == "مرحبا"
    assert len(route.calls) == 2
    assert slept == [3.0]


def test_split_parts_preserve_offsets(monkeypatch, tmp_path: Path):
    mp3 = tmp_path / "audio.mp3"
    first = tmp_path / "first.mp3"
    second = tmp_path / "second.mp3"
    for path in (mp3, first, second):
        path.write_bytes(b"audio")
    parts = [(first, 0.0, 2.0), (second, 2.0, 5.0)]
    monkeypatch.setattr(
        "app.features.transcription.stt_cohere.split_at_silences", lambda *args: parts
    )
    monkeypatch.setattr(
        "app.features.transcription.stt_cohere.probe_duration",
        lambda path: 2.0 if path == first else 3.0,
    )
    transcriber = CohereTranscriber(_settings())
    responses = iter(["مرحبا بكم", "في الاجتماع اليوم"])
    monkeypatch.setattr(transcriber, "_request", lambda _: next(responses))

    words = transcriber._transcribe_parts(mp3)

    assert [word.text for word in words] == ["مرحبا", "بكم", "في", "الاجتماع", "اليوم"]
    assert words[0].start == 0.0
    assert words[1].end == 2.0
    assert words[2].start == 2.0
    assert words[-1].end == 5.0


@respx.mock
def test_empty_and_invalid_responses(monkeypatch, tmp_path: Path):
    wav, mp3 = _audio(tmp_path)
    monkeypatch.setattr("app.features.transcription.stt_cohere.probe_duration", lambda _: 1.0)
    route = respx.post(_URL).mock(
        side_effect=[
            httpx.Response(200, json={"text": ""}),
            httpx.Response(200, text="not-json"),
        ]
    )
    transcriber = CohereTranscriber(_settings())

    with pytest.raises(TranscriptionError) as empty:
        transcriber.transcribe(wav, mp3)
    with pytest.raises(TranscriptionError) as invalid:
        transcriber.transcribe(wav, mp3)

    assert empty.value.message_key == "transcription.empty"
    assert invalid.value.message_key == "cohere.failed"
    assert len(route.calls) == 2
