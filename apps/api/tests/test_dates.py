from datetime import date

import pytest
from hijridate import Gregorian, Hijri

from app.features.analysis import dates
from app.features.analysis.dates import normalize

ANCHOR = date(2026, 8, 18)


def _hijri(g: date) -> str:
    return Gregorian(g.year, g.month, g.day).to_hijri().isoformat()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("غدًا", date(2026, 8, 19)),
        ("غدا", date(2026, 8, 19)),
        ("بعد غد", date(2026, 8, 20)),
        ("بعد 3 أيام", date(2026, 8, 21)),
        ("بعد يومين", date(2026, 8, 20)),
        ("بعد أسبوع", date(2026, 8, 25)),
        ("بعد أسبوعين", date(2026, 9, 1)),
        ("بعد 3 أسابيع", date(2026, 9, 8)),
        ("بعد شهر", date(2026, 9, 18)),
        ("بعد شهرين", date(2026, 10, 18)),
        ("بعد 3 أشهر", date(2026, 11, 18)),
        ("الأسبوع القادم", date(2026, 8, 25)),
        ("نهاية الأسبوع", date(2026, 8, 21)),
        ("نهاية أسبوع العمل", date(2026, 8, 20)),
        ("نهاية الشهر", date(2026, 8, 31)),
        ("نهاية الشهر القادم", date(2026, 9, 30)),
        ("نهاية الشهر المقبل", date(2026, 9, 30)),
        ("الخميس القادم", date(2026, 8, 27)),
        ("الجمعة القادم", date(2026, 8, 28)),
        ("يوم الأحد القادم", date(2026, 8, 30)),
    ],
)
def test_relative_phrases(raw: str, expected: date):
    assert normalize(raw, ANCHOR) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("8/12/2026", date(2026, 12, 8)),
        ("15/8/2026", date(2026, 8, 15)),
        ("2026-12-25", date(2026, 12, 25)),
        ("31/12/2026", date(2026, 12, 31)),
    ],
)
def test_explicit_gregorian(raw: str, expected: date):
    assert normalize(raw, ANCHOR) == expected


@pytest.mark.parametrize(
    ("raw", "hijri_iso"),
    [
        ("15 محرم 1448", "1448-01-15"),
        ("1 رمضان 1448", "1448-09-01"),
        ("10 ذو الحجة 1448", "1448-12-10"),
    ],
)
def test_explicit_hijri_with_year(raw: str, hijri_iso: str):
    expected = Hijri(*map(int, hijri_iso.split("-"))).to_gregorian()
    assert normalize(raw, ANCHOR) == expected


def test_hijri_to_gregorian_and_back():

    greg = Hijri(1448, 9, 1).to_gregorian()
    assert _hijri(greg) == "1448-09-01"
    assert normalize("1 رمضان 1448", ANCHOR) == greg


def test_gregorian_model_helper_round_trip():
    from app.shared.models import gregorian_hijri

    assert gregorian_hijri("2026-08-18") == "1448-03-05"
    assert gregorian_hijri("ليس تاريخًا") is None


@pytest.mark.parametrize(
    "raw",
    [
        "15 محرم",
        "ربيع الأول",
        "بعد 2 أيام",
        "بعد 400 يوم",
        "متى ما اتفقنا",
        "قريبًا",
        "الشهر القادم",
        "عيد الفطر",
        "الأسبوع اللي بعده",
        "",
        None,
    ],
)
def test_ambiguous_or_out_of_scope_returns_null(raw):
    assert normalize(raw, ANCHOR) is None


def test_gregorian_from_hijri_iso():
    assert dates.gregorian_from_hijri("1448-09-01") == Hijri(1448, 9, 1).to_gregorian().isoformat()
    assert dates.gregorian_from_hijri("لا شيء") is None
    assert dates.gregorian_from_hijri(None) is None


def test_month_end_leap_year():
    anchor = date(2024, 2, 5)
    assert normalize("نهاية الشهر", anchor) == date(2024, 2, 29)


def test_calendar_month_clamps_short_months():

    assert normalize("بعد شهر", date(2026, 1, 31)) == date(2026, 2, 28)
    assert normalize("بعد شهرين", date(2026, 1, 31)) == date(2026, 3, 31)
