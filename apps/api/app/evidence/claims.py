"""Patent-claim parsing that survives chemistry: 'LiNi0.8Mn0.1Co0.1O2', '1.5 M', '70-90 °C', 'claim 1 or 2'.

Claims are found by sequential numbering ('1.' then '2.' ...) at a boundary and followed by a capital
letter, so decimals inside formulas never start a new claim. Dependency comes from references such as
'of claim 3', 'according to any one of claims 1 to 4', 'as claimed in claim 1'. Independent claims are
split into elements on the transition ('comprising', 'consisting of', 'characterised in that') and on
';' / line breaks / '(a) (b)' markers. Element text is always a verbatim slice of the claim.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_DEP = re.compile(
    r"\b(?:of|in|to|by|from|with|according\s+to|as\s+(?:claimed|defined|recited|set\s+forth|described)\s+in)\s+"
    r"(?:any\s+(?:one\s+)?of\s+(?:the\s+)?(?:preceding\s+)?)?claims?\s+(\d+)", re.I)
_TRANSITION = re.compile(r"\b(comprising|comprises|consisting\s+(?:essentially\s+)?of|characteri[sz]ed\s+(?:in\s+that|by)|including|wherein)\b\s*:?", re.I)
_SPLIT = re.compile(r";\s*(?:and\s+)?|\n+|(?<=[.:,])\s+(?=\([a-z0-9ivx]{1,4}\)\s)", re.I)


@dataclass
class Claim:
    number: int
    text: str
    depends_on: int | None = None
    elements: list[str] = field(default_factory=list)

    @property
    def independent(self) -> bool:
        return self.depends_on is None


def split_claims(text: str | list[str]) -> list[Claim]:
    if isinstance(text, list):  # sources that already return one string per claim
        text = "\n".join(text)
    text = text.replace("\r", "")
    starts, expect, pos = [], 1, 0
    while True:
        m = re.compile(rf"(?:^|(?<=[\s.;]))({expect})\s*[.)]\s+(?=[A-Z(])", re.M).search(text, pos)
        if not m:
            break
        starts.append((expect, m.start(1), m.end()))
        pos, expect = m.end(), expect + 1
    claims = []
    for i, (num, _s, body_start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        body = re.sub(r"[ \t]+", " ", text[body_start:end]).strip()
        dep = _DEP.search(body[:250])
        claims.append(Claim(num, body, int(dep.group(1)) if dep and int(dep.group(1)) < num else None))
    if not claims and text.strip():  # unnumbered single claim
        claims.append(Claim(1, re.sub(r"\s+", " ", text).strip()))
    for c in claims:
        if c.independent:
            c.elements = elements_of(c.text)
    return claims


def elements_of(claim: str) -> list[str]:
    """Preamble (when it carries substance) + body elements, each a verbatim slice of the claim."""
    m = _TRANSITION.search(claim)
    pre, body = (claim[: m.start()], claim[m.end():]) if m else ("", claim)
    out = []
    pre = pre.strip(" ,:;")
    if len(re.findall(r"[A-Za-z]{4,}", pre)) >= 4:  # 'A method for regenerating a spent NMC cathode' - limiting
        out.append(pre)
    parts = re.split(r",?\s*characteri[sz]ed\s+(?:in\s+that|by)\s*", body, flags=re.I)
    if ";" not in body and "\n" not in body.strip():
        # comma-separated element lists (common in EP claims): split before a new 'a/an/means ...' item
        parts = [x for p in parts for x in re.split(r",\s*(?:and\s+)?(?=(?:a|an|means|one or more|at least one|two|said)\b)", p)]
    for part in (x for p in parts for x in _SPLIT.split(p)):
        part = re.sub(r"^\s*(?:\(?[a-z0-9ivx]{1,4}\)|and)\s+", "", part.strip(), flags=re.I).strip(" ,;:.")
        for sub in re.split(r",?\s+wherein\s+", part):
            sub = sub.strip(" ,;:.")
            if len(re.findall(r"[A-Za-z0-9]{2,}", sub)) >= 3:
                out.append(sub)
    return out
