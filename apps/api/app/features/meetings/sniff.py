def looks_like_audio(header: bytes) -> bool:

    return any(
        probe(header) for probe in (_is_webm, _is_ogg, _is_wav, _is_id3, _is_mp3_frame, _is_ftyp)
    )


def _is_webm(header: bytes) -> bool:
    return header[:4] == b"\x1a\x45\xdf\xa3"


def _is_ogg(header: bytes) -> bool:
    return header[:4] == b"OggS"


def _is_wav(header: bytes) -> bool:
    return header[:4] == b"RIFF" and header[8:12] == b"WAVE"


def _is_id3(header: bytes) -> bool:
    return header[:3] == b"ID3"


def _is_mp3_frame(header: bytes) -> bool:
    return len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0


def _is_ftyp(header: bytes) -> bool:

    return header[4:8] == b"ftyp"
