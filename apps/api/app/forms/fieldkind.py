"""Label heuristics shared by the PDF and HTML parsers."""

from __future__ import annotations

import re

NARRATIVE = re.compile(
    r"describ|description|summary|abstract|overview|innovation|novelty|objective|aim|goal|impact|benefit|"
    r"market|commerciali|methodolog|approach|work ?plan|workplan|justif|background|problem|solution|"
    r"team|experience|capabilit|motivation|why\b|explain|outcome|risk|strateg",
    re.I,
)
SIGNATURE = re.compile(r"signature|sign here", re.I)


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
    if "e-mail" in low or "email" in low:
        return "email"
    if re.search(r"phone|tel\b|telephone|mobile", low):
        return "tel"
    if re.search(r"\bdate\b|\bdob\b", low):
        return "date"
    if re.search(r"amount|budget|cost|\busd\b|\bthb\b|\beur\b|number of|duration|months|\btrl\b", low):
        return "number"
    return base


def is_narrative(label: str, ftype: str, maxlen: int | None) -> bool:
    if ftype == "textarea":
        return True
    if maxlen and maxlen >= 300:
        return True
    return ftype == "text" and bool(NARRATIVE.search(label)) and not re.search(r"title|name\b", label, re.I)
