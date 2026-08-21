"""Deterministic normalization of relative and explicit Arabic dates, off-model.

The context is Saudi: the work week runs Sunday to Thursday. "End of week" is
the coming Friday and "end of work week" the coming Thursday (documented in
DECISIONS.md). Any phrase no parser here matches returns None rather than guess.

The Arabic phrase tables below are product vocabulary for an Arabic product,
not code copy; they stay Arabic by design (see DECISIONS.md).
"""

import re
from datetime import date, timedelta

from hijridate import Hijri

_WORD_NUMBER = {
    "يوم": 1,
    "يومين": 2,
    "أيام": 3,
    "أسبوع": 7,
    "أسبوعين": 14,
    "أسابيع": 21,
}

_HIJRI_MONTHS = {
    "محرم": 1,
    "صفر": 2,
    "ربيع الأول": 3,
    "ربيع الآخر": 4,
    "ربيع الثاني": 4,
    "ربيع الاخر": 4,
    "جمادى الأولى": 5,
    "جمادى الاولى": 5,
    "جمادى الآخرة": 6,
    "جمادى الاخرة": 6,
    "جمادى الثانية": 6,
    "رجب": 7,
    "شعبان": 8,
    "رمضان": 9,
    "شوال": 10,
    "ذو القعدة": 11,
    "ذي القعدة": 11,
    "ذو الحجة": 12,
    "ذي الحجة": 12,
}

_DAY_INDEX = {
    "الأحد": 6,
    "الاحد": 6,
    "أحد": 6,
    "احد": 6,
    "الاثنين": 0,
    "الإثنين": 0,
    "اثنين": 0,
    "الثلاثاء": 1,
    "ثلاثاء": 1,
    "الأربعاء": 2,
    "الاربعاء": 2,
    "أربعاء": 2,
    "اربعاء": 2,
    "الخميس": 3,
    "خميس": 3,
    "الجمعة": 4,
    "جمعة": 4,
    "السبت": 5,
    "سبت": 5,
}

_RANGES = {
    "أيام": (3, 364),
    "أسابيع": (3, 52),
    "أشهر": (3, 36),
}

_HIJRI_MONTH_RE = "محرم|صفر|شعبان|رجب|رمضان|شوال|ذو القعدة|ذي القعدة|ذو الحجة|ذي الحجة"
_HIJRI_PREFIX_RE = "ربيع|جمادى"

# Julian month lengths; February's leap-day entry is chosen per year at lookup.
_MONTH_LENGTHS = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
_FEBRUARY = 2


def normalize(raw: str | None, anchor: date) -> date | None:
    text = _clean(raw)
    if not text:
        return None
    return _absolute(text) or _relative(text, anchor)


def gregorian_from_hijri(hijri_iso: str) -> str | None:
    """Convert an ISO Hijri date (from the model) to ISO Gregorian; None when it fails."""
    match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", (hijri_iso or "").strip())
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    try:
        return Hijri(year, month, day).to_gregorian().isoformat()
    except (OverflowError, ValueError):
        return None


def _clean(raw: str | None) -> str:
    if not raw:
        return ""
    text = re.sub(r"\s+", " ", raw.strip())
    return text.replace("ـ", "")


def _absolute(text: str) -> date | None:
    match = re.fullmatch(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})", text)
    if match:
        day, month, year = (int(part) for part in match.groups())
        return _safe_date(year, month, day) or _safe_date(year, day, month)
    match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if match:
        year, month, day = (int(part) for part in match.groups())
        return _safe_date(year, month, day)
    hijri = _parse_hijri(text)
    if hijri:
        return hijri
    return None


def _parse_hijri(text: str) -> date | None:
    month_pattern = rf"(?:{_HIJRI_PREFIX_RE})\s+\S+|(?:{_HIJRI_MONTH_RE})"
    match = re.fullmatch(rf"(\d{{1,2}})\s+({month_pattern})(?:\s+(\d{{4}}))?", text)
    if not match:
        return None
    day = int(match.group(1))
    month_name = re.sub(r"\s+", " ", match.group(2).strip())
    year = int(match.group(3)) if match.group(3) else None
    month = _HIJRI_MONTHS.get(month_name)
    if month is None or not 1 <= day <= 30:
        return None
    if year is None:
        return None  # No explicit Hijri year: a real ambiguity between two cycles, so no guess.
    try:
        return Hijri(year, month, day).to_gregorian()
    except (OverflowError, ValueError):
        return None


def _relative(text: str, anchor: date) -> date | None:
    if text == "غدًا" or text == "غدا":
        return anchor + timedelta(days=1)
    if text == "بعد غد":
        return anchor + timedelta(days=2)
    if text in ("يوم الأحد القادم", "يوم الاحد القادم"):
        text = "الأحد القادم"
    day_match = re.fullmatch(r"(?:يوم\s+)?(\S+)\s+القادم", text)
    if day_match and day_match.group(1) in _DAY_INDEX:
        return _next_weekday(anchor, _DAY_INDEX[day_match.group(1)])
    after = re.fullmatch(r"بعد\s+(\d+)\s+(أيام|أسابيع|أشهر)", text)
    if after:
        return _after_units(anchor, int(after.group(1)), after.group(2))
    dual = re.fullmatch(r"بعد\s+(يومين|أسبوعين)", text)
    if dual:
        return anchor + timedelta(days=_WORD_NUMBER[dual.group(1)])
    if text == "بعد شهرين":
        return _add_months(anchor, 2)
    single = re.fullmatch(r"بعد\s+(يوم|أسبوع)", text)
    if single:
        return anchor + timedelta(days=_WORD_NUMBER[single.group(1)])
    if text == "بعد شهر":
        return _add_months(anchor, 1)
    if text == "الأسبوع القادم":
        return anchor + timedelta(days=7)
    if text == "نهاية الأسبوع":
        return _coming_weekday(anchor, 4)  # coming Friday
    if text == "نهاية أسبوع العمل":
        return _coming_weekday(anchor, 3)  # coming Thursday
    if text == "نهاية الشهر":
        return _month_end(anchor, 0)
    if text in ("نهاية الشهر القادم", "نهاية الشهر المقبل", "نهاية الشهر الجاي"):
        return _month_end(anchor, 1)
    return None


def _after_units(anchor: date, count: int, unit: str) -> date | None:
    low, high = _RANGES[unit]
    if count < low or count > high:
        return None
    if unit == "أيام":
        return anchor + timedelta(days=count)
    if unit == "أسابيع":
        return anchor + timedelta(weeks=count)
    return _add_months(anchor, count)


def _coming_weekday(anchor: date, weekday: int) -> date:
    days = ((weekday - anchor.weekday()) % 7) or 7
    return anchor + timedelta(days=days)


def _next_weekday(anchor: date, weekday: int) -> date:
    """A day marked "coming" always falls in the next week, without exception.

    One rule with no special cases: whoever meant a later day of the current
    week named it plainly, and whoever said "coming" meant the next weekly
    cycle however near or far.
    """
    return anchor + timedelta(days=(weekday - anchor.weekday()) % 7 + 7)


def _month_end(anchor: date, advance: int) -> date:
    target = _add_months(anchor, advance)
    first_next = _add_months(target.replace(day=1), 1)
    return first_next - timedelta(days=1)


def _add_months(anchor: date, months: int) -> date:
    month = anchor.month - 1 + months
    year = anchor.year + month // 12
    month = month % 12 + 1
    limit = _MONTH_LENGTHS[month - 1]
    if month == _FEBRUARY and not _is_leap(year):
        limit = 28
    return date(year, month, min(anchor.day, limit))


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None
