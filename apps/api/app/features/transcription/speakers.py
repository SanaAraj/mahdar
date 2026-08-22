from app import strings
from app.shared.models import Sentence, Speaker, Turn


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def assign_speakers(sentences: list[Sentence], turns: list[Turn]) -> list[Sentence]:

    for sentence in sentences:
        sentence.speaker = best_speaker(sentence.start, sentence.end, turns)
    return sentences


def best_speaker(start: float, end: float, turns: list[Turn]) -> str | None:

    best: str | None = None
    best_overlap = 0.0
    for turn in turns:
        value = _overlap(start, end, turn.start, turn.end)
        if value > best_overlap:
            best_overlap = value
            best = turn.speaker

    return best


def build_speakers(turns: list[Turn], labels: dict[str, str]) -> list[Speaker]:

    order: list[str] = []
    first_start: dict[str, float] = {}
    for turn in turns:
        if turn.speaker not in first_start:
            order.append(turn.speaker)
            first_start[turn.speaker] = turn.start
    return [
        Speaker(
            id=speaker_id,
            label=labels.get(speaker_id) or strings.default_speaker_label(index),
            first_start=round(first_start[speaker_id], 3),
        )
        for index, speaker_id in enumerate(order)
    ]
