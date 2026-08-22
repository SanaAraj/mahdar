"""Cleanup guards against whisper silence hallucinations: no_speech filter and collapse."""

from app import constants
from app.features.transcription.cleanup import collapse_repeated_sentences, filter_no_speech_words
from app.features.transcription.sentences import words_to_sentences
from app.shared.models import Sentence, Word

from .factories import make_words


def _sentence(sid: str, text: str, start: float = 0.0) -> Sentence:
    return Sentence(id=sid, start=start, end=start + 1.0, text=text)


def test_no_speech_filter_drops_flagged_keeps_unflagged():
    words = [
        Word(start=0.0, end=0.4, text="كلام", no_speech_prob=0.2),
        Word(start=0.4, end=0.8, text="صمت", no_speech_prob=0.9),
        Word(start=0.8, end=1.2, text="واضح"),
    ]
    assert [w.text for w in filter_no_speech_words(words)] == ["كلام", "واضح"]


def test_no_speech_filter_boundary_is_strict():
    at_max = Word(start=0.0, end=0.4, text="عند", no_speech_prob=constants.NO_SPEECH_PROB_MAX)
    above = Word(start=0.4, end=0.8, text="فوق", no_speech_prob=constants.NO_SPEECH_PROB_MAX + 0.01)
    assert [w.text for w in filter_no_speech_words([at_max, above])] == ["عند"]


def test_no_speech_filter_keeps_all_when_field_absent():
    words = make_words(["اجتماع", "الفريق", "اليوم"])
    assert filter_no_speech_words(words) == words


def test_no_speech_filter_logs_dropped_count(caplog):
    with caplog.at_level("INFO"):
        filter_no_speech_words([Word(start=0.0, end=0.4, text="ضجيج", no_speech_prob=0.95)])
    assert any("Dropped 1" in r.getMessage() for r in caplog.records)


def test_collapse_keeps_first_of_consecutive_identical(caplog):
    sents = [_sentence("s1", "مرحبا بالجميع"), _sentence("s2", "مرحبا بالجميع", start=1.0)]
    with caplog.at_level("INFO"):
        kept = collapse_repeated_sentences(sents)
    assert [s.id for s in kept] == ["s1"]
    assert any("Collapsed 1" in r.getMessage() for r in caplog.records)


def test_collapse_spares_legitimate_repeat_separated_by_others():
    sents = [
        _sentence("s1", "نبدأ الاجتماع"),
        _sentence("s2", "نناقش الميزانية", start=1.0),
        _sentence("s3", "نبدأ الاجتماع", start=2.0),
    ]
    assert [s.id for s in collapse_repeated_sentences(sents)] == ["s1", "s2", "s3"]


def test_collapse_uses_arabic_normalization():
    # Alef-hamza and plain alef normalize to one form, so these two collapse.
    sents = [_sentence("s1", "إجتماع الفريق"), _sentence("s2", "اجتماع الفريق", start=1.0)]
    assert [s.id for s in collapse_repeated_sentences(sents)] == ["s1"]


def test_collapse_spares_distinct_short_token_sentences():
    # Tokens under the min length yield an empty signature; distinct texts still survive.
    sents = [_sentence("s1", "و في"), _sentence("s2", "ثم مع", start=1.0)]
    assert [s.id for s in collapse_repeated_sentences(sents)] == ["s1", "s2"]


def test_collapse_after_real_assembly_leaves_one_survivor(caplog):
    words = make_words(
        ["مرحبا", "بالجميع", "مرحبا", "بالجميع"], step=0.3, gaps=[0.05, 0.85, 0.05, 0.05]
    )
    sentences = words_to_sentences(words)
    assert len(sentences) == 2
    with caplog.at_level("INFO"):
        kept = collapse_repeated_sentences(sentences)
    assert len(kept) == 1
    assert kept[0].text == "مرحبا بالجميع"
    assert any("Collapsed 1" in r.getMessage() for r in caplog.records)
