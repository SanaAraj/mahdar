import logging
import re
import subprocess
from pathlib import Path

from app import constants
from app.shared.errors import AudioError

log = logging.getLogger(__name__)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=constants.FFMPEG_TIMEOUT_S
        )
    except FileNotFoundError as exc:
        raise AudioError("audio.ffmpeg_missing", "ffmpeg/ffprobe executables not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise AudioError("audio.corrupt", "ffmpeg timed out") from exc


def probe_duration(path: Path) -> float:
    proc = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    if proc.returncode != 0:
        raise AudioError("audio.corrupt", proc.stderr.strip())
    try:
        return float(proc.stdout.strip())
    except ValueError as exc:
        raise AudioError("audio.corrupt", f"unparseable duration: {proc.stdout!r}") from exc


def convert_if_missing(src: Path, dst: Path, options: list[str], label: str) -> None:
    if dst.exists() and dst.stat().st_size > 0:
        return
    proc = _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), *options, str(dst)])
    if proc.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
        dst.unlink(missing_ok=True)
        raise AudioError("audio.corrupt", f"{label}: {proc.stderr.strip()}")


def to_wav16k_mono(src: Path, dst: Path) -> None:
    convert_if_missing(src, dst, ["-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le"], "wav convert")


def to_mp3_mono_64k(src: Path, dst: Path) -> None:
    convert_if_missing(src, dst, ["-ac", "1", "-b:a", "64k", "-c:a", "libmp3lame"], "mp3 convert")


def split_at_silences(
    mp3: Path, dst_dir: Path, max_part_s: int = constants.SPLIT_PART_LENGTH_S
) -> list[tuple[Path, float, float]]:

    dst_dir.mkdir(parents=True, exist_ok=True)
    silences = detect_silences(mp3)
    duration = probe_duration(mp3)
    points = pick_split_points(silences, duration, max_part_s)
    parts: list[tuple[Path, float, float]] = []
    prev = 0.0
    for index, point in enumerate([*points, duration]):
        part = dst_dir / f"part{index + 1:02d}.mp3"
        segment_to(mp3, part, prev, point)
        if part.stat().st_size > 0:
            parts.append((part, prev, point))
        if point - prev < constants.SPLIT_MIN_PART_S and not parts:
            break
        prev = point
    if not parts:
        raise AudioError("audio.split_failed", "split produced no parts")
    return parts


def detect_silences(mp3: Path) -> list[float]:
    noise = constants.SILENCE_NOISE_DB
    hold = constants.SILENCE_MIN_DURATION_S
    proc = _run(
        [
            "ffmpeg",
            "-i",
            str(mp3),
            "-af",
            f"silencedetect=noise={noise}:d={hold}",
            "-f",
            "null",
            "-",
        ]
    )
    return [float(m.group(1)) for m in re.finditer(r"silence_end: ([0-9.]+)", proc.stderr)]


def pick_split_points(silences: list[float], duration: float, max_part_s: int) -> list[float]:
    points: list[float] = []
    cursor = 0.0
    while cursor + max_part_s < duration - constants.SPLIT_EDGE_MARGIN_S:
        target = cursor + max_part_s
        back = constants.SPLIT_SEARCH_BACK_S
        forward = constants.SPLIT_SEARCH_FORWARD_S
        near = [s for s in silences if target - back <= s <= target + forward]
        point = min(near, key=lambda s: abs(s - target)) if near else target
        points.append(point)
        cursor = point
    return points


def segment_to(src: Path, dst: Path, start: float, end: float) -> None:
    proc = _run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{end:.3f}",
            "-i",
            str(src),
            "-c",
            "copy",
            str(dst),
        ]
    )
    if proc.returncode != 0 or not dst.exists():
        raise AudioError("audio.split_failed", proc.stderr.strip())
