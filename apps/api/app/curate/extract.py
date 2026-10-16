"""Page text -> candidate corpus entries, each value backed by a quote that is checked against the page.

Two extractors share one verifier:
  * Claude (when ANTHROPIC_API_KEY is set): every opportunity on the page, with per-field quotes.
  * Heuristics (always available): one candidate per page from the Thai/English deadline and
    amount parsers in app/thai.py. Lower recall, zero cost.

The verifier is the point. A quote must occur in the fetched text (whitespace-insensitive, Thai digits
normalised); dates and amounts must also be *in* their quote. Anything that fails is dropped and listed
under `dropped` in the review queue, so a hallucinated deadline cannot reach the corpus silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .. import llm, thai
from ..quotes import norm, quote_in
from ..models import taxonomy
from .textify import Doc

# --- relevance pre-filter: spend LLM calls only on pages that look like calls ----------------------
_STRONG = re.compile(
    r"call for (?:proposals|applications|projects)|funding opportunit|grant (?:programme|program|scheme|call)|"
    r"applications? (?:are )?(?:now )?open|apply (?:now|by|before)|accelerator program|"
    r"ทุนวิจัย|ขอรับทุน|ขอรับการสนับสนุน|ประกาศรับ(?:ข้อเสนอ|สมัคร)|เปิดรับ(?:ข้อเสนอ|สมัคร)|แหล่งทุน|ให้ทุน|ทุนสนับสนุน",
    re.I,
)
_WEAK = re.compile(r"\bgrants?\b|\bfunding\b|\beligib|\bTRL\b|ทุน|สนับสนุน|คุณสมบัติ|ผู้มีสิทธิ์", re.I)
CANDIDATE_MIN = 3.0


def relevance(doc: Doc) -> tuple[float, list[str]]:
    t = doc.text[:60_000]
    strong = {m.group(0).lower() for m in _STRONG.finditer(t)}
    weak = len(_WEAK.findall(t))
    reasons, score = [], 0.0
    if strong:
        score += 2 + min(len(strong), 3)
        reasons.append("call language: " + ", ".join(sorted(strong)[:3]))
    if weak:
        score += min(weak, 10) * 0.2
    if thai.find_deadline(t):
        score += 2
        reasons.append("deadline cue")
    if thai.find_max_amount(t) or thai.find_amounts(t[:20_000]):
        score += 1
        reasons.append("amount")
    return score, reasons


# --- verification ----------------------------------------------------------------------------------
def _amount_in(value: float, currency: str | None, quote: str) -> str | None:
    """The currency of a money amount in the quote equal to `value` (and to `currency`, if given), else None.
    A bare number is not enough: the quote must carry the amount with its currency or unit."""
    for amt, cur, _ in thai.find_amounts(quote):
        if abs(amt - value) <= max(1.0, value * 0.005) and (not currency or cur.upper() == currency.upper()):
            return cur
    return None


# Words that must appear in a quote for a country / region / applicant-type value to count as stated.
_REGION_WORDS = {
    "ASEAN": r"ASEAN|อาเซียน|Southeast Asia|South-East Asia|เอเชียตะวันออกเฉียงใต้",
    "EU27": r"\bEU\b|European Union|EU member|สหภาพยุโรป",
    "HE_ELIGIBLE": r"Horizon Europe|associated countr",
    "GLOBAL": r"global|worldwide|international|any country|all countries|open to all|ทั่วโลก|ทุกประเทศ|นานาชาติ",
}
_COUNTRY_TH = {"TH": "ไทย", "SG": "สิงคโปร์", "MY": "มาเลเซีย", "ID": "อินโดนีเซีย", "VN": "เวียดนาม", "PH": "ฟิลิปปินส์",
               "JP": "ญี่ปุ่น", "KR": "เกาหลี", "CN": "จีน", "US": "สหรัฐ", "GB": "สหราชอาณาจักร"}
_APPLICANT_WORDS = {
    "individual": r"individual|researcher|scientist|natural person|(?<!นิติ)บุคคล|นักวิจัย|อาจารย์",  # not นิติบุคคล (juristic person)
    "university": r"universit|institut|academ|มหาวิทยาลัย|สถาบัน|สถานศึกษา|หน่วยงานวิจัย",
    "startup": r"start-?up|สตาร์ทอัพ|วิสาหกิจเริ่มต้น|นิติบุคคล|company|บริษัท",
    "sme": r"\bSMEs?\b|small and medium|วิสาหกิจขนาดกลางและขนาดย่อม|เอสเอ็มอี|นิติบุคคล|company|บริษัท",
    "consortium": r"consorti|partnership|joint|ความร่วมมือ|ภาคี|เครือข่าย",
}


def _country_ok(code: str, quote: str) -> bool:
    from ..models import taxonomy

    pat = _REGION_WORDS.get(code)
    if pat is None:
        name = taxonomy.COUNTRIES.get(code, (None,))[0]
        alts = [rf"\b{re.escape(code)}\b"] + ([re.escape(name)] if name else []) + ([_COUNTRY_TH[code]] if code in _COUNTRY_TH else [])
        pat = "|".join(alts)
    return bool(re.search(pat, quote, re.I))


QUOTED = ("title", "deadline", "amount_min", "amount_max", "trl_min", "trl_max", "countries", "applicant_types",
          "requires_incorporation", "ip_assignment_required", "equity_taken", "rolling", "cycle", "application_mode")
# The quote exists on the page, but no program can check that the value follows from it: shown to the reviewer as such.
UNCHECKED = ("requires_incorporation", "ip_assignment_required", "equity_taken", "rolling", "cycle", "application_mode")
INFERRED = ("fields", "subdomains", "summary", "title_en")  # classification / paraphrase: shown as inferred


def verify(item: dict, doc: Doc) -> tuple[dict, dict[str, str], list[dict], list[str]]:
    """Returns (kept values, field -> verified quote, dropped [{field, value, reason}], unchecked fields)."""
    hay = norm(doc.text + "\n" + (doc.title or ""))
    quotes: dict[str, list[str]] = {}
    for ev in item.get("evidence") or []:
        quotes.setdefault(ev.get("field", ""), []).append(ev.get("quote", ""))
    kept, evidence, dropped, unchecked = dict(item), {}, [], []

    def on_page(f: str) -> list[str]:
        return [q for q in quotes.get(f, []) + ([item["title"]] if f == "title" and item.get("title") else []) if q and quote_in(q, hay)]

    def drop(f, v, found_quotes):
        reason = ("a quote was found on the page, but it does not contain this value" if found_quotes
                  else "no supporting quote found on the page")
        dropped.append({"field": f, "value": v, "reason": reason})
        kept[f] = [] if isinstance(v, list) else None

    for f in QUOTED:
        v = item.get(f)
        if v in (None, "", []):
            continue
        found = on_page(f)
        if f == "deadline":
            try:
                d = date.fromisoformat(str(v))
            except ValueError:
                dropped.append({"field": f, "value": v, "reason": "not an ISO date"})
                kept[f] = None
                continue
            q = next((q for q in found if d in [x for x, _ in thai.find_dates(q)]), None)
        elif f in ("amount_min", "amount_max"):
            q, cur = None, None
            for cand in found:
                cur = _amount_in(float(v), item.get("currency"), cand) or _amount_in(float(v), None, cand)
                if cur:
                    q = cand
                    break
            if q and item.get("currency") and cur != item["currency"]:
                dropped.append({"field": "currency", "value": item["currency"], "reason": f"page states {cur}; corrected"})
            if q:
                kept["currency"] = cur  # the currency comes from the page, never from a default
        elif f in ("trl_min", "trl_max"):
            q = next((q for q in found if re.search(rf"(?<!\d){v}(?!\d)", q) and re.search(r"TRL|technology readiness|ระดับความพร้อม", q, re.I)), None)
        elif f == "countries":
            ok = [c for c in v if any(_country_ok(c, q) for q in found)]
            for c in set(v) - set(ok):
                dropped.append({"field": f, "value": c, "reason": "this country/region is not named in any quote on the page"})
            kept[f] = ok
            q = next((q for q in found if any(_country_ok(c, q) for c in ok)), None) if ok else None
            if q:
                evidence[f] = q
            continue
        elif f == "applicant_types":
            ok = [a for a in v if any(re.search(_APPLICANT_WORDS.get(a, "(?!)"), q, re.I) for q in found)]
            for a in set(v) - set(ok):
                dropped.append({"field": f, "value": a, "reason": "this applicant type is not named in any quote on the page"})
            kept[f] = ok
            q = next((q for q in found if any(re.search(_APPLICANT_WORDS.get(a, "(?!)"), q, re.I) for a in ok)), None) if ok else None
            if q:
                evidence[f] = q
            continue
        else:
            q = found[0] if found else None
            if q and f in UNCHECKED:
                unchecked.append(f)
        if q:
            evidence[f] = q
        else:
            drop(f, v, found)
    if kept.get("amount_min") is None and kept.get("amount_max") is None:
        kept["currency"] = None
    link_urls = {u for u, _ in doc.links}
    if item.get("form_url") and item["form_url"] not in link_urls and item["form_url"] != doc.url:
        dropped.append({"field": "form_url", "value": item["form_url"], "reason": "not a link on the page"})
        kept["form_url"] = None
    kept.pop("evidence", None)
    return kept, evidence, dropped, unchecked


# --- extractors ------------------------------------------------------------------------------------
def heuristic(doc: Doc) -> list[dict]:
    """One candidate per page: title, deadline and maximum amount, with the matched text as quotes."""
    item: dict = {"title": doc.title, "evidence": []}
    dl = thai.find_deadline(doc.text)
    if dl:
        item["deadline"] = dl[0].isoformat()
        item["evidence"].append({"field": "deadline", "quote": dl[1]})
    amt = thai.find_max_amount(doc.text)
    if amt:
        item.update(amount_max=amt[0], currency=amt[1])
        item["evidence"].append({"field": "amount_max", "quote": amt[2]})
    return [item] if doc.title and (dl or amt) else []


SUBDOMAINS = sorted({s for f in taxonomy.FIELDS.values() for s in f["subdomains"]})
_NULLABLE = lambda t: {"type": [t, "null"]}  # noqa: E731

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "title_en": _NULLABLE("string"),
        "summary": {"type": "string"},
        "fields": {"type": "array", "items": {"type": "string", "enum": list(taxonomy.FIELDS)}},
        "subdomains": {"type": "array", "items": {"type": "string", "enum": SUBDOMAINS}},
        "trl_min": _NULLABLE("integer"),
        "trl_max": _NULLABLE("integer"),
        "countries": {"type": "array", "items": {"type": "string"}},
        "applicant_types": {"type": "array", "items": {"type": "string", "enum": list(taxonomy.APPLICANT_TYPES)}},
        "requires_incorporation": _NULLABLE("boolean"),
        "ip_assignment_required": _NULLABLE("boolean"),
        "equity_taken": _NULLABLE("boolean"),
        "amount_min": _NULLABLE("number"),
        "amount_max": _NULLABLE("number"),
        "currency": _NULLABLE("string"),
        "deadline": _NULLABLE("string"),
        "rolling": _NULLABLE("boolean"),
        "cycle": _NULLABLE("string"),
        "application_mode": {"anyOf": [{"type": "string", "enum": taxonomy.APPLICATION_MODES}, {"type": "null"}]},
        "form_url": _NULLABLE("string"),
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"field": {"type": "string", "enum": list(QUOTED)}, "quote": {"type": "string"}},
                "required": ["field", "quote"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "title_en", "summary", "fields", "subdomains", "trl_min", "trl_max", "countries",
                 "applicant_types", "requires_incorporation", "ip_assignment_required", "equity_taken", "amount_min",
                 "amount_max", "currency", "deadline", "rolling", "cycle", "application_mode", "form_url", "evidence"],
    "additionalProperties": False,
}
SCHEMA = {
    "type": "object",
    "properties": {"opportunities": {"type": "array", "items": ITEM_SCHEMA}},
    "required": ["opportunities"],
    "additionalProperties": False,
}

SYSTEM = """You extract research and innovation funding opportunities (grants, calls for proposals, accelerator or incubator intakes, prizes, fellowships for researchers) from ONE web page or document, for a curated index that researchers rely on.

Rules:
- Report only what this page states. If the page does not state a value, return null (or [] for lists). Never fill a value from general knowledge of the funder.
- `title`: copied exactly as written on the page, in the page's language. `title_en`: an English translation if the title is not English, else null.
- Every non-null value of title, deadline, amount_min, amount_max, trl_min, trl_max, countries, applicant_types, requires_incorporation, ip_assignment_required, equity_taken, rolling, cycle, application_mode needs an `evidence` item whose `quote` is copied character-for-character from the page (8-200 characters) and contains the date, number or statement itself. Quotes are checked by a program; a value whose quote is not found is deleted.
- `deadline`: the final closing date for applications as YYYY-MM-DD in the Common Era. Thai Buddhist-era years are 543 more (2569 B.E. = 2026 C.E.; "69" in "31 มี.ค. 69" means 2569). The quote stays verbatim. An opening date, event date or announcement date is NOT a deadline.
- Amounts: the per-project amount in the stated currency (ISO code, e.g. THB, USD, SGD, EUR). Expand Thai multipliers: ล้าน x1,000,000, แสน x100,000, หมื่น x10,000. A programme's total budget is not a per-project amount. The amount's quote must contain the number together with its currency or unit (e.g. "ไม่เกิน 1.5 ล้านบาท", "up to S$250,000").
- `countries`: ISO-3166 alpha-2 codes or ASEAN / EU27 / GLOBAL, only where the page states applicant-location eligibility.
- `fields`/`subdomains`: choose from the allowed lists only when the page names the topic; these are your classification and will be labelled as inferred.
- `summary`: one or two plain English sentences on who can apply and for what, using only facts on the page.
- `form_url`: only a link that appears on the page and leads to the application form or form document.
- News about past winners, events, procurement notices, job adverts and general agency news are not opportunities. A listing page may contain several calls: return each one that has its own title on this page. Return an empty list if there is none."""


def with_llm(doc: Doc, today: date, max_chars: int = 40_000) -> list[dict] | None:
    """None when the LLM is unavailable or failed (caller falls back to heuristics)."""
    user = (f"URL: {doc.url}\nPage title: {doc.title or '-'}\nToday: {today.isoformat()}\n\n"
            f"<page>\n{doc.text[:max_chars]}\n</page>")
    out = llm.structured(system=SYSTEM, user=user, schema=SCHEMA, effort="low", max_tokens=8000)
    return None if out is None else out.get("opportunities", [])


@dataclass
class Candidate:
    doc: Doc
    method: str  # llm | heuristic
    values: dict
    evidence: dict[str, str]
    dropped: list[dict] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    unchecked: list[str] = field(default_factory=list)  # quote on the page, value not machine-checkable


def extract(doc: Doc, today: date, use_llm: bool = True) -> list[Candidate]:
    items, method = None, "heuristic"
    if use_llm and llm.enabled():
        items = with_llm(doc, today)
        method = "llm" if items is not None else "heuristic"
    if items is None:
        items = heuristic(doc)
    out = []
    for item in items:
        values, evidence, dropped, unchecked = verify(item, doc)
        flags = []
        if not values.get("title"):
            if not doc.title:
                continue
            values["title"] = doc.title
            flags.append("no title given; page title used")
        if "title" not in evidence:
            # keep the model's wording (two calls on one listing page must stay two items), but say so
            flags.append("title not found verbatim on the page (model wording)")
        if values.get("deadline") and date.fromisoformat(values["deadline"]) < today:
            flags.append("deadline has passed - closed call or an older cycle")
        if not set(evidence) - {"title"}:
            flags.append("no verified facts beyond the title")
        if values.get("amount_max") is not None and not values.get("currency"):
            flags.append("amount without a stated currency")
        out.append(Candidate(doc, method, values, evidence, dropped, flags, unchecked))
    return out
