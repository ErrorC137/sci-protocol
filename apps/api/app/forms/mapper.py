"""FieldSpec[] x ProjectProfile -> proposed values, each with a confidence state (brief §5.2).

    green  value comes directly from the researcher's own profile/contact details
    amber  inferred (LLM), converted or drafted scaffold - the researcher must verify it
    red    cannot be filled from what we know - needs the researcher

Hard rules, enforced here regardless of what the LLM returns (when unsure, red):
  * declarations, consents, signatures, identity/bank details, dates and empty labels are never filled
  * fields about someone else (supervisor, approver, referee...), track record, budget lines and table rows
    other than your own row of the team table are never filled
  * money is green only in USD, the currency the profile holds; other currencies are flagged estimates
  * narrative fields are drafts containing explicit [YOU MUST ADD: ...] placeholders, and no placeholder is
    ever cut by a length limit
  * no field is ever filled with content that isn't grounded in the profile or grant data
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable

from .. import llm
from ..ingest.base import USD_PER
from ..models import taxonomy
from ..models.schemas import Applicant, FieldSpec, FilledField, Grant, ProjectProfile

PLACEHOLDER = "[YOU MUST ADD:"
PLACEHOLDER_TH = "[ต้องเพิ่ม:"
PLACEHOLDERS = (PLACEHOLDER, PLACEHOLDER_TH)
PLACEHOLDER_SPAN = re.compile(r"\[(?:YOU MUST ADD|ต้องเพิ่ม):[^\]]*(?:\]|$)")
DECLARATION = re.compile(
    r"declar|\bcertify\b|certifications and assurances|consent|acknowledg|attest|undertak|\bhereby\b|"
    r"\b(?:i|we|i ?/ ?we)\s+(?:(?:hereby|also|have|do|fully|further)\s+)*"
    r"(?:certify|declare|confirm|agree|accept|acknowledge|understand|consent|attest|undertake|warrant|read)\b|"
    r"terms (?:and|&) conditions|terms of (?:use|service)|platform terms|privacy (?:policy|notice)|"
    r"true(?:,| and| &)? (?:correct|accurate|complete)|to the best of (?:my|our) knowledge|"
    # Thai: "I ... certify / confirm / agree / have read and understood", "certify that", "correct and complete", "true".
    # Bare รับรอง is left alone: การทดสอบและรับรองมาตรฐาน (testing & certification) is a use of funds, not a declaration.
    r"ข้าพเจ้า.{0,80}?(?:รับรอง|ยืนยัน|ตกลง|ได้อ่าน|เข้าใจ|ยินยอม|รับทราบ|ยอมรับ)|ขอรับรอง(?!มาตรฐาน)|คำรับรอง|รับรองว่า|"
    r"ยืนยันว่า|ขอยืนยัน|ยินยอม|รับทราบ|ยอมรับ(?:เงื่อนไข|ข้อตกลง)|ตกลงตาม|ได้อ่านและเข้าใจ|ถูกต้อง\s*(?:และ)?\s*ครบถ้วน|เป็นความจริง",
    re.I | re.S,
)
BANK = (r"\bbank|account\s*(?:number|no\b|name|holder|#)|\bacct\b|\biban\b|\bswift\b|\bbic\b|\brouting\b|sort code|"
        r"financial institution|ธนาคาร|บัญชี(?:ธนาคาร|เงินฝาก)|ชื่อบัญชี|หมายเลขบัญชี|เลขบัญชี|เลขที่บัญชี|สถาบันการเงิน|"
        r"พร้อมเพย์|promptpay|ออมทรัพย์|กระแสรายวัน")
NEVER_FILL = re.compile(
    BANK + r"|signature|sign here|\bsigned\b|date of sign|signator|\bstamp|\bseal\b|"
    r"passport|national id|identity card|\bid card|citizen id|tax id|tax identification|taxpayer|\b(?:ein|tin|ssn|uei|duns)\b|"
    r"social security|identification (?:number|no)|nationality|citizenship|(?:country|place|date) of birth|\bgender\b|\bsex\b|"
    r"religion|marital|ลงชื่อ|ลายมือชื่อ|ลงนาม|ผู้มีอำนาจ|ตราประทับ|ประทับตรา|บัตรประจำตัว|บัตรประชาชน|เลขประจำตัว|"
    r"หนังสือเดินทาง|13 หลัก|สัญชาติ|เชื้อชาติ|ศาสนา|สถานภาพสมรส",
    re.I,
)
DATE_LABEL = re.compile(r"\bdated?\b|\bdob\b|\bdd\s*/\s*mm|\bmm\s*/\s*dd|yyyy|fiscal year|financial year|"
                        r"วันที่|วัน\s*/?\s*เดือน\s*/?\s*ปี|พ\.\s*ศ|ค\.\s*ศ\.|วันเกิด|ปีงบประมาณ", re.I)
THIRD_PARTY = re.compile(
    r"supervisor|head of (?:the )?(?:department|school|unit|division|organi[sz]ation|institution|agency)|department head|\bdean\b|"
    r"approv(?:er|ing|ed by)|referee|recommender|endors(?:er|ed by)|witness|guarantor|"
    r"authori[sz]ed (?:representative|official|officer|person)|co-?investigator|co-?applicant|\bco-?pi\b|partner|collaborat|"
    r"mentor|advis[oe]r|emergency contact|next of kin|funding (?:agency|body)|"
    r"ผู้บังคับบัญชา|หัวหน้าหน่วยงาน|หัวหน้าภาค|หัวหน้าส่วนงาน|คณบดี|อธิการบดี|ผู้อำนวยการ|อนุมัติ|ผู้รับรอง|ผู้ให้การรับรอง|พยาน|"
    r"ผู้ค้ำประกัน|ที่ปรึกษา|ผู้ร่วมวิจัย|ผู้ร่วมโครงการ|หน่วยงานร่วม|ร่วมดำเนินการ|ร่วมทุน|ผู้ประสานงาน|ผู้ให้ทุน|หน่วยงานที่ให้ทุน",
    re.I,
)
HISTORY = re.compile(
    r"ผลงาน(?!ที่คาด|ที่จะ)|ประวัติ(?!ความเป็นมา)|ทุนที่เคยได้รับ|เคยได้รับ|วุฒิการศึกษา|ระดับการศึกษา|สำเร็จการศึกษา|"
    r"publications?\b(?!\s*(?:fees?|costs?|charges?))|track record|\b(?:previous|former)\b|"
    r"(?:prior|past|current|other) (?:grants?|funding|awards?|projects?)|curriculum vitae|\bcv\b|biograph|h-index|"
    r"\beducation\b|\bdegrees?\b(?! of)|qualification|graduat|alma mater",
    re.I,
)
TEAM = re.compile(r"คณะผู้วิจัย|ผู้วิจัย|นักวิจัย|ทีม|\bteam\b|investigators?|researchers?|members?", re.I)
OTHER = re.compile(r"อื่น\s*ๆ|^\W*others?\b|\bothers?\b\W*(?:please\s+)?specif|if other", re.I)
PROJECT_ROLE = re.compile(r"role in (?:the )?project|position in (?:the )?project|^\W*(?:your )?role\b|"
                          r"ตำแหน่งในโครงการ|หน้าที่|บทบาท", re.I)
FULL_NAME = re.compile(r"ชื่อ\s*(?:-|–|/|และ)?\s*(?:นาม)?สกุล|full\s*name|name\s*(?:and|&|/)\s*(?:sur|last\s*|family\s*)name|"
                       r"first and last name", re.I)
NAME_PART = re.compile(r"(?:นาม)?สกุล|ชื่อจริง|ชื่อกลาง|surname|forename|(?:first|last|given|family|middle)\s*-?\s*name", re.I)
BARE_NAME = re.compile(r"\W*(?:ชื่อ|name|title|คำนำหน้า(?:ชื่อ)?)\W*", re.I)
BUDGET_TH = re.compile(r"ค่าตอบแทน|ค่าจ้าง|ค่าวัสดุ|ค่าใช้สอย|ค่าครุภัณฑ์|ค่าเดินทาง|ค่าที่พัก|ค่าเบี้ยเลี้ยง|ค่าสาธารณูปโภค|"
                       r"ค่าธรรมเนียม|ค่าบริหาร|เงินเดือน|เงินสมทบ|รายได้|ยอดขาย|ต่อปี|รายปี|ต่อเดือน")
BUDGET_EN = re.compile(r"salar|wages?\b|stipend|personnel|staff|honorari|material|consumable|equipment|travel|per diem|"
                       r"subcontract|overhead|indirect|matching|co-?funding|in-?kind|revenue|turnover|"
                       r"per (?:year|month|annum)|annual", re.I)
MONEY = re.compile(r"amount|budget|cost|fund|price|fee|expens|\$|฿|€|£|บาท|งบประมาณ|จำนวนเงิน|วงเงิน", re.I)
BUDGET_CTX = re.compile(r"use[sd]? of funds|funds will be used|budget|expenditure|spend|cost (?:categor|item)|"
                        r"หมวดค่าใช้จ่าย|ค่าใช้จ่าย|การใช้จ่าย|งบประมาณ|การใช้เงิน", re.I)
CHOICE = ("checkbox", "radio", "select")
TABLE_ROW = "[table row]"

# Currency markers, checked in order: prefixed dollars (US$, S$...) are consumed before a bare "$" means USD.
_CUR_SIGNS = [
    ("USD", r"US\$|US ?dollars?|ดอลลาร์สหรัฐ"), ("SGD", r"\bS\$|singapore dollars?"), ("AUD", r"\bA\$"), ("CAD", r"\bC\$"),
    ("HKD", r"\bHK\$"), ("NZD", r"\bNZ\$"), ("TWD", r"\bNT\$"), ("BRL", r"\bR\$"), ("THB", r"บาท|฿|\bbaht\b"),
    ("EUR", r"€|\beuros?\b"), ("GBP", r"£|sterling"), ("JPY", r"¥|\byen\b|円"), ("KRW", r"₩"), ("INR", r"₹|rupees?"),
    ("PHP", r"₱|pesos?"), ("VND", r"₫"), ("MYR", r"\bRM\b|ringgit"), ("IDR", r"\bRp\b|rupiah"), ("CNY", r"\bRMB\b|yuan"),
]
_ISO = set(USD_PER) | {cur for _, cur in taxonomy.COUNTRIES.values()}


def has_placeholder(text: object) -> bool:
    return isinstance(text, str) and any(p in text for p in PLACEHOLDERS)


def _thai(label: str) -> bool:
    return any("฀" <= ch <= "๿" for ch in label)


def _currencies(text: str) -> set[str]:
    found = set()
    for code, pat in _CUR_SIGNS:
        if re.search(pat, text, re.I):
            found.add(code)
            text = re.sub(pat, " ", text, flags=re.I)
    found |= {m for m in re.findall(r"\b[A-Z]{3}\b", text) if m in _ISO}
    return found | ({"USD"} if "$" in text else set())


@dataclass
class Ctx:
    profile: ProjectProfile
    applicant: Applicant
    grant: Grant


Resolved = tuple[str | bool | list[str] | None, str, str]  # (value, status, rationale)


def _fields(c: Ctx, th: bool = False) -> str:
    return ", ".join((taxonomy.FIELDS_TH.get(f) if th else None) or taxonomy.field_label(f) for f in c.profile.fields)


def _uses(c: Ctx, th: bool = False) -> list[str]:
    return [(taxonomy.USES_OF_FUNDS_TH[u] if th else taxonomy.USES_OF_FUNDS[u]) for u in c.profile.uses_of_funds]


def _evidence(c: Ctx, th: bool = False) -> list[str]:
    return [(taxonomy.EVIDENCE_TH[e] if th else taxonomy.EVIDENCE[e]["label"]) for e in c.profile.evidence]


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1] if items else ""


def _request_usd(c: Ctx) -> tuple[float, bool]:
    """Ask for the top of your need, but never more than the grant's own maximum award."""
    need = c.profile.funding_max_usd
    cap = c.grant.amount_max_usd
    return (cap, True) if cap is not None and cap < need else (need, False)


def _amount(c: Ctx, label: str, hint: str = "") -> Resolved:
    text = f"{label} {hint}"
    curs = _currencies(text)
    if len(curs) > 1:
        return None, "red", f"The form mentions more than one currency ({', '.join(sorted(curs))}) - enter the amount yourself"
    th = _thai(label)
    cur = next(iter(curs), None) or ("THB" if th else None)  # a Thai form that names no currency means baht
    if cur is None and c.grant.currency and c.grant.currency.upper() != "USD":
        cur = c.grant.currency.upper()
    usd, capped = _request_usd(c)
    why_cap = " (capped at this grant's maximum award)" if capped else ""
    scale = 1e6 if re.search(r"ล้าน|million|\bmn\b", text, re.I) else 1e3 if re.search(r"พันบาท|thousands?|'000", text, re.I) else 1

    def fmt(v: float) -> str:
        return f"{v:,.0f}" if scale == 1 else f"{v / scale:,.2f}".rstrip("0").rstrip(".")

    if cur == "USD":
        if capped or scale != 1:
            return fmt(usd), "amber", f"Your funding need in USD{why_cap} - check the figure and its units"
        return fmt(usd), "green", "Upper end of your stated funding need (USD)"
    if cur is None:
        return fmt(usd), "amber", f"Your funding need in USD{why_cap} - the form doesn't say which currency it expects; confirm it is USD"
    orig = c.grant.raw.get("amount_original") or {}
    if capped and orig.get("currency") == cur and orig.get("max"):
        return fmt(orig["max"]), "amber", f"This grant's maximum award in {cur} - confirm you need the full amount"
    rate = USD_PER.get(cur)
    if not rate:
        return None, "red", f"Your funding need is in USD and there is no exchange rate for {cur} - enter the amount yourself"
    note = (f"{PLACEHOLDER_TH} ตัวเลขประมาณการ แปลงจาก USD {usd:,.0f} - ใส่จำนวนเงินที่ถูกต้อง]" if th
            else f"{PLACEHOLDER} estimate converted from USD {usd:,.0f} - enter the exact {cur} amount]")
    return (f"{fmt(usd / rate)} {note}", "amber",
            f"USD {usd:,.0f}{why_cap} converted to {cur} at an indicative rate - an estimate, not your figure")


def _duration(c: Ctx, label: str, hint: str = "") -> Resolved:
    if re.search(r"year|\bdays?\b|ปี|วัน", label, re.I) and not re.search(r"month|เดือน", label, re.I):
        return None, "red", "The form asks for a unit other than months - enter the duration yourself"
    return str(c.profile.months_to_milestone), "amber", "Months to your next milestone - confirm this equals the project duration"


def _applicant(attr: str) -> Callable[..., Resolved]:
    def r(c: Ctx, label: str, hint: str = "") -> Resolved:
        v = getattr(c.applicant, attr)
        return (v, "green", "From your applicant details") if v else (None, "red", "Add this in your applicant details")
    r.applicant = attr  # type: ignore[attr-defined]  # marks the resolvers allowed in your row of a team table
    return r


def _stage(c: Ctx, label: str, hint: str = "") -> Resolved:
    th = _thai(label)
    ev = ", ".join(_evidence(c, th))
    if th:
        v = f"TRL {c.profile.trl}" + (f" (หลักฐาน: {ev})" if ev else "")
    else:
        v = f"TRL {c.profile.trl} - {taxonomy.TRL_LEVELS[c.profile.trl]['name']}" + (f" (evidence: {ev})" if ev else "")
    return v, "green", "From your TRL and evidence"


def _registered(c: Ctx, label: str, hint: str = "") -> Resolved:
    if re.search(r"number|no\.|registration id|เลขทะเบียน|เลขที่จดทะเบียน|เลขนิติบุคคล", label, re.I):
        return None, "red", "Registration number is not part of your profile"
    if _thai(label):
        return ("ใช่" if c.profile.has_entity else "ไม่ใช่"), "green", "From your applicant type"
    return ("Yes" if c.profile.has_entity else "No"), "green", "From your applicant type"


# Order matters: the first matching rule wins. Each resolver is called as fn(ctx, label, hint).
RULES: list[tuple[re.Pattern, Callable[..., Resolved]]] = [
    (re.compile(r"project (title|name)|title of (the )?(project|proposal)|proposal title|^title$|ชื่อโครงการ|ชื่อเรื่อง|ชื่อข้อเสนอ", re.I),
     lambda c, l, *_: (c.profile.nickname, "green", "Your project nickname - make sure it reveals nothing confidential")
     if c.profile.nickname else (None, "red", "Add a non-confidential project title")),
    (re.compile(r"e-?mail|อีเมล", re.I), _applicant("email")),
    (re.compile(r"phone|tel\b|telephone|mobile|โทรศัพท์|มือถือ|โทร\.", re.I), _applicant("phone")),
    (re.compile(r"web ?site|\burl\b|homepage|เว็บไซต์|orcid|linkedin|social media", re.I),
     lambda *_: (None, "red", "Not part of your profile")),
    (re.compile(r"organi[sz]ation name|institution|company name|affiliation|university|legal (entity )?name|employer|organi[sz]ation$|หน่วยงาน|สังกัด|ชื่อบริษัท|ชื่อนิติบุคคล|มหาวิทยาลัย|สถาบัน", re.I),
     _applicant("organization")),
    (re.compile(r"\bposition\b(?!\s+(?:of|in)\b)|job title|designation|academic (?:rank|title)|ตำแหน่ง", re.I), _applicant("position")),
    (re.compile(r"address|ที่อยู่", re.I), _applicant("address")),
    (re.compile(r"(applicant|full|contact|lead|pi|principal investigator'?s?|researcher'?s?|founder'?s?|your)\s*name|^name$|name of (the )?(applicant|pi|principal|lead|researcher)|"
                r"name\s*(and|&)\s*surname|ชื่อ\s*(-|และ)?\s*(นาม)?สกุล|^ชื่อ$|ชื่อผู้(เสนอ|สมัคร|วิจัย)|หัวหน้าโครงการ|ผู้รับผิดชอบโครงการ", re.I),
     _applicant("name")),
    (re.compile(r"\btrl\b|technology readiness|readiness level|ระดับความพร้อม", re.I),
     lambda c, l, *_: (str(c.profile.trl), "green", "Your self-assessed TRL")),
    (re.compile(r"stage of development|development stage|current (status|stage)|maturity|stage$|สถานะของเทคโนโลยี|ระดับการพัฒนา|ขั้นการพัฒนา", re.I), _stage),
    (re.compile(r"amount|funding request|requested funding|funding goal|funding (needed|sought)|budget request|grant request|"
                r"total (budget|cost|request)|how much|งบประมาณ|จำนวนเงิน|วงเงิน|เงินทุนที่ขอ|ทุนที่ขอ", re.I), _amount),
    (re.compile(r"duration|project period|number of months|months|ระยะเวลา|จำนวนเดือน", re.I), _duration),
    (re.compile(r"country|ประเทศ", re.I), lambda c, l, *_: ((taxonomy.COUNTRY_TH.get(c.profile.country) if _thai(l) else None)
     or taxonomy.country_name(c.profile.country), "green", "From your profile")),
    (re.compile(r"applicant type|type of (applicant|organi[sz]ation)|entity type|organi[sz]ation type|legal status|ประเภทผู้(สมัคร|ขอรับทุน)|ประเภทหน่วยงาน|สถานะนิติบุคคล", re.I),
     lambda c, l, *_: ((taxonomy.APPLICANT_TYPES_TH if _thai(l) else taxonomy.APPLICANT_TYPES)[c.profile.applicant_type], "green", "From your profile")),
    (re.compile(r"registered|incorporat|company registration|จดทะเบียน|เป็นนิติบุคคล", re.I), _registered),
    (re.compile(r"keyword|คำสำคัญ|คำค้น", re.I),
     lambda *_: (None, "red", "Your keywords never leave your browser - add the ones you're comfortable sharing")),
    (re.compile(r"sub-?domain|technology area|topic|speciali[sz]ation|ด้านเทคโนโลยี|เทคโนโลยีที่เกี่ยวข้อง|สาขาย่อย", re.I),
     lambda c, *_: (", ".join(c.profile.subdomains), "green", "Your sub-domains") if c.profile.subdomains else (None, "red", "No sub-domain in profile")),
    (re.compile(r"field|sector|discipline|research area|domain|industry|สาขา|อุตสาหกรรม", re.I),
     lambda c, l, *_: (_fields(c, _thai(l)), "green", "Your research fields")),
    (re.compile(r"use of funds|funds will be used|budget categor|หมวดค่าใช้จ่าย|การใช้จ่ายเงิน", re.I),
     lambda c, l, *_: (", ".join(_uses(c, _thai(l))), "green", "Your intended uses of funds")
     if c.profile.uses_of_funds else (None, "red", "No uses of funds in profile")),
    (re.compile(r"(name|title) of (the )?(grant|program(me)?|call|scheme)|program(me)? applied (for|to)|call (name|title)|ชื่อทุน|ชื่อแหล่งทุน", re.I),
     lambda c, *_: (c.grant.title, "green", "The opportunity you're applying to")),
]


def _table_row(spec: FieldSpec) -> bool:
    return (spec.hint or "").lstrip().lower().startswith(TABLE_ROW)


def _budget_line(text: str, ftype: str) -> bool:
    return bool(BUDGET_TH.search(text) or (BUDGET_EN.search(text) and (ftype == "number" or MONEY.search(text) or _currencies(text))))


def _gate(spec: FieldSpec, near: str = "") -> str | None:
    """Why this field must stay with the researcher whatever the rules or the model propose; None if it may be filled.
    `near` holds the labels of neighbouring fields that share this field's hint (same paragraph or row)."""
    label, hint = spec.label.strip(), spec.hint or ""
    ctx = f"{label} {hint} {spec.id.replace('_', ' ')}"
    if not re.sub(r"[\W\d_]+", "", label):
        return "This field has no label, so nothing can safely go in it"
    if spec.type == "signature" or NEVER_FILL.search(ctx):
        return "Only you can provide this"
    if DECLARATION.search(ctx):
        return "Declarations and consents must be read and ticked by you"
    if spec.type == "date" or DATE_LABEL.search(ctx):
        return "Dates are yours to set"
    if THIRD_PARTY.search(ctx):
        return "This is about someone other than you (supervisor, approver, referee, partner...)"
    if HISTORY.search(ctx):
        return "Your track record, publications, education and past funding aren't in your profile"
    if OTHER.search(label):
        return "'Other' answers are yours to specify"
    if PROJECT_ROLE.search(label):
        return "Your role in this project isn't in your profile"
    if (NAME_PART.search(label) and not FULL_NAME.search(label)) or (BARE_NAME.fullmatch(label) and NAME_PART.search(f"{hint} {near}")):
        return "Your profile holds only your full name - split it yourself"
    if re.fullmatch(r"\W*(?:สาขา|branch)\W*", label, re.I) and re.search(BANK, near, re.I):
        return "Only you can provide this"  # a bank branch, not a research field
    if _table_row(spec) and not TEAM.search(ctx):
        return "Rows of this table are yours to fill"
    row = re.search(r"\((\d+)\)$", label)
    if row and int(row.group(1)) >= 2:  # 2nd+ rows of a repeating table (team members, partners...)
        return "Additional rows are yours to fill"
    if not spec.narrative and spec.type not in CHOICE and _budget_line(f"{label} {hint}", spec.type):
        return "Your profile has no budget breakdown - enter this line yourself"
    return None


# ---------------------------------------------------------------------------
# Choices: whole-word matching against the controlled vocabulary
# ---------------------------------------------------------------------------

def _vocab(c: Ctx) -> list[tuple[str, str, bool]]:
    """Every vocabulary term (English and Thai) with its category and whether the profile selects it."""
    p, out = c.profile, []
    for k, v in taxonomy.USES_OF_FUNDS.items():
        out += [(v, "use of funds", k in p.uses_of_funds), (taxonomy.USES_OF_FUNDS_TH[k].split(" (")[0], "use of funds", k in p.uses_of_funds)]
    for k, f in taxonomy.FIELDS.items():
        out += [(f["label"], "research field", k in p.fields), (taxonomy.FIELDS_TH[k], "research field", k in p.fields)]
        out += [(s, "sub-domain", s in p.subdomains) for s in f["subdomains"]]
    for k, e in taxonomy.EVIDENCE.items():
        out += [(e["label"], "evidence", k in p.evidence), (taxonomy.EVIDENCE_TH[k], "evidence", k in p.evidence)]
    for k, a in taxonomy.APPLICANT_TYPES.items():
        mine = k == p.applicant_type
        out += [(a.split(" (")[0], "applicant type", mine), (taxonomy.APPLICANT_TYPES_TH[k].split(" (")[0], "applicant type", mine)]
    return out


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w฀-๿]+", " ", s.lower()).split())


_JOINT = r"(?:และ|[\s()/,]|$)"


def _term_match(term: str, label: str) -> bool:
    """Whole words only, never a bare substring. Thai is written without spaces, so there a prefix match counts
    only where a word must end: before และ ('and'), a space, a bracket, '/' or the end of the text."""
    t, l = term.lower().strip(), label.lower().strip()
    if not t or not l:
        return False
    if _norm(t) == _norm(l):
        return True
    if _thai(t) or _thai(l):
        return bool(re.search(r"(?:^|[\s:(/,])" + re.escape(t) + _JOINT, l) or (len(l) > 2 and re.match(re.escape(l) + _JOINT, t)))
    nt, nl = _norm(t), _norm(l)
    return bool(re.search(rf"(?<!\S){re.escape(nt)}(?!\S)", nl) or (len(nl) > 3 and re.match(rf"{re.escape(nl)}(?!\S)", nt)))


def _budget_ctx(spec: FieldSpec) -> bool | None:
    """True for a uses-of-funds question, False for any other known context, None when only a bare label is known."""
    if BUDGET_CTX.search(f"{spec.label} {spec.hint or ''}"):
        return True
    return False if (spec.hint or spec.options or ":" in spec.label) else None


def _matches(text: str, c: Ctx, budget: bool | None) -> list[tuple[str, str, bool]]:
    # In a budget question only uses-of-funds words count; anywhere else they must not tick anything.
    return [m for m in _vocab(c) if (budget is None or (m[1] == "use of funds") == budget) and _term_match(m[0], text)]


def _checkbox(spec: FieldSpec, c: Ctx) -> Resolved | None:
    ms = _matches(spec.label, c, _budget_ctx(spec))
    if len({cat for _, cat, _ in ms}) != 1:
        return None  # no match, or the label could mean more than one kind of thing
    hit = next((cat for _, cat, mine in ms if mine), None)
    return (True, "green", f"Matches your {hit}") if hit else (False, "green", "Not in your profile")


def _pick_options(value: str, options: list[str]) -> list[str]:
    """The option equal to value, else options whose words appear whole in value (or value's in them), in value order."""
    v = _norm(value)
    if not v or not options:
        return []
    exact = [o for o in options if _norm(o) == v]
    if exact:
        return exact[:1]
    hits = []
    for o in options:
        n = _norm(o)
        m = re.search(rf"(?<!\S){re.escape(n)}(?!\S)", v) if n else None
        if m or (n and re.search(rf"(?<!\S){re.escape(v)}(?!\S)", n)):
            hits.append((m.start() if m else 0, o))
    return [o for _, o in sorted(hits, key=lambda h: h[0])]


def _pick_option(value: str, options: list[str]) -> str | None:
    hits = _pick_options(value, options)
    return hits[0] if len(hits) == 1 else None


def _group_choice(spec: FieldSpec, c: Ctx) -> Resolved | None:
    """Radio/select/checkbox-group: pick option(s) that match profile vocabulary."""
    budget = _budget_ctx(spec)
    opts = [o for o in spec.options if not DECLARATION.search(o) and not OTHER.search(o)]
    chosen = [o for o in opts if any(mine for _, _, mine in _matches(o, c, budget))]
    if spec.type == "checkbox":
        return (chosen, "green", "Options matching your profile") if chosen else None
    if re.search(r"\btrl\b|readiness", spec.label, re.I):
        o = _pick_option(str(c.profile.trl), spec.options) or _pick_option(f"TRL {c.profile.trl}", spec.options)
        if o:
            return o, "green", "Your TRL"
    if len(chosen) == 1:
        return chosen[0], "green", "Matches your profile"
    evidence_order = [taxonomy.EVIDENCE[e]["label"].lower() for e in taxonomy.EVIDENCE if e in c.profile.evidence]
    evidence_order += [taxonomy.EVIDENCE_TH[e] for e in taxonomy.EVIDENCE if e in c.profile.evidence]
    ranked = [o for o in chosen if o.lower() in evidence_order]
    if ranked:
        best = max(ranked, key=lambda o: evidence_order.index(o.lower()))
        return best, "green", "Your most advanced evidence"
    return None


def deterministic(spec: FieldSpec, c: Ctx, near: str = "") -> FilledField | None:
    base = dict(field_id=spec.id, label=spec.label, type=spec.type, required=spec.required, options=spec.options,
                maxlen=spec.maxlen, narrative=spec.narrative)
    why = _gate(spec, near)
    if why:
        return FilledField(**base, value=None, status="red", source="none", rationale=why)

    res: Resolved | None = None
    used = None
    if spec.type == "checkbox" and not spec.options:
        res = _checkbox(spec, c)
    elif spec.type in ("radio", "select") or (spec.type == "checkbox" and spec.options):
        res = _group_choice(spec, c)
        if res is None:
            for pat, fn in RULES:
                if pat.search(spec.label):
                    v, st, why = fn(c, spec.label, spec.hint or "")
                    hits = _pick_options(str(v), spec.options) if v else []
                    if len(hits) == 1:
                        res = (hits[0], st, why)
                    elif hits:
                        res = (hits[0], "amber", f"{why} - more than one option matches; check this one")
                    break
    elif not spec.narrative:
        for pat, fn in RULES:
            if pat.search(spec.label) or pat.search(spec.id.replace("_", " ")):
                res, used = fn(c, spec.label, spec.hint or ""), fn
                break
    if _table_row(spec):  # only the team table gets here (see _gate), and it may not be the researcher's own row
        if not (getattr(used, "applicant", None) and res and res[0]):
            return FilledField(**base, value=None, status="red", source="none",
                               rationale="In a table only your own name and contact details are suggested - fill the rest yourself")
        res = (res[0], "amber", "From your applicant details - check this table row is meant for you")
    if res is None:
        return None
    value, status, why = res
    return FilledField(**base, value=value, status=status if value not in (None, "", []) else "red",
                       source="profile" if value not in (None, "", []) else "none", rationale=why)


# ---------------------------------------------------------------------------
# Narrative scaffolds (used when the LLM is unavailable)
# ---------------------------------------------------------------------------

def scaffold(label: str, c: Ctx) -> str:
    if _thai(label):
        return scaffold_th(label, c)
    p = c.profile
    fields = _join([taxonomy.field_label(f).lower() for f in p.fields])
    subs = _join([s.lower() for s in p.subdomains]) or fields
    stage = f"TRL {p.trl} ({taxonomy.TRL_LEVELS[p.trl]['name'].lower()})"
    evidence = _join([taxonomy.EVIDENCE[e]["label"].lower() for e in p.evidence]) or f"{PLACEHOLDER} your current evidence]"
    uses = _join([taxonomy.USES_OF_FUNDS[u].lower() for u in p.uses_of_funds]) or f"{PLACEHOLDER} uses of funds]"
    usd, _ = _request_usd(c)
    amount = f"USD {usd:,.0f}"
    low = label.lower()
    if re.search(r"innovation|novel|what is new|new compared|unique", low):
        return (f"{PLACEHOLDER} what is new compared with existing solutions, described without confidential method detail]. "
                f"The work is in {subs} and is at {stage}, supported by {evidence}. "
                f"{PLACEHOLDER} the main advantage over the current best alternative, with one figure if you can share it].")
    if re.search(r"context|background|problem|motivation", low):
        return (f"{PLACEHOLDER} the problem this work addresses and who has it]. This {fields} project in {subs} is at {stage}, "
                f"with existing evidence from {evidence}. {PLACEHOLDER} why current approaches fall short].")
    if re.search(r"objective|aim|goal", low):
        return (f"The objective is to take this {subs} work from {stage} toward TRL {min(9, p.trl + 2)} within "
                f"{p.months_to_milestone} months. {PLACEHOLDER} the specific, measurable objective - what will work at the end that does not work today].")
    if re.search(r"impact|benefit|market|commerciali|outcome|significan", low):
        return (f"If successful, this {fields} work would {PLACEHOLDER} who benefits and how, with one quantified estimate]. "
                f"{PLACEHOLDER} the market or societal need, with a source].")
    if re.search(r"plan|methodolog|approach|timeline|milestone|work", low):
        return (f"Over {p.months_to_milestone} months: (1) {PLACEHOLDER} first work package]; (2) {PLACEHOLDER} second work package]; "
                f"(3) {PLACEHOLDER} final milestone and how it will be verified]. Funds will be used for {uses}.")
    if re.search(r"budget|justif|cost", low):
        return f"The requested {amount} will cover {uses}. {PLACEHOLDER} itemised costs for each category]."
    if re.search(r"team|experience|capabilit", low):
        return f"{PLACEHOLDER} team members, their roles and relevant experience]."
    if re.search(r"risk", low):
        return f"{PLACEHOLDER} the two or three main technical and commercial risks, and how each is mitigated]."
    return (f"This is a {fields} project in {subs}, currently at {stage}, with existing evidence from {evidence}. "
            f"{PLACEHOLDER} a non-confidential description of what is new compared with existing solutions]. "
            f"The requested {amount} would fund {uses} over {p.months_to_milestone} months to reach the next milestone: "
            f"{PLACEHOLDER} next milestone].")


def scaffold_th(label: str, c: Ctx) -> str:
    """Thai-language scaffolds for Thai forms; placeholders use [ต้องเพิ่ม: ...] so reviewers can read them."""
    p, P = c.profile, PLACEHOLDER_TH
    fields = ", ".join(taxonomy.FIELDS_TH[f] for f in p.fields)
    subs = ", ".join(p.subdomains) or fields
    evidence = ", ".join(_evidence(c, True)) or f"{P} หลักฐานที่มีในปัจจุบัน]"
    uses = ", ".join(_uses(c, True)) or f"{P} หมวดการใช้เงิน]"
    usd, _ = _request_usd(c)
    amount = f"ประมาณ {usd / USD_PER['THB']:,.0f} บาท (ประมาณการจาก USD {usd:,.0f})"  # converted, so never stated as exact
    if re.search(r"นวัตกรรม|ความใหม่|จุดเด่น", label):
        return (f"{P} ความใหม่เมื่อเทียบกับเทคโนโลยีที่มีอยู่ โดยไม่เปิดเผยรายละเอียดที่เป็นความลับ] "
                f"งานนี้อยู่ในด้าน {subs} ปัจจุบันอยู่ที่ระดับความพร้อมทางเทคโนโลยี TRL {p.trl} โดยมีหลักฐานจาก {evidence} "
                f"{P} ข้อได้เปรียบหลักเหนือทางเลือกที่ดีที่สุดในปัจจุบัน พร้อมตัวเลขหนึ่งค่าหากเปิดเผยได้]")
    if re.search(r"ความเป็นมา|หลักการและเหตุผล|ที่มา|ปัญหา", label):
        return (f"{P} ปัญหาที่งานนี้แก้ไขและผู้ที่ประสบปัญหา] โครงการนี้อยู่ในสาขา{fields} ด้าน {subs} "
                f"ปัจจุบันอยู่ที่ TRL {p.trl} โดยมีหลักฐานจาก {evidence} {P} เหตุผลที่แนวทางเดิมยังไม่เพียงพอ]")
    if re.search(r"วัตถุประสงค์|เป้าหมาย", label):
        return (f"เพื่อพัฒนางานด้าน {subs} จาก TRL {p.trl} ไปสู่ TRL {min(9, p.trl + 2)} ภายใน {p.months_to_milestone} เดือน "
                f"{P} วัตถุประสงค์ที่วัดผลได้ เช่น สิ่งที่ต้องทำได้เมื่อสิ้นสุดโครงการ]")
    if re.search(r"ผลกระทบ|ประโยชน์|ผลที่คาดว่าจะได้รับ|ตลาด|เชิงพาณิชย์", label):
        return (f"หากโครงการสำเร็จ จะ{P} ผู้ได้รับประโยชน์และประโยชน์ที่ได้รับ พร้อมตัวเลขประมาณการอย่างน้อยหนึ่งค่า] "
                f"{P} ความต้องการของตลาดหรือสังคม พร้อมแหล่งอ้างอิง]")
    if re.search(r"แผน|วิธีการ|ระเบียบวิธี|ขั้นตอน", label):
        return (f"ระยะเวลา {p.months_to_milestone} เดือน: (1) {P} กิจกรรมที่ 1] (2) {P} กิจกรรมที่ 2] "
                f"(3) {P} เป้าหมายสุดท้ายและวิธีการตรวจวัด] งบประมาณใช้สำหรับ {uses}")
    if re.search(r"งบประมาณ|ค่าใช้จ่าย", label):
        return f"งบประมาณที่ขอ {amount} ใช้สำหรับ {uses} {P} รายละเอียดค่าใช้จ่ายแยกตามหมวด]"
    if re.search(r"คณะผู้วิจัย|ทีม|ประสบการณ์", label):
        return f"{P} รายชื่อคณะผู้วิจัย บทบาท และประสบการณ์ที่เกี่ยวข้อง]"
    if re.search(r"ความเสี่ยง", label):
        return f"{P} ความเสี่ยงหลักด้านเทคนิคและธุรกิจ 2-3 ข้อ และแนวทางลดความเสี่ยง]"
    return (f"โครงการนี้อยู่ในสาขา{fields} ด้าน {subs} ปัจจุบันอยู่ที่ TRL {p.trl} โดยมีหลักฐานจาก {evidence} "
            f"{P} คำอธิบายที่ไม่เป็นความลับว่าแตกต่างจากเทคโนโลยีที่มีอยู่อย่างไร] "
            f"งบประมาณที่ขอ {amount} จะใช้สำหรับ {uses} ภายในระยะเวลา {p.months_to_milestone} เดือน "
            f"เพื่อบรรลุเป้าหมายถัดไป: {P} เป้าหมายถัดไป]")


# ---------------------------------------------------------------------------
# LLM pass for everything the rules couldn't place
# ---------------------------------------------------------------------------

SYSTEM = """You help a researcher pre-fill a grant application form. You receive the form fields that are still empty, the researcher's NON-CONFIDENTIAL profile (categories, stage and needs only - deliberately no method, composition or data), and the grant's public details.

For every field return exactly one action:
- "fill": only when the value follows directly from the provided data. Respect maxlen and, for choice fields, return one of the listed options exactly.
- "draft": for narrative questions (describe, objectives, impact, plan, budget justification, team...). Write a short scaffold using only facts in the profile, and put an explicit placeholder of the exact form [YOU MUST ADD: <what is needed>] wherever specific technical, quantitative, or personal content is required. Never fill those gaps yourself.
- "cannot_fill": personal or legal details not provided, signatures, dates, declarations or consents, bank or registration numbers, or anything else you don't have the data for.

Write each value in the same language as the field's label: Thai labels get Thai answers, using the placeholder form [ต้องเพิ่ม: <สิ่งที่ต้องเพิ่ม>] instead of [YOU MUST ADD: ...].

Never invent results, data, numbers, names, partners, publications, prior funding, or technical details. Never describe or guess the researcher's method or invention. A fabricated claim in a grant application exposes the researcher to fraud allegations - when in doubt, use a placeholder or "cannot_fill"."""

SCHEMA = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field_id": {"type": "string"},
                    "action": {"type": "string", "enum": ["fill", "draft", "cannot_fill"]},
                    "value": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["field_id", "action", "value", "rationale"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["fields"],
    "additionalProperties": False,
}


def _llm_map(specs: list[FieldSpec], c: Ctx) -> dict[str, dict]:
    if not specs or not llm.enabled():
        return {}
    from ..match.explain import _profile_brief  # same non-confidential projection used for explanations

    payload = {
        "fields": [s.model_dump(include={"id", "label", "type", "options", "maxlen", "required", "hint"}) for s in specs],
        "researcher_profile": {**_profile_brief(c.profile), "project_title": c.profile.nickname},
        "grant": {"title": c.grant.title, "funder": c.grant.funder_name, "summary": (c.grant.summary or "")[:1200]},
    }
    result = llm.structured(
        system=SYSTEM,
        user="Propose values for these form fields.\n\n" + json.dumps(payload, ensure_ascii=False),
        schema=SCHEMA,
        effort="medium",
    )
    return {f["field_id"]: f for f in (result or {}).get("fields", []) if isinstance(f, dict) and "field_id" in f}


def _grounded_numbers(c: Ctx) -> set[str]:
    p = c.profile
    nums = {str(p.trl), str(p.months_to_milestone), str(min(9, p.trl + 1)), str(min(9, p.trl + 2))}
    for v in (p.funding_min_usd, p.funding_max_usd, c.grant.amount_min_usd, c.grant.amount_max_usd):
        if v:
            nums |= {f"{v:,.0f}", f"{v:.0f}"}
    nums |= set(re.findall(r"\d[\d,.]*", c.grant.summary or ""))
    return nums


def _flag_ungrounded(f: FilledField, c: Ctx) -> None:
    """Model-written text must not introduce figures the researcher never gave us."""
    if f.source != "llm" or not isinstance(f.value, str):
        return
    found = set(re.findall(r"\d[\d,.]*\d|\d", f.value))
    stray = sorted(n for n in found - _grounded_numbers(c) if len(n.strip(".,")) > 0)
    if stray:
        f.warnings.append(f"Contains figures not from your profile ({', '.join(stray[:4])}) - verify or remove")
        f.confirmed = False


def _fit(value: str, maxlen: int) -> str | None:
    """Shorten to maxlen without leaving half a placeholder: one the cut would drop is put back at the end.
    None when not even a placeholder fits - the value must then not be exported at all."""
    spans = list(PLACEHOLDER_SPAN.finditer(value))
    lost = [m for m in spans if m.end() > maxlen]
    if not lost:
        return value[:maxlen]
    first = lost[0].group(0) if lost[0].group(0).endswith("]") else lost[0].group(0) + "]"
    short = f"{PLACEHOLDER_TH} ส่วนที่เหลือ]" if first.startswith(PLACEHOLDER_TH) else f"{PLACEHOLDER} the rest]"
    for ph in (first, short):
        if len(ph) > maxlen:
            continue
        head = value[: max(maxlen - len(ph) - 1, 0)]
        inside = [m.start() for m in spans if m.start() < len(head) < m.end()]
        head = (head[: inside[0]] if inside else head).rstrip()
        return f"{head} {ph}" if head else ph
    return None


def _enforce(f: FilledField, spec: FieldSpec) -> FilledField:
    """Post-conditions that hold no matter where a value came from."""
    if isinstance(f.value, str):
        if f.narrative and f.value and not has_placeholder(f.value):
            gap = f" {PLACEHOLDER_TH} รายละเอียดทางเทคนิคที่เฉพาะเจาะจง]" if _thai(spec.label) else f" {PLACEHOLDER} specific technical detail]"
            f.value = f.value.rstrip() + gap
        if spec.maxlen and len(f.value) > spec.maxlen:
            fitted = _fit(f.value, spec.maxlen)
            if fitted is None:
                f.value, f.status, f.source = None, "red", "none"
                f.warnings.append(f"Too long for the form's {spec.maxlen}-character limit, and shortening it would drop "
                                  "the part you must add - write this yourself")
            else:
                f.value = fitted
                f.warnings.append(f"Truncated to the form's {spec.maxlen}-character limit")
                if f.status == "green":
                    f.status = "amber"
        if spec.type in ("select", "radio") and spec.options and f.value and f.value not in spec.options:
            o = _pick_option(f.value, spec.options)
            if o:
                f.value = o
            else:
                f.value, f.status, f.source = None, "red", "none"
                f.warnings.append("Proposed value was not one of the form's options")
    if has_placeholder(f.value) and f.status == "green":
        f.status = "amber"
    if f.source == "llm" and f.status == "green":
        f.status = "amber"  # the model never vouches for a value
    return f


def _near(specs: list[FieldSpec], i: int) -> str:
    """Labels of the fields either side of specs[i] that share its hint (same paragraph or table row)."""
    return " ".join(o.label for o in specs[max(i - 1, 0): i + 2] if o is not specs[i] and o.hint == specs[i].hint)


def map_fields(specs: list[FieldSpec], profile: ProjectProfile, applicant: Applicant, grant: Grant) -> tuple[list[FilledField], bool]:
    """Returns (filled fields in form order, whether the LLM contributed)."""
    c = Ctx(profile, applicant, grant)
    out: dict[str, FilledField] = {}
    leftovers: list[FieldSpec] = []
    near = {s.id: _near(specs, i) for i, s in enumerate(specs)}
    for s in specs:
        f = deterministic(s, c, near[s.id])
        if f is not None:
            out[s.id] = f
        else:
            leftovers.append(s)

    # The gate is re-applied here so a guarded field can never reach the model or take its answer.
    gated = {s.id: _gate(s, near[s.id]) for s in leftovers}
    llm_out = _llm_map([s for s in leftovers if not gated[s.id]], c)
    for s in leftovers:
        base = dict(field_id=s.id, label=s.label, type=s.type, required=s.required, options=s.options,
                    maxlen=s.maxlen, narrative=s.narrative)
        r = None if gated[s.id] else llm_out.get(s.id)
        if gated[s.id]:
            out[s.id] = FilledField(**base, value=None, status="red", source="none", rationale=gated[s.id])
        elif r and r.get("action") in ("fill", "draft") and str(r.get("value") or "").strip():
            value: str | bool = str(r["value"]).strip()
            if s.type == "checkbox" and not s.options:
                value = value.lower() in ("true", "yes", "1", "checked")
            out[s.id] = FilledField(**{**base, "narrative": s.narrative or r["action"] == "draft"}, value=value,
                                    status="amber", source="llm", rationale=r.get("rationale") or "Inferred - verify")
        elif s.narrative:
            out[s.id] = FilledField(**base, value=scaffold(s.label, c), status="amber", source="template",
                                    rationale="Draft scaffold from your profile - replace every placeholder")
        else:
            why = (r or {}).get("rationale") or "Not something your profile covers"
            out[s.id] = FilledField(**base, value=None, status="red", source="none", rationale=why)

    filled = [_enforce(out[s.id], s) for s in specs]
    for f in filled:
        _flag_ungrounded(f, c)
    return filled, bool(llm_out)
