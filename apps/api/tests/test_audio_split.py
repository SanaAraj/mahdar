import httpx
import pytest
import respx

from app.config import Settings
from app.features.transcription import stt_groq
from app.shared.audio import pick_split_points
from app.shared.errors import AudioError


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


@respx.mock
def test_part_offset_uses_intended_span_not_drifted_probe(monkeypatch, tmp_path):

    part1 = tmp_path / "part01.mp3"
    part2 = tmp_path / "part02.mp3"
    part1.write_bytes(b"audio")
    part2.write_bytes(b"audio")

    spans = [(part1, 0.0, 10.0), (part2, 10.0, 20.0)]
    monkeypatch.setattr(stt_groq, "split_at_silences", lambda *a, **k: spans)

    durations = {part1: 9.7, part2: 10.0}
    monkeypatch.setattr(stt_groq, "_duration_of", lambda path: durations[path])

    def word_payload(text: str) -> dict:

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
    assert words[1].start == pytest.approx(10.0)


@respx.mock
def test_excess_part_drift_fails_loudly(monkeypatch, tmp_path):

    part1 = tmp_path / "part01.mp3"
    part1.write_bytes(b"audio")
    monkeypatch.setattr(stt_groq, "split_at_silences", lambda *a, **k: [(part1, 0.0, 10.0)])

    monkeypatch.setattr(stt_groq, "_duration_of", lambda path: 8.0)
    respx.post(stt_groq._API_URL).mock(
        return_value=httpx.Response(
            200, json={"text": "أول", "words": [{"start": 0.0, "end": 0.4, "word": "أول"}]}
        )
    )
    settings = Settings(groq_api_key="test-key")
    with pytest.raises(AudioError, match="split_failed"):
        stt_groq.GroqTranscriber(settings)._transcribe_parts(tmp_path / "a.mp3")
