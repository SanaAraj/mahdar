from backend.app.core.models import Word

DEFAULT_GAP_S = 0.1


def make_words(
    tokens: list[str],
    start: float = 0.0,
    step: float = 0.4,
    gaps: list[float] | None = None,
) -> list[Word]:
    """Build time-ordered test words, skipping empty tokens.

    gaps is the pause after each token (the default is used when a gap is not
    supplied for that position).
    """
    words: list[Word] = []
    cursor = start
    for index, token in enumerate(tokens):
        if token:
            words.append(Word(start=round(cursor, 3), end=round(cursor + step, 3), text=token))
        gap = gaps[index] if (gaps and index < len(gaps)) else DEFAULT_GAP_S
        cursor += step + gap
    return words
