from app.features.analysis.citations import content_overlap, validate
from app.shared.models import (
    Analysis,
    Decision,
    Directive,
    DueDate,
    Sentence,
    TaskItem,
    Topic,
)

SENTENCES = [
    Sentence(id="s1", start=0.0, end=2.0, text="نراجع خطة العمل اليوم."),
    Sentence(id="s2", start=2.0, end=4.0, text="سأرفع التقرير غدًا."),
    Sentence(id="s3", start=4.0, end=6.0, text="يعتمد المجلس الميزانية السنوية."),
    Sentence(id="s4", start=6.0, end=8.0, text="نعتمد مؤشر KPI الجديد."),
]


def _holding(items: dict[str, list]) -> Analysis:
    return Analysis(title="اجتماع", attendees=["أ"], **items)


def test_grounded_item_passes():
    analysis = _holding({"decisions": [Decision(text="رفع التقرير", segment_ids=["s2"])]})
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 0
    assert [d.text for d in cleaned.decisions] == ["رفع التقرير"]


def test_fabricated_item_with_valid_ids_drops():
    analysis = _holding(
        {
            "decisions": [
                Decision(text="توظيف مدير تسويق جديد", segment_ids=["s1", "s2"]),
            ]
        }
    )
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 1
    assert cleaned.decisions == []


def test_single_generic_shared_word_does_not_ground_a_long_item():
    analysis = _holding(
        {
            "decisions": [
                Decision(text="اعتماد خطة التوظيف الجديدة", segment_ids=["s3"]),
            ]
        }
    )
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 1
    assert cleaned.decisions == []


def test_latin_term_overlap_counts():
    analysis = _holding(
        {
            "decisions": [
                Decision(text="اعتماد مؤشر KPI الجديد", segment_ids=["s4"]),
                Decision(text="شراء تجهيزات المختبر", segment_ids=["s4"]),
            ]
        }
    )
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 1
    assert [d.text for d in cleaned.decisions] == ["اعتماد مؤشر KPI الجديد"]


def test_diacritic_variant_matches():
    analysis = _holding(
        {
            "topics": [
                Topic(title="الخطة", summary="مراجعة خطّةِ الفريق", segment_ids=["s1"]),
            ]
        }
    )
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 0
    assert [t.title for t in cleaned.topics] == ["الخطة"]


def test_alef_and_ta_marbuta_variants_match():
    analysis = _holding({"decisions": [Decision(text="اعتماد الميزانيه", segment_ids=["s3"])]})
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 0
    assert [d.text for d in cleaned.decisions] == ["اعتماد الميزانيه"]


def test_short_tokens_ignored_below_min_chars():
    analysis = _holding({"decisions": [Decision(text="في أو عن", segment_ids=["s1"])]})
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 1
    assert cleaned.decisions == []


def test_task_description_carries_the_overlap():
    analysis = _holding(
        {
            "tasks": [
                TaskItem(description="مراجعة خطة مكتوبة", segment_ids=["s1"]),
                TaskItem(description="شراء أجهزة حديثة", segment_ids=["s1"]),
            ]
        }
    )
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 1
    assert [t.description for t in cleaned.tasks] == ["مراجعة خطة مكتوبة"]


def test_directive_requires_overlap():
    analysis = _holding({"directives": [Directive(text="متابعة خطة العمل", segment_ids=["s1"])]})
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 0
    assert [d.text for d in cleaned.directives] == ["متابعة خطة العمل"]


def test_topic_grounded_via_title_with_paraphrased_summary_survives():

    analysis = _holding(
        {
            "topics": [
                Topic(
                    title="الميزانية السنوية",
                    summary="قرار مجلسي بالإجماع",
                    segment_ids=["s3"],
                )
            ]
        }
    )
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 0
    assert [t.title for t in cleaned.topics] == ["الميزانية السنوية"]


def test_topic_grounded_via_title_with_empty_summary_survives():

    analysis = _holding(
        {"topics": [Topic(title="الميزانية السنوية", summary="", segment_ids=["s3"])]}
    )
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 0
    assert [t.title for t in cleaned.topics] == ["الميزانية السنوية"]


def test_topic_with_neither_title_nor_summary_overlap_drops():

    analysis = _holding(
        {
            "topics": [
                Topic(
                    title="خطة تسويق جديدة",
                    summary="إطلاق حملة إعلانية",
                    segment_ids=["s3"],
                )
            ]
        }
    )
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 1
    assert cleaned.topics == []


def test_partial_ids_keep_overlap_check_on_remaining():
    analysis = _holding(
        {
            "decisions": [
                Decision(text="رفع التقرير", segment_ids=["s99", "s2"]),
                Decision(text="توظيف مستشار", segment_ids=["s99", "s2"]),
            ]
        }
    )
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 1

    assert cleaned.decisions[0].segment_ids == ["s2"]


def test_empty_citations_still_drop_without_overlap_check():
    analysis = _holding({"directives": [Directive(text="خطة العمل", segment_ids=[])]})
    cleaned, dropped = validate(analysis, SENTENCES)
    assert dropped == 1
    assert cleaned.directives == []


def test_content_overlap_normalization():
    tokens = content_overlap("نراجعُ خطّة العمل، اليوم.")
    assert {"نراجع", "خطه", "العمل", "اليوم"} <= tokens

    assert content_overlap("نراجع خطة العمل اليوم") == tokens

    assert "KPI" in content_overlap("اعتماد KPI المالية")


def test_hallucinated_model_date_with_null_raw_is_cleared():

    from datetime import date

    from app.features.analysis.service import apply_meeting_task_dates

    task = TaskItem(
        description="مهمة",
        due=DueDate(raw=None, gregorian="2026-03-01"),
        segment_ids=["s1"],
    )
    analysis = Analysis(title="اجتماع", tasks=[task])
    apply_meeting_task_dates(analysis, date(2026, 8, 18))
    assert task.due.gregorian is None and task.due.hijri is None
