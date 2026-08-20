"""Resilience edges through the mocked pipeline: near-silence, corrupt audio,
and a single-speaker clip. The pipeline runs for real against a generated wav;
only the providers are mocked, as in tests/test_api.py.
"""

import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import strings
from backend.app.config import get_settings
from backend.app.core.jobs import JobRegistry
from backend.app.core.models import JobStatus, Turn
from backend.app.main import create_app
from backend.app.providers.diarize_local import LocalDiarizer
from backend.app.providers.llm_groq import GroqMinutesExtractor
from backend.app.providers.stt_groq import GroqTranscriber

from .test_api import fake_analysis

WAIT_TIMEOUT_S = 15.0


@pytest.fixture
def near_silence_wav(tmp_path: Path) -> Path:
    """A 20-second near-silence clip: a real wav the convert stage can probe."""
    path = tmp_path / "silence.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anoisesrc=color=white:amplitude=0.0001:duration=20",
            str(path),
        ],
        check=True,
    )
    return path


@pytest.fixture
def one_speaker_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    get_settings.cache_clear()
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data1spk"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "5")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("HF_TOKEN", "hf-test")
    get_settings.cache_clear()
    return TestClient(create_app())


def _wait(client: TestClient, job_id: str) -> dict:
    deadline = time.monotonic() + WAIT_TIMEOUT_S
    while time.monotonic() < deadline:
        job = client.get(f"/api/meetings/{job_id}").json()
        if job["status"] in (JobStatus.DONE, JobStatus.FAILED):
            return job
        time.sleep(0.2)
    raise AssertionError("job did not finish in time")


def test_near_silence_finishes_clean_with_few_sentences(
    one_speaker_client: TestClient, near_silence_wav: Path, monkeypatch: pytest.MonkeyPatch
):
    """A 20s near-silence clip yields zero words, hence zero sentences, and the
    job still reaches done with a clean analysis of the empty transcript."""
    monkeypatch.setattr(GroqTranscriber, "transcribe", lambda self, w, m: [])
    monkeypatch.setattr(
        GroqMinutesExtractor,
        "extract",
        lambda self, meta, sentences, speakers, job_id=None: fake_analysis(),
    )
    monkeypatch.setattr(
        LocalDiarizer, "diarize", lambda self, w: [Turn(start=0.0, end=20.0, speaker="SPEAKER_00")]
    )
    with near_silence_wav.open("rb") as fh:
        job_id = one_speaker_client.post(
            "/api/meetings", files={"audio": ("silence.wav", fh, "audio/wav")}
        ).json()["id"]
    job = _wait(one_speaker_client, job_id)
    assert job["status"] == JobStatus.DONE
    assert job["sentences"] == []  # no speech became no sentences, none invented
    # No repeated-sentence hallucination: whatever words stayed are few and unique.
    texts = [s["text"] for s in job["sentences"]]
    assert len(texts) == len(set(texts))


def test_corrupt_upload_yields_arabic_audio_error(
    one_speaker_client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A file that ffmpeg cannot decode fails the convert stage with the Arabic
    corrupt-audio message, so the UI surfaces a clean reason, never a trace."""
    monkeypatch.setattr(GroqTranscriber, "transcribe", lambda self, w, m: [])
    bad = tmp_path / "broken.wav"
    bad.write_bytes(b"not a real wav at all, just bytes")
    with bad.open("rb") as fh:
        job_id = one_speaker_client.post(
            "/api/meetings", files={"audio": ("broken.wav", fh, "audio/wav")}
        ).json()["id"]
    job = _wait(one_speaker_client, job_id)
    assert job["status"] == JobStatus.FAILED
    assert job["error_ar"] == strings.resolve("audio.corrupt")


def test_single_speaker_clip_yields_one_speaker_chip(
    one_speaker_client: TestClient, near_silence_wav: Path, monkeypatch: pytest.MonkeyPatch
):
    """A diarizer that returns one turn for the whole clip yields exactly one
    speaker chip on the wire, not an empty or duplicated bar."""
    from .factories import make_words

    monkeypatch.setattr(
        GroqTranscriber,
        "transcribe",
        lambda self, w, m: make_words(["أهلاً", "بالجميع", "هنا"], step=0.4),
    )
    monkeypatch.setattr(
        GroqMinutesExtractor,
        "extract",
        lambda self, meta, sentences, speakers, job_id=None: fake_analysis(),
    )
    monkeypatch.setattr(
        LocalDiarizer, "diarize", lambda self, w: [Turn(start=0.0, end=20.0, speaker="SPEAKER_00")]
    )
    with near_silence_wav.open("rb") as fh:
        job_id = one_speaker_client.post(
            "/api/meetings", files={"audio": ("silence.wav", fh, "audio/wav")}
        ).json()["id"]
    job = _wait(one_speaker_client, job_id)
    assert job["status"] == JobStatus.DONE
    assert len(job["speakers"]) == 1
    assert job["speakers"][0]["id"] == "SPEAKER_00"
    # The one cell stays consistent on a registry reload.
    fresh = JobRegistry(one_speaker_client.app.state.settings.data_dir)
    assert len(fresh.get(job_id).speakers) == 1
