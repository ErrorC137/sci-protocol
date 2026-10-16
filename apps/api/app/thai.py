"""Thai-language helpers shared by the corpus crawler and the form pipeline.

Thai funder pages and forms use Thai digits (๐-๙), Buddhist-era years (B.E. = C.E. + 543),
full or abbreviated Thai month names, and amounts like "1.5 ล้านบาท". Parsing them correctly is the
difference between a usable corpus and silently wrong deadlines.
"""

from __future__ import annotations

import re
from datetime import date

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

THAI_MONTHS: dict[str, int] = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
}
EN_MONTHS: dict[str, int] = {
    m: i for i, names in enumerate(
        [("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"), ("may",),
         ("june", "jun"), ("july", "jul"), ("august", "aug"), ("september", "sep", "sept"),
         ("october", "oct"), ("november", "nov"), ("december", "dec")], start=1)
    for m in names
}

_TH_MONTH_RE = "|".join(sorted((re.escape(k) for k in THAI_MONTHS), key=len, reverse=True))
_EN_MONTH_RE = "|".join(sorted(EN_MONTHS, key=len, reverse=True))

# 31 มีนาคม 2569 | 31 มี.ค. 69 | วันที่ 5 ธันวาคม พ.ศ. 2568 | 31 มีนาคม ค.ศ. 2026
_TH_DATE = re.compile(rf"(\d{{1,2}})\s*({_TH_MONTH_RE})\s*(?:(พ\.ศ\.|ค\.ศ\.)\s*)?(\d{{2,4}})")
# 31 March 2026 | March 31, 2026 | 31 Mar 2026 | 31 March 2569 (B.E. year in English text)
_EN_DATE_DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_EN_MONTH_RE})\.?,?\s+(\d{{4}})\b", re.I)
_EN_DATE_MDY = re.compile(rf"\b({_EN_MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I)
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
# 31/03/2569 | 31/3/69 | 31.03.2026 | 31-03-2026 (day first, as written in Thailand; month-first only if day-first is invalid)
_NUM_DATE = re.compile(r"(?<![\d/.\-])(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4}|\d{2})(?![\d/.\-])")


def normalize(text: str) -> str:
    """Thai digits -> Arabic, collapse whitespace (Thai text often has stray NBSP / zero-width spaces)."""
    text = text.translate(THAI_DIGITS).replace("​", "").replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", text)


def be_to_ce(year: int) -> int:
    """Buddhist-era year to Common Era. Two-digit years are B.E. short forms (69 -> 2569 -> 2026)."""
    if year < 100:
        year += 2500
    return year - 543 if year > 2400 else year


def _year(y: int, era: str | None = None) -> int:
    """Any year as written -> C.E.: '2569' and '69' are B.E.; '2026' stays; 'ค.ศ.' forces C.E."""
    if era == "ค.ศ.":
        return y + 2000 if y < 100 else y
    if y < 100:  # short years: B.E. short forms run 60-79 these decades, C.E. short forms 17-36
        return be_to_ce(y) if y >= 50 else 2000 + y
    return be_to_ce(y)


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def find_dates(text: str) -> list[tuple[date, str]]:
    """All dates in the text with the exact matched substring (the evidence quote), in text order."""
    t = normalize(text)
    out: list[tuple[int, date, str]] = []
    for m in _TH_DATE.finditer(t):
        d = _safe_date(_year(int(m.group(4)), m.group(3)), THAI_MONTHS[m.group(2)], int(m.group(1)))
        if d:
            out.append((m.start(), d, m.group(0)))
    for m in _EN_DATE_DMY.finditer(t):
        d = _safe_date(_year(int(m.group(3))), EN_MONTHS[m.group(2).lower()], int(m.group(1)))
        if d:
            out.append((m.start(), d, m.group(0)))
    for m in _EN_DATE_MDY.finditer(t):
        d = _safe_date(_year(int(m.group(3))), EN_MONTHS[m.group(1).lower()], int(m.group(2)))
        if d:
            out.append((m.start(), d, m.group(0)))
    for m in _ISO_DATE.finditer(t):
        d = _safe_date(_year(int(m.group(1))), int(m.group(2)), int(m.group(3)))
        if d:
            out.append((m.start(), d, m.group(0)))
    for m in _NUM_DATE.finditer(t):
        a, b, y = int(m.group(1)), int(m.group(2)), _year(int(m.group(3)))
        d = _safe_date(y, b, a) or _safe_date(y, a, b)
        if d:
            out.append((m.start(), d, m.group(0)))
    out.sort(key=lambda x: x[0])
    return [(d, q) for _, d, q in out]


# Closing cues name the application deadline; generic cues ('ถึง', 'until', 'ภายในวันที่') also introduce project
# periods and result dates, so they only count when no closing cue exists.
_STRONG_CUES = re.compile(
    # (?<!เ): "เปิดรับ" (applications OPEN) contains "ปิดรับ" (applications CLOSE) as a substring.
    r"((?<!เ)ปิดรับ|หมดเขต|สิ้นสุดการรับ|รับสมัครถึง|(?:ส่ง|ยื่น)(?:ข้อเสนอ|ใบสมัคร|เอกสาร).{0,20}?ภายใน|"
    r"deadline|closing date|closes?\b|due date|submit(?:ted)? by|applications? (?:close|are due|due))",
    re.I,
)
_WEAK_CUES = re.compile(r"(ภายในวันที่|(?:จน)?ถึง(?:วันที่)?|\buntil\b)", re.I)
# A cue preceded or followed by these is about results, interviews or the project period, not the deadline.
_NOT_DEADLINE = re.compile(
    r"ประกาศผล|ผลการพิจารณา|แจ้งผล|สัมภาษณ์|ทำสัญญา|ระยะเวลา(?:ดำเนิน)?(?:การ|งาน)?(?:โครงการ)?|เริ่ม(?:ดำเนิน)?โครงการ|"
    r"\bresults?\b|\bannounce|\bnotif|\binterview|project (?:period|duration|start|end)|\bstart date|kick-?off|\bcontract",
    re.I,
)


def _cue_dates(t: str, cues: re.Pattern) -> list[tuple[date, str]]:
    out = []
    for cue in cues.finditer(t):
        window = t[cue.start(): cue.end() + 120]
        found = find_dates(window)
        if not found:
            continue
        d, quote = found[0]  # the date nearest after the cue
        end = window.index(quote) + len(quote)
        context = t[max(0, cue.start() - 30): cue.start()] + window[:end]
        if _NOT_DEADLINE.search(context):
            continue
        out.append((d, window[:end].strip()))
    return out


def find_deadline(text: str) -> tuple[date, str] | None:
    """The application deadline: the date nearest after a closing cue ('ปิดรับ', 'หมดเขต', 'deadline'...).
    Several closing cues -> the latest (extensions). Only without any closing cue is a generic cue used."""
    t = normalize(text)
    strong = _cue_dates(t, _STRONG_CUES)
    if strong:
        return max(strong, key=lambda x: x[0])
    weak = _cue_dates(t, _WEAK_CUES)
    return weak[0] if weak else None


_MULT_WORDS = {"million": 1e6, "mn": 1e6, "m": 1e6, "bn": 1e9, "billion": 1e9, "k": 1e3, "thousand": 1e3,
               "ล้าน": 1e6, "แสน": 1e5, "หมื่น": 1e4}
_PREFIX = r"US\$|S\$|C\$|CA\$|A\$|AU\$|HK\$|NT\$|NZ\$|(?<![A-Za-z])RM(?![A-Za-z])|€|£|(?<![A-Za-z])\$|฿|\b(?:USD|EUR|SGD|MYR|THB|GBP|AUD|CAD|JPY)\b"
_SUFFIX = r"ล้าน\s*บาท|แสน\s*บาท|หมื่น\s*บาท|บาท|ล้าน|แสน|หมื่น|\b(?:THB|baht|USD|EUR|SGD|MYR|GBP|AUD|CAD|JPY)\b"
_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_AMOUNT = re.compile(
    rf"(?:(?P<pre>{_PREFIX})\s?(?P<num1>{_NUM})(?:\s?(?P<mult>million|billion|thousand|bn|mn|ล้าน|แสน|หมื่น|[kKmM])(?![A-Za-z]))?)"
    rf"|(?:(?P<num2>{_NUM})\s*(?P<unit>{_SUFFIX}))",
    re.I,
)
_CUR = {"บาท": "THB", "thb": "THB", "baht": "THB", "฿": "THB", "usd": "USD", "us$": "USD", "$": "USD",
        "eur": "EUR", "€": "EUR", "sgd": "SGD", "s$": "SGD", "myr": "MYR", "rm": "MYR", "gbp": "GBP", "£": "GBP",
        "c$": "CAD", "ca$": "CAD", "cad": "CAD", "a$": "AUD", "au$": "AUD", "aud": "AUD", "hk$": "HKD",
        "nt$": "TWD", "nz$": "NZD", "jpy": "JPY"}


def find_amounts(text: str) -> list[tuple[float, str, str]]:
    """(amount, currency, evidence quote) for every money amount, in text order: ล้าน/แสน/หมื่น and k/M/bn
    multipliers, prefix currencies (US$, S$, C$, A$, HK$, RM, €, £, $, ฿) and suffix units (บาท, THB, USD...)."""
    return [(a, c, q) for _, a, c, q in _amounts(normalize(text))]


def _amounts(t: str) -> list[tuple[int, float, str, str]]:
    out = []
    for m in _AMOUNT.finditer(t):
        if m.group("pre"):
            num = float(m.group("num1").replace(",", ""))
            mult = _MULT_WORDS.get((m.group("mult") or "").lower(), 1)
            cur = _CUR.get(m.group("pre").lower(), m.group("pre").upper())
        else:
            unit = re.sub(r"\s+", "", m.group("unit")).lower()
            num = float(m.group("num2").replace(",", ""))
            word = next((w for w in ("ล้าน", "แสน", "หมื่น") if unit.startswith(w)), None)
            mult = _MULT_WORDS[word] if word else 1
            cur = "THB" if word or unit == "บาท" else _CUR.get(unit, unit.upper())
        out.append((m.start(), num * mult, cur, m.group(0)))
    return out


_PER_PROJECT = re.compile(r"โครงการละ|ต่อโครงการ|ต่อทีม|ทีมละ|per (?:project|award|grant|team|applicant)|each (?:project|award|grant)", re.I)
_MAX_CUES = re.compile(r"(ไม่เกิน|สูงสุด|วงเงิน|up to|maximum|max\.?|not exceeding)\s*", re.I)
_TOTAL = re.compile(r"ทั้งสิ้น|งบประมาณรวม|รวมทั้งหมด|total (?:budget|funding|pool)|programme budget|program budget|in total|funding pool", re.I)


def find_max_amount(text: str) -> tuple[float, str, str] | None:
    """The per-project maximum: an amount after a cap cue ('ไม่เกิน', 'up to', 'โครงการละ', 'per project'),
    preferring explicit per-project wording and skipping programme totals ('ทั้งสิ้น', 'total budget')."""
    t = normalize(text)
    best: tuple[int, float, str, str] | None = None
    for pos, amt, cur, quote in _amounts(t):
        before = t[max(0, pos - 40): pos]
        after = t[pos + len(quote): pos + len(quote) + 20]
        if _TOTAL.search(before):
            continue
        cues = list(_MAX_CUES.finditer(before)) + list(_PER_PROJECT.finditer(before))
        per_project = bool(_PER_PROJECT.search(before) or _PER_PROJECT.match(after.strip()))
        if not cues and not per_project:
            continue
        start = pos - len(before) + min(c.start() for c in cues) if cues else pos
        end = pos + len(quote)
        if per_project and _PER_PROJECT.match(after.strip()):
            end = pos + len(quote) + after.index(after.strip()) + _PER_PROJECT.match(after.strip()).end()
        rank = 0 if per_project else 1
        cand = (rank, amt, cur, t[start:end].strip())
        if best is None or rank < best[0]:
            best = cand
    return (best[1], best[2], best[3]) if best else None


def is_thai(text: str) -> bool:
    thai = sum(1 for ch in text if "฀" <= ch <= "๿")
    return thai > max(10, len(text) * 0.15)
