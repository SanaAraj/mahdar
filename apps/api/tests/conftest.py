import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def wav_file(tmp_path: Path) -> Path:
    path = tmp_path / "tone.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            str(path),
        ],
        check=True,
    )
    return path
