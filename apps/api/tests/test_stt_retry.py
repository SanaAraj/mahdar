"""The STT provider tags words with segment stats and honors Retry-After on 429."""

from pathlib import Path

import httpx
import respx

from app import constants
from app.config import Settings
from app.features.transcription.stt_groq import GroqTranscriber

_URL = constants.GROQ_API_BASE + constants.STT_API_PATH


def _settings() -> Settings:
    return Settings(groq_api_key="test-key")


def _words_payload() -> dict:
    return {
        "text": "مرحبا",
        "words": [{"start": 0.0, "end": 0.4, "word": "مرحبا"}],
    }


@respx.mock
def test_stt_429_honors_retry_after(monkeypatch, tmp_path: Path):
    slept: list[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    monkeypatch.setattr(constants, "HTTP_JITTER_S", 0)  # deterministic sleep assertion
    mp3 = tmp_path / "a.mp3"
    mp3.write_bytes(b"audio")
    route = respx.post(_URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "90"}, text="limited"),
            httpx.Response(200, json=_words_payload()),
        ]
    )
    words = GroqTranscriber(_settings()).transcribe(tmp_path / "a.wav", mp3)
    assert words and words[0].text == "مرحبا"
    assert len(route.calls) == 2
    # The leaked hint (90s) is capped at the one-minute window constant.
    assert slept == [constants.RETRY_AFTER_MAX_S]


def test_words_inherit_segment_stats_and_omit_them_when_absent():
    transcriber = GroqTranscriber(_settings())
    with_stats = {
        "text": "مرحبا بكم",
        "words": [
            {"start": 0.0, "end": 0.4, "word": "مرحبا"},
            {"start": 0.4, "end": 0.8, "word": "بكم"},
        ],
        "segments": [{"start": 0.0, "end": 1.0, "text": "مرحبا بكم", "no_speech_prob": 0.92}],
    }
    tagged = transcriber._payload_to_words(with_stats, 0.0)
    assert [w.no_speech_prob for w in tagged] == [0.92, 0.92]
    plain = transcriber._payload_to_words(_words_payload(), 0.0)
    assert plain[0].no_speech_prob is None
