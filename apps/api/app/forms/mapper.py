"""FieldSpec[] x ProjectProfile -> proposed values, each with a confidence state (brief §5.2).

    green  value comes directly from the researcher's own profile/contact details
    amber  inferred (LLM) or drafted scaffold - the researcher must verify it
    red    cannot be filled from what we know - needs the researcher

Hard rules, enforced here regardless of what the LLM returns:
  * declarations, consents and signatures are never filled
  * narrative fields are drafts containing explicit [YOU MUST ADD: ...] placeholders
  * no field is ever filled with content that isn't grounded in the profile or grant data
"""

from __future__ import annotations

import difflib
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
DECLARATION = re.compile(
    r"declar|\bcertify\b|certifications and assurances|i confirm|i agree|consent|acknowledg|attest|undertake|"
    r"terms and conditions|platform terms|true and correct|"
    r"ขอรับรอง|คำรับรอง|ยินยอม|รับทราบ|ยอมรับเงื่อนไข|เป็นความจริงทุกประการ",
    re.I,
)
NEVER_FILL = re.compile(
    r"signature|sign here|date of sign|bank|account number|iban|swift|passport|national id|id card|tax id|"
    r"ลงชื่อ|ลายมือชื่อ|บัญชีธนาคาร|เลขที่บัญชี|เลขประจำตัวประชาชน|บัตรประชาชน|เลขประจำตัวผู้เสียภาษี|หนังสือเดินทาง",
    re.I,
)
DATE_LABEL = re.compile(r"\bdate\b|วันที่|วัน\s*/?\s*เดือน\s*/?\s*ปี", re.I)


def has_placeholder(text: object) -> bool:
    return isinstance(text, str) and any(p in text for p in PLACEHOLDERS)


def _thai(label: str) -> bool:
    return any("\u0e00" <= ch <= "\u0e7f" for ch in label)


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


def _amount(c: Ctx, label: str) -> Resolved:
    usd, capped = _request_usd(c)
    why_cap = " (capped at this grant's maximum award)" if capped else ""
    m = re.search(r"\b(THB|SGD|MYR|IDR|VND|PHP|EUR|GBP|JPY|KRW|AUD|CAD|CHF|INR|baht|euro)\b|(บาท)", label, re.I)
    if m:
        cur = "THB" if m.group(2) else {"baht": "THB", "euro": "EUR"}.get(m.group(1).lower(), m.group(1).upper())
        orig = c.grant.raw.get("amount_original") or {}
        if capped and orig.get("currency") == cur and orig.get("max"):
            return f"{orig['max']:,.0f}", "amber", f"This grant's maximum award in {cur} - confirm you need the full amount"
        local = usd / USD_PER[cur]
        return f"{local:,.0f}", "amber", f"USD {usd:,.0f}{why_cap} converted to {cur} at an indicative rate - confirm the exact figure"
    if capped:
        return f"{usd:,.0f}", "amber", f"Your need exceeds the maximum award; requesting USD {usd:,.0f}{why_cap}"
    return f"{usd:,.0f}", "green", "Upper end of your stated funding need (USD)"


def _applicant(attr: str) -> Callable[[Ctx, str], Resolved]:
    def r(c: Ctx, label: str) -> Resolved:
        v = getattr(c.applicant, attr)
        return (v, "green", "From your applicant details") if v else (None, "red", "Add this in your applicant details")
    return r


def _stage(c: Ctx, label: str) -> Resolved:
    th = _thai(label)
    ev = ", ".join(_evidence(c, th))
    if th:
        v = f"TRL {c.profile.trl}" + (f" (หลักฐาน: {ev})" if ev else "")
    else:
        v = f"TRL {c.profile.trl} - {taxonomy.TRL_LEVELS[c.profile.trl]['name']}" + (f" (evidence: {ev})" if ev else "")
    return v, "green", "From your TRL and evidence"


def _registered(c: Ctx, label: str) -> Resolved:
    if re.search(r"number|no\.|registration id|เลขทะเบียน|เลขที่จดทะเบียน|เลขนิติบุคคล", label, re.I):
        return None, "red", "Registration number is not part of your profile"
    if _thai(label):
        return ("ใช่" if c.profile.has_entity else "ไม่ใช่"), "green", "From your applicant type"
    return ("Yes" if c.profile.has_entity else "No"), "green", "From your applicant type"


# Order matters: the first matching rule wins.
RULES: list[tuple[re.Pattern, Callable[[Ctx, str], Resolved]]] = [
    (re.compile(r"project (title|name)|title of (the )?(project|proposal)|proposal title|^title$|ชื่อโครงการ|ชื่อเรื่อง|ชื่อข้อเสนอ", re.I),
     lambda c, l: (c.profile.nickname, "green", "Your project nickname - make sure it reveals nothing confidential") if c.profile.nickname
     else (None, "red", "Add a non-confidential project title")),
    (re.compile(r"e-?mail|อีเมล", re.I), _applicant("email")),
    (re.compile(r"phone|tel\b|telephone|mobile|โทรศัพท์|มือถือ|โทร\.", re.I), _applicant("phone")),
    (re.compile(r"organi[sz]ation name|institution|company name|affiliation|university|legal (entity )?name|employer|organi[sz]ation$|หน่วยงาน|สังกัด|ชื่อบริษัท|ชื่อนิติบุคคล|มหาวิทยาลัย|สถาบัน", re.I),
     _applicant("organization")),
    (re.compile(r"position|job title|designation|^(your )?role\b|role in (the )?project|ตำแหน่ง", re.I), _applicant("position")),
    (re.compile(r"address|ที่อยู่", re.I), _applicant("address")),
    (re.compile(r"(applicant|full|contact|lead|pi|principal investigator'?s?|researcher'?s?|founder'?s?|your)\s*name|^name$|name of (the )?(applicant|pi|principal|lead|researcher)|ชื่อ\s*-?\s*(นาม)?สกุล|^ชื่อ$|ชื่อผู้(เสนอ|สมัคร|วิจัย)|หัวหน้าโครงการ|ผู้รับผิดชอบโครงการ", re.I),
     _applicant("name")),
    (re.compile(r"\btrl\b|technology readiness|readiness level|ระดับความพร้อม", re.I),
     lambda c, l: (str(c.profile.trl), "green", "Your self-assessed TRL")),
    (re.compile(r"stage of development|development stage|current (status|stage)|maturity|stage$|สถานะของเทคโนโลยี|ระดับการพัฒนา|ขั้นการพัฒนา", re.I), _stage),
    (re.compile(r"amount|funding request|requested funding|funding goal|funding (needed|sought)|budget request|grant request|"
                r"total (budget|cost|request)|how much|งบประมาณ|จำนวนเงิน|วงเงิน|เงินทุนที่ขอ|ทุนที่ขอ", re.I), _amount),
    (re.compile(r"duration|project period|number of months|months|ระยะเวลา|จำนวนเดือน", re.I),
     lambda c, l: (str(c.profile.months_to_milestone), "amber", "Months to your next milestone - confirm this equals the project duration")),
    (re.compile(r"country|ประเทศ", re.I), lambda c, l: ((taxonomy.COUNTRY_TH.get(c.profile.country) if _thai(l) else None)
     or taxonomy.country_name(c.profile.country), "green", "From your profile")),
    (re.compile(r"applicant type|type of (applicant|organi[sz]ation)|entity type|organi[sz]ation type|legal status|ประเภทผู้(สมัคร|ขอรับทุน)|ประเภทหน่วยงาน|สถานะนิติบุคคล", re.I),
     lambda c, l: ((taxonomy.APPLICANT_TYPES_TH if _thai(l) else taxonomy.APPLICANT_TYPES)[c.profile.applicant_type], "green", "From your profile")),
    (re.compile(r"registered|incorporat|company registration|จดทะเบียน|เป็นนิติบุคคล", re.I), _registered),
    (re.compile(r"keyword|คำสำคัญ|คำค้น", re.I),
     lambda c, l: (None, "red", "Your keywords never leave your browser - add the ones you're comfortable sharing")),
    (re.compile(r"sub-?domain|technology area|topic|speciali[sz]ation|ด้านเทคโนโลยี|เทคโนโลยีที่เกี่ยวข้อง|สาขาย่อย", re.I),
     lambda c, l: (", ".join(c.profile.subdomains), "green", "Your sub-domains") if c.profile.subdomains else (None, "red", "No sub-domain in profile")),
    (re.compile(r"field|sector|discipline|research area|domain|industry|สาขา|อุตสาหกรรม", re.I),
     lambda c, l: (_fields(c, _thai(l)), "green", "Your research fields")),
    (re.compile(r"use of funds|funds will be used|budget categor|หมวดค่าใช้จ่าย|การใช้จ่ายเงิน", re.I),
     lambda c, l: (", ".join(_uses(c, _thai(l))), "green", "Your intended uses of funds")
     if c.profile.uses_of_funds else (None, "red", "No uses of funds in profile")),
    (re.compile(r"(name|title) of (the )?(grant|program(me)?|call|scheme)|program(me)? applied (for|to)|call (name|title)|ชื่อทุน|ชื่อแหล่งทุน", re.I),
     lambda c, l: (c.grant.title, "green", "The opportunity you're applying to")),
]


def _vocab_hits(c: Ctx) -> dict[str, str]:
    """Phrases that, appearing in a checkbox label, mean 'tick this' based on the profile."""
    hits = {}
    for u in c.profile.uses_of_funds:
        hits[taxonomy.USES_OF_FUNDS[u].lower()] = "use of funds"
    for f in c.profile.fields:
        hits[taxonomy.field_label(f).lower()] = "research field"
    for s in c.profile.subdomains:
        hits[s.lower()] = "sub-domain"
    for e in c.profile.evidence:
        hits[taxonomy.EVIDENCE[e]["label"].lower()] = "evidence"
    hits[taxonomy.APPLICANT_TYPES[c.profile.applicant_type].split(" (")[0].lower()] = "applicant type"
    # Thai equivalents, for Thai-language forms
    for u in c.profile.uses_of_funds:
        hits[taxonomy.USES_OF_FUNDS_TH[u].split(" (")[0]] = "use of funds"
    for f in c.profile.fields:
        hits[taxonomy.FIELDS_TH[f]] = "research field"
    for e in c.profile.evidence:
        hits[taxonomy.EVIDENCE_TH[e]] = "evidence"
    hits[taxonomy.APPLICANT_TYPES_TH[c.profile.applicant_type].split(" (")[0]] = "applicant type"
    return hits


_VOCAB_ALL = (
    [v.lower() for v in taxonomy.USES_OF_FUNDS.values()]
    + [f["label"].lower() for f in taxonomy.FIELDS.values()]
    + [s.lower() for f in taxonomy.FIELDS.values() for s in f["subdomains"]]
    + [e["label"].lower() for e in taxonomy.EVIDENCE.values()]
    + [a.split(" (")[0].lower() for a in taxonomy.APPLICANT_TYPES.values()]
    + [v.split(" (")[0] for v in taxonomy.USES_OF_FUNDS_TH.values()]
    + list(taxonomy.FIELDS_TH.values()) + list(taxonomy.EVIDENCE_TH.values())
    + [a.split(" (")[0] for a in taxonomy.APPLICANT_TYPES_TH.values()]
)


def _checkbox(spec: FieldSpec, c: Ctx) -> Resolved | None:
    low = spec.label.lower()
    hits = _vocab_hits(c)
    for phrase, why in hits.items():
        if phrase in low or (len(low) > 3 and low in phrase):
            return True, "green", f"Matches your {why}"
    if any(v in low or (len(low) > 3 and low in v) for v in _VOCAB_ALL):
        return False, "green", "Not in your profile"
    return None


def _pick_option(value: str, options: list[str]) -> str | None:
    if not options or not value:
        return None
    low = {o.lower(): o for o in options}
    if value.lower() in low:
        return low[value.lower()]
    for o in options:
        if o.lower() in value.lower() or value.lower() in o.lower():
            return o
    best = difflib.get_close_matches(value.lower(), list(low), n=1, cutoff=0.6)
    return low[best[0]] if best else None


def _group_choice(spec: FieldSpec, c: Ctx) -> Resolved | None:
    """Radio/select/checkbox-group: pick option(s) that match profile vocabulary."""
    hits = _vocab_hits(c)
    chosen = [o for o in spec.options if any(h in o.lower() or o.lower() in h for h in hits if len(o) > 2)]
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


def deterministic(spec: FieldSpec, c: Ctx) -> FilledField | None:
    base = dict(field_id=spec.id, label=spec.label, type=spec.type, required=spec.required, options=spec.options,
                maxlen=spec.maxlen, narrative=spec.narrative)
    if spec.type == "signature" or NEVER_FILL.search(spec.label):
        return FilledField(**base, value=None, status="red", source="none", rationale="Only you can provide this")
    if DECLARATION.search(spec.label):
        return FilledField(**base, value=None, status="red", source="none",
                           rationale="Declarations and consents must be read and ticked by you")
    if DATE_LABEL.search(spec.label):
        return FilledField(**base, value=None, status="red", source="none", rationale="Dates are yours to set")
    row = re.search(r"\((\d+)\)$", spec.label.strip())
    if row and int(row.group(1)) >= 2:  # 2nd+ rows of a repeating table (team members, partners...)
        return FilledField(**base, value=None, status="red", source="none", rationale="Additional rows are yours to fill")

    res: Resolved | None = None
    if spec.type == "checkbox" and not spec.options:
        res = _checkbox(spec, c)
    elif spec.type in ("radio", "select") or (spec.type == "checkbox" and spec.options):
        res = _group_choice(spec, c)
        if res is None:
            for pat, fn in RULES:
                if pat.search(spec.label):
                    v, st, why = fn(c, spec.label)
                    o = _pick_option(str(v), spec.options) if v else None
                    if o:
                        res = (o, st, why)
                    break
    elif not spec.narrative:
        for pat, fn in RULES:
            if pat.search(spec.label) or pat.search(spec.id.replace("_", " ")):
                res = fn(c, spec.label)
                break
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
    amount = f"{usd / USD_PER['THB']:,.0f} บาท"
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


def _enforce(f: FilledField, spec: FieldSpec) -> FilledField:
    """Post-conditions that hold no matter where a value came from."""
    if isinstance(f.value, str):
        if f.narrative and f.value and not has_placeholder(f.value):
            gap = f" {PLACEHOLDER_TH} รายละเอียดทางเทคนิคที่เฉพาะเจาะจง]" if _thai(spec.label) else f" {PLACEHOLDER} specific technical detail]"
            f.value = f.value.rstrip() + gap
        if spec.maxlen and len(f.value) > spec.maxlen:
            f.value = f.value[: spec.maxlen]
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
    if f.narrative and has_placeholder(f.value) and f.status == "green":
        f.status = "amber"
    return f


def map_fields(specs: list[FieldSpec], profile: ProjectProfile, applicant: Applicant, grant: Grant) -> tuple[list[FilledField], bool]:
    """Returns (filled fields in form order, whether the LLM contributed)."""
    c = Ctx(profile, applicant, grant)
    out: dict[str, FilledField] = {}
    leftovers: list[FieldSpec] = []
    for s in specs:
        f = deterministic(s, c)
        if f is not None:
            out[s.id] = f
        else:
            leftovers.append(s)

    llm_out = _llm_map(leftovers, c)
    for s in leftovers:
        base = dict(field_id=s.id, label=s.label, type=s.type, required=s.required, options=s.options,
                    maxlen=s.maxlen, narrative=s.narrative)
        r = llm_out.get(s.id)
        if r and r.get("action") in ("fill", "draft") and r.get("value", "").strip() and not DECLARATION.search(s.label):
            value: str | bool = r["value"].strip()
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
