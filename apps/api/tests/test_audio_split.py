"""Unit tests for long-file splitting around detected silences."""

import httpx
import pytest
import respx

from app.config import Settings
from app.core.errors import AudioError
from app.processing.audio import pick_split_points
from app.providers import stt_groq


def test_no_splits_under_max():
    assert pick_split_points(silences=[10.0, 20.0], duration=200.0, max_part_s=600) == []


def test_hard_cut_without_silence():
    assert pick_split_points(silences=[], duration=1500.0, max_part_s=600) == [600.0, 1200.0]


def test_snaps_to_nearest_silence():
    assert pick_split_points(silences=[605.0, 1210.0], duration=1800.0, max_part_s=600) == [
        605.0,
        1210.0,
    ]


def test_split_points_are_strictly_increasing():
    pts = pick_split_points(
        silences=[610.0, 590.0, 1220.0, 1500.0], duration=1800.0, max_part_s=600
    )
    assert all(a < b for a, b in zip(pts, pts[1:], strict=False))


def test_last_point_below_duration():
    pts = pick_split_points(silences=[1190.0], duration=1300.0, max_part_s=600)
    assert pts[-1] < 1300.0


# ---- split-boundary integrity: later parts must not be shifted by drift ----


@respx.mock
def test_part_offset_uses_intended_span_not_drifted_probe(monkeypatch, tmp_path):
    """A part whose re-encoded duration drifts must not skew the next part.

    The extractor shifts each part's words by a cumulative cursor. Before the
    guard, the cursor advanced by the part's post-hoc probed duration, so a
    part that encodes short pulled every later word earlier by that error. Two
    parts with intended windows [0,10) and [10,20), where part one's probe
    reports 9.7s (within the overlap slack), must still place part two's word
    at the correct 10.0s boundary, not at the drifted 9.7s.
    """
    part1 = tmp_path / "part01.mp3"
    part2 = tmp_path / "part02.mp3"
    part1.write_bytes(b"audio")
    part2.write_bytes(b"audio")
    # Contiguous intended windows [0,10) and [10,20).
    spans = [(part1, 0.0, 10.0), (part2, 10.0, 20.0)]
    monkeypatch.setattr(stt_groq, "split_at_silences", lambda *a, **k: spans)
    # Probed durations: part one drifts to 9.7s (within slack); part two intact.
    durations = {part1: 9.7, part2: 10.0}
    monkeypatch.setattr(stt_groq, "_duration_of", lambda path: durations[path])

    def word_payload(text: str) -> dict:
        # Each part returns one word at its own relative time zero.
        return {"text": text, "words": [{"start": 0.0, "end": 0.4, "word": text}]}

    route = respx.post(stt_groq._API_URL).mock(
        side_effect=[
            httpx.Response(200, json=word_payload("أول")),
            httpx.Response(200, json=word_payload("ثانٍ")),
        ]
    )
    settings = Settings(groq_api_key="test-key")
    words = stt_groq.GroqTranscriber(settings)._transcribe_parts(tmp_path / "a.mp3")
    assert route.call_count == 2
    assert words[0].start == pytest.approx(0.0)
    assert words[1].start == pytest.approx(10.0)  # correct boundary, not drifted 9.7


@respx.mock
def test_excess_part_drift_fails_loudly(monkeypatch, tmp_path):
    """A drift beyond the part-overlap tolerance is a loud split failure.

    Small encodings slack is absorbed by the part-word overlap allowance, but
    a probe that mismatches the intended window by more than that allowance
    means the split boundary is wrong and must raise audio.split_failed
    instead of shifting every later sentence silently.
    """
    part1 = tmp_path / "part01.mp3"
    part1.write_bytes(b"audio")
    monkeypatch.setattr(stt_groq, "split_at_silences", lambda *a, **k: [(part1, 0.0, 10.0)])
    # Intended window is 10.0s, but the probe reports 8.0s (far beyond slack).
    monkeypatch.setattr(stt_groq, "_duration_of", lambda path: 8.0)
    respx.post(stt_groq._API_URL).mock(
        return_value=httpx.Response(
            200, json={"text": "أول", "words": [{"start": 0.0, "end": 0.4, "word": "أول"}]}
        )
    )
    settings = Settings(groq_api_key="test-key")
    with pytest.raises(AudioError, match="split_failed"):
        stt_groq.GroqTranscriber(settings)._transcribe_parts(tmp_path / "a.mp3")
