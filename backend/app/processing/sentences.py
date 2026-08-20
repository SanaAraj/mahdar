"""Turns timestamped words into sentences with logical endings."""

from backend.app import constants
from backend.app.core.models import Sentence, Word


def words_to_sentences(words: list[Word]) -> list[Sentence]:
    """Group words into sentences, closed by punctuation, pause, or hard limits."""
    sentences: list[Sentence] = []
    current: list[Word] = []
    for index, word in enumerate(words):
        current.append(word)
        if _should_close(current, words, index):
            sentences.append(_build(sentences, current))
            current = []
    if current:
        sentences.append(_build(sentences, current))
    return sentences


def _should_close(current: list[Word], words: list[Word], index: int) -> bool:
    word = words[index]
    duration = word.end - current[0].start
    if len(current) >= constants.SENTENCE_MAX_WORDS:
        return True
    if duration >= constants.SENTENCE_MAX_DURATION_S:
        return True
    if index + 1 < len(words):
        gap = words[index + 1].start - word.end
        if gap >= constants.SENTENCE_PAUSE_GAP_S:
            return True
    return _ends_with_closer(word.text)


def _ends_with_closer(text: str) -> bool:
    cleaned = text.strip()
    if cleaned in constants.ARABIC_HONORIFICS:
        return False
    return bool(cleaned) and cleaned[-1] in constants.SENTENCE_TERMINATORS


def _build(sentences: list[Sentence], current: list[Word]) -> Sentence:
    text = " ".join(w.text for w in current).strip()
    return Sentence(
        id=f"s{len(sentences) + 1}",
        start=round(current[0].start, 3),
        end=round(current[-1].end, 3),
        text=text,
    )
