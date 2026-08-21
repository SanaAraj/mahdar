import re
from pathlib import Path

from fastapi import UploadFile

from app import constants
from app.shared.errors import UploadError


def extension_of(filename: str) -> str:
    match = re.search(r"\.([A-Za-z0-9]+)$", filename)
    return match.group(1).lower() if match else ""


async def save_upload(audio: UploadFile, dst: Path, max_bytes: int) -> int:
    """Stream the upload to disk in chunks; reject mid-stream when oversized.

    Reads at most one chunk past the cap, then deletes the partial file, so an
    over-cap body is never fully buffered (the with-block closes the handle).
    """
    size = 0
    with dst.open("wb") as fh:
        while chunk := await audio.read(constants.UPLOAD_CHUNK_BYTES):
            size += len(chunk)
            if size > max_bytes:
                dst.unlink(missing_ok=True)
                raise UploadError("upload.file_too_large", f"{size} bytes > {max_bytes}")
            fh.write(chunk)
    await audio.close()
    return size
