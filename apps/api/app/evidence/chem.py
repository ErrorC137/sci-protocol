"""Battery-chemistry vocabulary: one canonical id per material / process so that 'NCM523',
'NMC532' and 'LiNi0.5Mn0.3Co0.2O2' match each other, plus quantity extraction (°C, M, wt%, h, g/L ...)
for numeric-range comparison between a submission and prior art.

The synonym table is a starting point written for this engine; extend it with a battery practitioner
(the battery-materials-scientist subagent role) and keep it versioned (VOCAB_VERSION).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

VOCAB_VERSION = "battery-vocab-0.1"

# canonical id -> surface forms (case-insensitive). Query expansion uses the first few forms.
CONCEPTS: dict[str, list[str]] = {
    "nmc": ["NMC", "NCM", "nickel manganese cobalt oxide", "lithium nickel manganese cobalt oxide"],
    "nca": ["NCA", "lithium nickel cobalt aluminium oxide", "lithium nickel cobalt aluminum oxide"],
    "lfp": ["LFP", "LiFePO4", "lithium iron phosphate"],
    "lmfp": ["LMFP", "lithium manganese iron phosphate"],
    "lco": ["LCO", "LiCoO2", "lithium cobalt oxide"],
    "lmo": ["LMO", "LiMn2O4", "lithium manganese oxide"],
    "black_mass": ["black mass", "electrode powder", "cathode powder"],
    "spent_lib": ["spent lithium-ion batteries", "spent lithium ion batteries", "spent LIBs", "end-of-life batteries",
                  "end-of-life lithium-ion batteries", "waste lithium-ion batteries", "retired batteries"],
    "hydrometallurgy": ["hydrometallurgy", "hydrometallurgical", "acid leaching", "leaching", "leached", "leachate"],
    "pyrometallurgy": ["pyrometallurgy", "pyrometallurgical", "smelting"],
    "direct_recycling": ["direct recycling", "direct regeneration", "cathode regeneration", "cathode-to-cathode",
                         "upcycling", "upcycled", "regenerated cathode"],
    "relithiation": ["relithiation", "re-lithiation", "relithiated", "re-lithiated", "lithium replenishment"],
    "solvent_extraction": ["solvent extraction", "Cyanex 272", "D2EHPA", "PC88A"],
    "precipitation": ["co-precipitation", "coprecipitation", "precipitation"],
    "sulfuric_acid": ["H2SO4", "sulfuric acid", "sulphuric acid"],
    "hydrogen_peroxide": ["H2O2", "hydrogen peroxide"],
    "organic_acid": ["citric acid", "malic acid", "oxalic acid", "lactic acid", "formic acid", "acetic acid"],
    "des": ["deep eutectic solvent", "deep eutectic solvents"],
    "li2co3": ["Li2CO3", "lithium carbonate"],
    "lioh": ["LiOH", "lithium hydroxide"],
    "pcam": ["pCAM", "precursor cathode active material", "hydroxide precursor"],
    "single_crystal": ["single-crystal", "single crystal", "monocrystalline"],
    "graphite": ["spent graphite", "graphite anode", "anode graphite"],
    "calcination": ["calcination", "calcined", "sintering", "solid-state synthesis", "annealing"],
    "hydrothermal": ["hydrothermal", "hydrothermally", "solvothermal"],
    "coin_cell": ["coin cell", "coin-cell", "CR2032", "half cell", "half-cell"],
    "pouch_cell": ["pouch cell", "pouch-cell", "pouch full cell"],
}

_FORMS = sorted(((f, cid) for cid, forms in CONCEPTS.items() for f in forms), key=lambda x: -len(x[0]))
_FORM_RE = re.compile("|".join(rf"(?<![A-Za-z0-9]){re.escape(f)}(?![a-z0-9])" for f, _ in _FORMS), re.I)
_FORM_ID = {f.lower(): cid for f, cid in _FORMS}

# NMC / NCM shorthand: NCM523 = Ni5 Co2 Mn3 -> canonical nmc532 (Ni-Mn-Co order)
_SHORT = re.compile(r"(?<![A-Za-z])(NMC|NCM)\s?-?(\d)(\d)(\d)(?!\d)", re.I)
_NUM = r"(\d+(?:\.\d+)?(?:/\d+)?)"
# LiNi0.8Mn0.1Co0.1O2 | LiNi1/3Mn1/3Co1/3O2 | Li[Ni0.6Co0.2Mn0.2]O2 (either order of Mn/Co)
_FORMULA = re.compile(
    rf"Li(?:\d+(?:\.\d+)?)?\[?Ni{_NUM}(?:Mn{_NUM}Co{_NUM}|Co{_NUM}Mn{_NUM})\]?O2", re.I
)


def _tenths(x: str) -> int:
    v = float(Fraction(x)) if "/" in x else float(x)
    return round(v * 10)


def nmc_ids(text: str) -> set[str]:
    out = set()
    for m in _SHORT.finditer(text):
        a, b, c = m.group(2), m.group(3), m.group(4)
        out.add(f"nmc{a}{b}{c}" if m.group(1).upper() == "NMC" else f"nmc{a}{c}{b}")
    for m in _FORMULA.finditer(text):
        ni = m.group(1)
        mn, co = (m.group(2), m.group(3)) if m.group(2) else (m.group(5), m.group(4))
        t = [_tenths(ni), _tenths(mn), _tenths(co)]
        if t[0] == t[1] == t[2]:
            out.add("nmc111")  # LiNi1/3Mn1/3Co1/3O2
        elif all(0 <= x <= 9 for x in t):
            out.add("nmc" + "".join(str(x) for x in t))
    return out


def concepts(text: str) -> set[str]:
    """Canonical concept ids present in text (generic 'nmc' plus stoichiometry-specific 'nmc811')."""
    found = {_FORM_ID[m.group(0).lower()] for m in _FORM_RE.finditer(text or "")}
    specific = nmc_ids(text or "")
    return found | specific | ({"nmc"} if specific else set())


def expansions(cid: str, n: int = 2) -> list[str]:
    if cid.startswith("nmc") and len(cid) == 6:
        return [f"NMC{cid[3:]}", f"NCM{cid[3]}{cid[5]}{cid[4]}"][:n]
    return CONCEPTS.get(cid, [])[:n]


# --- quantities ------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Qty:
    lo: float
    hi: float
    unit: str  # canonical: C, M, wt%, vol%, g/L, h, min, pH, V, mAh/g, %
    text: str

    def overlaps(self, other: Qty) -> bool:
        return self.unit == other.unit and self.lo <= other.hi and other.lo <= self.hi


_UNITS = {
    "°c": "C", "ºc": "C", "℃": "C", "degc": "C", "deg c": "C", "degrees celsius": "C", "oc": "C",
    "m": "M", "mol/l": "M", "mol l-1": "M", "mol·l-1": "M", "mol/dm3": "M",
    "wt%": "wt%", "wt.%": "wt%", "wt %": "wt%", "vol%": "vol%", "vol.%": "vol%", "v/v%": "vol%",
    "g/l": "g/L", "g l-1": "g/L", "g·l-1": "g/L", "h": "h", "hr": "h", "hrs": "h", "hours": "h", "hour": "h",
    "min": "min", "mins": "min", "minutes": "min", "v": "V", "mah/g": "mAh/g", "mah g-1": "mAh/g", "mah·g-1": "mAh/g",
    "%": "%",
}
_UNIT_RE = "|".join(sorted((re.escape(u) for u in _UNITS), key=len, reverse=True))
_RANGE = re.compile(
    rf"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:(?:-|–|—|~|to)\s*(\d+(?:\.\d+)?))?\s*({_UNIT_RE})(?![A-Za-z])", re.I
)
_PH = re.compile(r"\bpH\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:(?:-|–|to)\s*(\d+(?:\.\d+)?))?", re.I)


def quantities(text: str) -> list[Qty]:
    out = []
    for m in _RANGE.finditer(text or ""):
        unit = _UNITS.get(m.group(3).lower().replace("  ", " "))
        if unit is None:
            continue
        if unit == "M" and m.group(3) == "m":  # lower-case 'm' is metres / milli-, not molar
            continue
        lo = float(m.group(1))
        hi = float(m.group(2)) if m.group(2) else lo
        out.append(Qty(min(lo, hi), max(lo, hi), unit, m.group(0).strip()))
    for m in _PH.finditer(text or ""):
        lo = float(m.group(1))
        hi = float(m.group(2)) if m.group(2) else lo
        out.append(Qty(min(lo, hi), max(lo, hi), "pH", m.group(0).strip()))
    return out


def numeric_overlaps(a: str, b: str) -> list[tuple[Qty, Qty]]:
    """Pairs of same-unit quantities whose ranges overlap. A flag for review, not a legal conclusion:
    whether a disclosed value anticipates a claimed range is jurisdiction-specific law."""
    qb = quantities(b)
    return [(x, y) for x in quantities(a) for y in qb if x.overlaps(y)]


# --- tokens for lexical matching -------------------------------------------------------------------
_STOP = set("""a an and are as at be been by for from has have in into is it its of on or that the this to with
within wherein which whereby said thereof therein such than then those these each least one more step steps method
process comprising comprises comprise consisting including include includes using used use via per about approximately
between further first second third may can were was then also""".split())


def stem(w: str) -> str:
    """Light suffix stripping so 'relithiating' / 'relithiated' / 'relithiation' meet at 'relithiat'."""
    for suf in ("ations", "ation", "ating", "ated", "ing", "ers", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4 and not (suf == "s" and w.endswith("ss")):
            return w[: -len(suf)]
    return w


def words(text: str) -> set[str]:
    t = _FORMULA.sub(" ", _SHORT.sub(" ", text or ""))  # formulas are represented by concept ids instead
    return {stem(w) for w in re.findall(r"[a-z][a-z0-9\-]{3,}", t.lower()) if w not in _STOP}


def tokens(text: str) -> set[str]:
    """Content tokens + concept ids + normalised quantities, for coverage-style lexical matching."""
    t = text or ""
    return words(t) | {f"#{c}" for c in concepts(t)} | {f"{q.lo:g}{q.unit}" for q in quantities(t)}


def coverage(element: str, passage: str) -> float:
    """Share of the element's terms found in the passage; a quantity counts as found when the passage
    has an overlapping range in the same unit (180-240 °C is matched by 220 °C)."""
    et = words(element) | {f"#{c}" for c in concepts(element)}
    pt = words(passage) | {f"#{c}" for c in concepts(passage)}
    eq, pq = quantities(element), quantities(passage)
    hit = len(et & pt) + sum(1 for q in eq if any(q.overlaps(x) for x in pq))
    return hit / max(1, len(et) + len(eq))


_SENT_END = re.compile(r"(?<=[.!?;])\s+(?=[A-Z(\[])|\n+")


def sentence_spans(text: str, min_len: int = 12) -> list[tuple[int, int]]:
    """(start, end) offsets of sentences, so quotes can be cut verbatim from the source text."""
    spans, start = [], 0
    for m in _SENT_END.finditer(text or ""):
        if m.start() - start >= min_len:
            spans.append((start, m.start()))
        start = m.end()
    if len(text or "") - start >= min_len:
        spans.append((start, len(text)))
    return spans


def sentences(text: str, min_len: int = 12) -> list[str]:
    return [text[a:b].strip() for a, b in sentence_spans(text, min_len)]
