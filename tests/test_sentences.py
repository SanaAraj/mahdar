from backend.app import constants
from backend.app.processing.sentences import words_to_sentences

from .factories import make_words

SENTENCE_MAX_WORDS = constants.SENTENCE_MAX_WORDS
SENTENCE_MAX_DURATION_S = constants.SENTENCE_MAX_DURATION_S
SENTENCE_PAUSE_GAP_S = constants.SENTENCE_PAUSE_GAP_S


def ids(sentences):
    return [s.id for s in sentences]


def test_empty_input_returns_no_sentences():
    assert words_to_sentences([]) == []


def test_single_word_becomes_one_sentence():
    result = words_to_sentences(make_words(["مرحبا"]))
    assert len(result) == 1
    assert result[0].id == "s1"
    assert result[0].text == "مرحبا"


def test_punctuation_closes_sentence():
    tokens = ["اجتمعنا", "اليوم.", "وناقشنا", "الخطة!"]
    result = words_to_sentences(make_words(tokens))
    assert len(result) == 2
    assert result[0].text == "اجتمعنا اليوم."
    assert result[1].text == "وناقشنا الخطة!"


def test_pause_closes_sentence():
    words = make_words(["الجملة", "الأولى", "", "الثانية"], gaps=[0.1, 0.1, 0.8, 0.1])
    result = words_to_sentences(words)
    assert len(result) == 2


def test_hard_word_limit():
    result = words_to_sentences(make_words(["كلمة"] * SENTENCE_MAX_WORDS + ["زائدة"]))
    assert len(result) == 2
    assert len(result[0].text.split()) == SENTENCE_MAX_WORDS


def test_hard_duration_limit():
    words = make_words(["كلمة"] * 40, step=0.61)
    result = words_to_sentences(words)
    for sentence in result:
        assert sentence.end - sentence.start <= SENTENCE_MAX_DURATION_S + 0.61
    assert len(result) > 1


def test_mixed_closers():
    tokens = ["كيف؟", "بلى؛", "ربما.", "حسنا!"]
    result = words_to_sentences(make_words(tokens))
    assert len(result) == 4


def test_colon_does_not_close():
    tokens = ["قال:", "أهلا", "بك"]
    result = words_to_sentences(make_words(tokens))
    assert len(result) == 1


def test_honorific_does_not_close():
    tokens = ["قال", "د.", "خالد", "مرحبا"]
    result = words_to_sentences(make_words(tokens))
    assert len(result) == 1
    assert result[0].text == "قال د. خالد مرحبا"


def test_empty_token_does_not_force_close():
    tokens = ["أهلا", "", "بك"]
    result = words_to_sentences(make_words(tokens))
    assert len(result) == 1


def test_gap_below_threshold_stays_in_sentence():
    gap = SENTENCE_PAUSE_GAP_S - 0.2
    words = make_words(["أولى", "ثانية"], gaps=[0.1, gap])
    result = words_to_sentences(words)
    assert len(result) == 1


def test_ids_are_sequential():
    tokens = ["واحد.", "اثنان.", "ثلاثة.", "أربعة."]
    result = words_to_sentences(make_words(tokens))
    assert ids(result) == ["s1", "s2", "s3", "s4"]


def test_timestamps_cover_first_and_last_word():
    words = make_words(["بدأنا.", "ثم", "انتهينا"], start=5.0)
    result = words_to_sentences(words)
    assert result[0].start == 5.0
    assert result[-1].end == words[-1].end


def test_text_is_trimmed():
    words = make_words(["  مرحبا  ", "بالعالم."])
    result = words_to_sentences(words)
    assert result[0].text.split()[0] == "مرحبا"


def test_property_sorted_non_overlapping_all_words_consumed():
    """Whole-property: sentences are ordered, non-overlapping, and consume every word."""
    tokens = [
        "افتتحنا",
        "الاجتماع.",
        "ثم",
        "ناقشنا",
        "الخطة؟",
        "نعم،",
        "وافقنا؛",
        "وسجلنا",
        "المهام",
        "الآتية.",
        "شكرا",
        "للجميع",
    ]
    words = make_words(tokens)
    result = words_to_sentences(words)

    # 1) Every word appears exactly once, in order.
    consumed = [tok for s in result for tok in s.text.split()]
    assert consumed == tokens

    # 2) Sentences are time-ordered and do not overlap.
    for a, b in zip(result, result[1:], strict=False):
        assert a.end <= b.start

    # 3) Each sentence carries a unique, sequential id.
    assert [s.id for s in result] == [f"s{i + 1}" for i in range(len(result))]

    # 4) The first sentence start and last sentence end bracket every word.
    assert result[0].start == words[0].start
    assert result[-1].end == words[-1].end


def test_long_run_every_word_consumed_with_hard_splits():
    """A longer run with no punctuation: the hard split still consumes every word."""
    tokens = [f"و{i}" for i in range(70)]
    words = make_words(tokens)
    result = words_to_sentences(words)
    consumed = [tok for s in result for tok in s.text.split()]
    assert consumed == tokens
    assert all(s.end - s.start <= SENTENCE_MAX_DURATION_S + 0.61 for s in result)
