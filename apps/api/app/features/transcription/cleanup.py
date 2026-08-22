import logging

from app import constants
from app.features.analysis.citations import content_overlap
from app.shared.models import Sentence, Word

log = logging.getLogger(__name__)


def filter_no_speech_words(words: list[Word]) -> list[Word]:

    kept: list[Word] = []
    dropped = 0
    for word in words:
        if word.no_speech_prob is not None and word.no_speech_prob > constants.NO_SPEECH_PROB_MAX:
            dropped += 1
            continue
        kept.append(word)
    if dropped:
        log.info("Dropped %d word(s) with no_speech_prob above threshold", dropped)
    return kept


def collapse_repeated_sentences(sentences: list[Sentence]) -> list[Sentence]:

    kept: list[Sentence] = []
    previous: frozenset[str] | None = None
    collapsed = 0
    for sentence in sentences:
        signature = content_overlap(sentence.text)

        if previous is not None and signature and signature == previous:
            collapsed += 1
            continue
        previous = signature
        kept.append(sentence)
    if collapsed:
        log.info("Collapsed %d repeated sentence(s)", collapsed)
    return kept
