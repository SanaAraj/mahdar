from app.features.transcription.speakers import assign_speakers, build_speakers
from app.shared.models import Sentence, Turn


def _sentence(id: str, start: float, end: float, text: str = "نص") -> Sentence:
    return Sentence(id=id, start=start, end=end, text=text)


def test_full_overlap_assigns_speaker():
    turns = [Turn(start=0.0, end=5.0, speaker="SPEAKER_00")]
    result = assign_speakers([_sentence("s1", 1.0, 2.0)], turns)
    assert result[0].speaker == "SPEAKER_00"


def test_partial_overlap_picks_max():

    turns = [
        Turn(start=0.0, end=5.0, speaker="SPEAKER_00"),
        Turn(start=5.0, end=9.0, speaker="SPEAKER_01"),
    ]
    result = assign_speakers([_sentence("s1", 4.0, 7.0)], turns)
    assert result[0].speaker == "SPEAKER_01"


def test_tie_breaks_to_earlier_turn():

    turns = [
        Turn(start=0.0, end=1.0, speaker="SPEAKER_00"),
        Turn(start=1.0, end=2.0, speaker="SPEAKER_01"),
    ]
    result = assign_speakers([_sentence("s1", 0.0, 2.0)], turns)
    assert result[0].speaker == "SPEAKER_00"


def test_zero_overlap_yields_none():
    turns = [Turn(start=10.0, end=12.0, speaker="SPEAKER_00")]
    result = assign_speakers([_sentence("s1", 0.0, 1.0)], turns)
    assert result[0].speaker is None


def test_empty_turns_leave_speaker_null():
    result = assign_speakers([_sentence("s1", 0.0, 1.0)], [])
    assert result[0].speaker is None


def test_touching_boundaries_count_as_zero():

    turns = [Turn(start=2.0, end=4.0, speaker="SPEAKER_00")]
    result = assign_speakers([_sentence("s1", 0.0, 2.0)], turns)
    assert result[0].speaker is None


def test_build_speakers_first_appearance_order_and_labels():
    turns = [
        Turn(start=5.0, end=8.0, speaker="SPEAKER_01"),
        Turn(start=0.0, end=3.0, speaker="SPEAKER_00"),
        Turn(start=9.0, end=10.0, speaker="SPEAKER_01"),
    ]
    speakers = build_speakers(turns, {})

    assert [s.id for s in speakers] == ["SPEAKER_01", "SPEAKER_00"]

    by_id = {s.id: s for s in speakers}
    assert by_id["SPEAKER_01"].first_start == 5.0
    assert by_id["SPEAKER_00"].first_start == 0.0


def test_build_speakers_default_labels_numbered_arabic():
    turns = [
        Turn(start=0.0, end=1.0, speaker="SPEAKER_00"),
        Turn(start=2.0, end=3.0, speaker="SPEAKER_01"),
    ]
    speakers = build_speakers(turns, {})
    assert speakers[0].label == "المتحدث 1"
    assert speakers[1].label == "المتحدث 2"


def test_build_speakers_uses_persisted_labels_over_defaults():
    turns = [Turn(start=0.0, end=1.0, speaker="SPEAKER_00")]
    speakers = build_speakers(turns, {"SPEAKER_00": "أحمد"})
    assert speakers[0].label == "أحمد"
