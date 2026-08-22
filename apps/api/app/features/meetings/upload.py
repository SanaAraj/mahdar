import re
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile

from app import constants
from app.features.meetings import sniff
from app.shared.errors import UploadError


def extension_of(filename: str) -> str:
    match = re.search(r"\.([A-Za-z0-9]+)$", filename)
    return match.group(1).lower() if match else ""


async def save_upload(audio: UploadFile, dst: Path, max_bytes: int) -> int:
    try:
        size = 0
        with dst.open("wb") as fh:
            first = True
            while chunk := await audio.read(constants.UPLOAD_CHUNK_BYTES):
                if first:
                    _reject_not_audio(chunk, dst, fh)
                    first = False
                size += len(chunk)
                if size > max_bytes:
                    _abort(dst, fh)
                    raise UploadError("upload.file_too_large", f"{size} bytes > {max_bytes}")
                fh.write(chunk)
        return size
    finally:
        await audio.close()


def _reject_not_audio(header: bytes, dst: Path, fh: BinaryIO) -> None:

    if sniff.looks_like_audio(header[: constants.AUDIO_HEADER_BYTES]):
        return
    _abort(dst, fh)
    raise UploadError("upload.bad_signature", f"head={header[:12].hex()}")


def _abort(dst: Path, fh: BinaryIO) -> None:
    fh.close()
    dst.unlink(missing_ok=True)
