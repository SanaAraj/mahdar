import threading
import time
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.features.analysis.llm_groq import GroqMinutesExtractor
from app.features.meetings.sniff import looks_like_audio
from app.features.transcription.stt_groq import GroqTranscriber
from app.main import create_app
from app.shared.models import Analysis, Topic

from .test_api import fake_transcribe

WEBM = bytes([0x1A, 0x45, 0xDF, 0xA3]) + b"\x00" * 60
OGG = b"OggS" + b"\x00" * 60
WAV = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 52
MP3_ID3 = b"ID3" + b"\x00" * 61
MP3_FRAME = bytes([0xFF, 0xFB]) + b"\x00" * 62
MP4 = b"\x00" * 4 + b"ftyp" + b"M4A " + b"\x00" * 52


def test_sniff_accepts_supported_containers():
    for header in (WEBM, OGG, WAV, MP3_ID3, MP3_FRAME, MP4):
        assert looks_like_audio(header), header[:8]


def test_sniff_rejects_disguised_binary():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 56
    pdf = b"%PDF-1.4" + b"\x00" * 56
    zip_head = b"PK\x03\x04" + b"\x00" * 60
    for header in (png, pdf, zip_head):
        assert not looks_like_audio(header)


def _fake_extract(self, meta, sentences, speakers, job_id=None):
    return Analysis(
        title="اجتماع",
        attendees=["المتحدث 1"],
        topics=[Topic(title="الخدمة", summary="نوقشت الخدمة", segment_ids=["s1"])],
        decisions=[],
        directives=[],
        tasks=[],
    )


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    get_settings.cache_clear()
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("HF_TOKEN", "")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    monkeypatch.setattr(GroqTranscriber, "transcribe", fake_transcribe)
    monkeypatch.setattr(GroqMinutesExtractor, "extract", _fake_extract)
    return TestClient(create_app())


def test_fake_audio_signature_rejected_415(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    fake = tmp_path / "fake.mp3"
    fake.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    client = _client(tmp_path, monkeypatch, RATE_LIMIT_ENABLED="false")
    response = client.post(
        "/api/meetings", files={"audio": ("fake.mp3", fake.read_bytes(), "audio/mpeg")}
    )
    assert response.status_code == 415
    assert "error_ar" in response.json()


def test_real_wav_upload_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wav_file: Path):
    client = _client(tmp_path, monkeypatch, RATE_LIMIT_ENABLED="false")
    response = client.post(
        "/api/meetings", files={"audio": ("clip.wav", wav_file.read_bytes(), "audio/wav")}
    )
    assert response.status_code == 201


def test_upload_rate_limit_returns_429(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wav_file: Path
):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    client = _client(
        tmp_path,
        monkeypatch,
        RATE_LIMIT_ENABLED="true",
        MAX_ACTIVE_JOBS="8",
    )
    body = wav_file.read_bytes()
    statuses = [
        client.post("/api/meetings", files={"audio": ("clip.wav", body, "audio/wav")}).status_code
        for _ in range(4)
    ]
    assert 429 in statuses
    assert client.get("/api/health").status_code == 200


def test_upload_rate_limit_separates_proxy_clients(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wav_file: Path
):
    client = _client(
        tmp_path,
        monkeypatch,
        RATE_LIMIT_ENABLED="true",
        MAX_ACTIVE_JOBS="8",
    )
    body = wav_file.read_bytes()
    statuses = [
        client.post(
            "/api/meetings",
            files={"audio": ("clip.wav", body, "audio/wav")},
            headers={"X-Mahdar-Client-IP": f"198.51.100.{index}"},
        ).status_code
        for index in range(1, 5)
    ]
    assert statuses == [201, 201, 201, 201]


def test_busy_server_returns_503_when_first_job_holds_the_only_slot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wav_file: Path
):
    gate = threading.Event()

    def slow_transcribe(self, wav_path, mp3_path):
        gate.wait(timeout=30)
        return fake_transcribe(self, wav_path, mp3_path)

    monkeypatch.setattr(GroqTranscriber, "transcribe", slow_transcribe)
    client = _client(tmp_path, monkeypatch, RATE_LIMIT_ENABLED="false", MAX_ACTIVE_JOBS="1")
    body = wav_file.read_bytes()
    start = time.time()
    first = client.post("/api/meetings", files={"audio": ("one.wav", body, "audio/wav")})
    assert first.status_code == 201
    job_id = first.json()["id"]

    for _ in range(200):
        response = client.get(f"/api/meetings/{job_id}")
        if response.status_code == 200 and response.json()["status"] in {
            "converting",
            "transcribing",
            "diarizing",
        }:
            break
        time.sleep(0.05)
    assert time.time() - start < 15, "first job never reached a running stage"

    second = client.post("/api/meetings", files={"audio": ("two.wav", body, "audio/wav")})
    gate.set()
    assert second.status_code == 503
    assert second.headers.get("retry-after") == "30"
    assert "error_ar" in second.json()


def test_failed_pipeline_admission_removes_job_and_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wav_file: Path
):
    client = _client(tmp_path, monkeypatch, RATE_LIMIT_ENABLED="false")
    job_id = "a" * 12
    monkeypatch.setattr(
        "app.features.meetings.routes.uuid.uuid4",
        lambda: UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    )
    monkeypatch.setattr(client.app.state.pipeline, "start", lambda _job_id: False)

    response = client.post(
        "/api/meetings",
        files={"audio": ("meeting.wav", wav_file.read_bytes(), "audio/wav")},
    )

    assert response.status_code == 503
    assert client.app.state.registry.get(job_id) is None
    assert not client.app.state.registry.job_dir(job_id).exists()
