"""Label heuristics shared by the PDF and HTML parsers."""

from __future__ import annotations

import re

NARRATIVE = re.compile(
    r"describ|description|summary|abstract|overview|innovation|novelty|objective|aim|goal|impact|benefit|"
    r"market|commerciali|methodolog|approach|work ?plan|workplan|justif|background|problem|solution|"
    r"team|experience|capabilit|motivation|why\b|explain|outcome|risk|strateg|"
    # Thai: objectives, background/rationale, expected results/benefits, work plan/method, innovation/novelty,
    # impact, market/commercial, abstract/summary, details/explain, team/researchers, experience, risk, strategy
    r"วัตถุประสงค์|ความเป็นมา|หลักการและเหตุผล|ที่มา|ผลที่คาดว่าจะได้รับ|ประโยชน์|แผนการดำเนินงาน|วิธีการ|ระเบียบวิธี|"
    r"นวัตกรรม|ความใหม่|ผลกระทบ|ตลาด|เชิงพาณิชย์|บทคัดย่อ|สรุป|รายละเอียด|อธิบาย|คณะผู้วิจัย|ประสบการณ์|ความเสี่ยง|กลยุทธ์",
    re.I,
)
SIGNATURE = re.compile(r"signature|sign here|ลงชื่อ|ลายมือชื่อ", re.I)


def humanize(name: str) -> str:
    """'applicant_org_name' / 'ApplicantOrgName' / 'topmostSubform[0].Page1[0].Name[0]' -> 'Applicant org name'."""
    name = re.sub(r"\[\d+\]", "", name).split(".")[-1]
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"[_\-]+", " ", name).strip()
    return name[:1].upper() + name[1:] if name else name


def guess_type(label: str, base: str = "text") -> str:
    low = label.lower()
    if SIGNATURE.search(low):
        return "signature"
    if base not in ("text",):
        return base
    if "e-mail" in low or "email" in low or "อีเมล" in low:
        return "email"
    if re.search(r"phone|tel\b|telephone|mobile|โทรศัพท์|มือถือ|โทร\.", low):
        return "tel"
    if re.search(r"\bdate\b|\bdob\b|วันที่|วัน เดือน ปี", low):
        return "date"
    if re.search(r"amount|budget|cost|\busd\b|\bthb\b|\beur\b|number of|duration|months|\btrl\b|"
                 r"งบประมาณ|จำนวนเงิน|\(บาท\)|ระยะเวลา|จำนวนเดือน", low):
        return "number"
    return base


def is_narrative(label: str, ftype: str, maxlen: int | None) -> bool:
    if ftype == "textarea":
        return True
    if maxlen and maxlen >= 300:
        return True
    return ftype == "text" and bool(NARRATIVE.search(label)) and not re.search(r"title|name\b|ชื่อ", label, re.I)
