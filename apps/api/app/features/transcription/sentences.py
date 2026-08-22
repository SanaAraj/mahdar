"""Turns timestamped words into sentences with logical endings."""

from app import constants
from app.features.transcription.speakers import best_speaker
from app.shared.models import Sentence, Turn, Word


def words_to_sentences(words: list[Word], turns: list[Turn] | None = None) -> list[Sentence]:
    """Group words into sentences, closed by punctuation, pause, hard limits,
    or a diarized speaker change. Without turns the behavior is unchanged."""
    marks = _turn_marks(words, turns or [])
    sentences: list[Sentence] = []
    current: list[Word] = []
    for index, word in enumerate(words):
        current.append(word)
        if _should_close(current, words, index, marks):
            sentences.append(_build(sentences, current))
            current = []
    if current:
        sentences.append(_build(sentences, current))
    return sentences


def _turn_marks(words: list[Word], turns: list[Turn]) -> list[str | None]:
    """Each word's diarized speaker; all None when diarization was skipped."""
    if not turns:
        return [None] * len(words)
    return [best_speaker(word.start, word.end, turns) for word in words]


def _should_close(
    current: list[Word], words: list[Word], index: int, marks: list[str | None]
) -> bool:
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
        # A diarized speaker change is a hard boundary: one sentence never
        # carries both sides of an exchange.
        if marks[index] is not None and marks[index + 1] is not None:
            if marks[index] != marks[index + 1]:
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
