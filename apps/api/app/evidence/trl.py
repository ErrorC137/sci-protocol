"""TRL from evidence for battery upcycling (track A) and recycling processes (track B).

Deterministic: a level counts only when a cue for it is found in the submission text, quoted, and not
phrased as future work. The model never assigns a level (MatDAO's keyword TRL scored a coin-cell paper
TRL 9 because it mentioned 'manufacturing'; here 'manufacturing cost' matches nothing).

RUBRIC_VERSION battery-trl-0.1 is a proposal: have a battery practitioner review the cues and the
required evidence per level, and version every change.
"""

from __future__ import annotations

import re

from . import chem
from .models import TRLAssessment, TRLEvidence

RUBRIC_VERSION = "battery-trl-0.1"

# (level, cue name, regex). Order within a level does not matter.
TRACK_A = [  # upcycling / regenerated cathode materials
    (2, "computational or conceptual only", r"\b(?:DFT|first[- ]principles|density functional|simulat\w+|computational screening|we propose)\b"),
    (3, "material synthesised and characterised", r"\b(?:XRD|X-ray diffraction|Rietveld|SEM|TEM)\b.{0,80}\b(?:regenerat|relithiat|upcycl|synthes)\w*|\b(?:regenerat|relithiat|upcycl)\w*.{0,120}\b(?:XRD|X-ray diffraction|Rietveld)\b"),
    (4, "coin / half-cell electrochemical validation", r"\b(?:coin[- ]cells?|half[- ]cells?|CR20\d\d)\b"),
    (5, "full or pouch cell, or kg-scale material", r"\b(?:pouch[- ]cells?|full[- ]cells?|kg[- ]scale|kilogram[- ]scale|\d+\s*kg\s+(?:of\s+)?(?:regenerated|cathode|material))\b"),
    (6, "Ah-scale multilayer cells or pilot line", r"\b(?:multi-?layer pouch|\d+(?:\.\d+)?\s*Ah\b|pilot[- ](?:line|scale|plant)|kg\s*/\s*day|kg per day)"),
    (7, "customer sample / qualification", r"\b(?:customer samples?|sampl\w+ (?:to|with) (?:a )?(?:cell maker|OEM|customer)|qualification (?:by|with|at)|OEM (?:testing|evaluation))\b"),
    (8, "qualified, supply agreement", r"\b(?:qualified by|supply agreement|offtake agreement|purchase order)\b"),
    (9, "commercial production", r"\b(?:commercial production|mass production|in commercial (?:use|products?))\b"),
]
TRACK_B = [  # recycling process / plant
    (3, "bench leaching with recovery data", r"\b(?:leach\w*|recover\w*)\b.{0,100}\b\d+(?:\.\d+)?\s*%|\b\d+(?:\.\d+)?\s*%.{0,60}\b(?:leach\w*|recover\w*)"),
    (4, "bench flowsheet with assays", r"\b(?:flow ?sheet|mass balance|ICP-(?:OES|MS|AES)|bench[- ]scale)\b"),
    (5, "real industrial feedstock", r"\b(?:industrial black mass|real black mass|black mass (?:supplied|obtained|provided|sourced) (?:by|from)|commercial black mass|spent (?:EV|electric vehicle) (?:batteries|packs))\b"),
    (6, "pilot plant / battery-grade product", r"\b(?:pilot[- ](?:plant|scale|line)|kg\s*/\s*(?:day|h)|kg per (?:day|hour)|battery[- ]grade)\b"),
    (7, "demonstration plant / permitting", r"\b(?:demonstration plant|demo plant|t\s*/\s*day|tonnes? per day|permit application|environmental impact assessment|EIA)\b"),
    (8, "permitted commercial plant / offtake", r"\b(?:commercial plant|offtake (?:agreement|contract)|factory licen[cs]e|operating permit|\d[\d,]*\s*(?:t|tonnes?)\s*(?:/|per)\s*(?:yr|year|annum))\b"),
    (9, "sustained audited operation", r"\b(?:in (?:commercial )?operation since|audited (?:annual )?throughput|annual throughput)\b"),
]
NEXT = {
    "A_upcycling_materials": {
        3: "Synthesise the regenerated material and confirm phase/structure (XRD, Rietveld) and composition (ICP).",
        4: "Coin-cell testing at stated C-rates over a meaningful number of cycles, reproduced across batches.",
        5: "kg-scale batch and full/pouch cells against a commercial counter-electrode.",
        6: "Ah-scale multilayer pouch cells under a realistic protocol; pilot-line production.",
        7: "Customer or cell-maker sample qualification.",
        8: "Qualification by a cell maker and a supply agreement.",
        9: "Material in commercial products.",
    },
    "B_recycling_process": {
        4: "Bench flowsheet with a closed mass balance; recoveries and purities by ICP-OES/MS.",
        5: "Integrated bench runs on real industrial black mass with an assay of the feed.",
        6: "Pilot at kg/day producing a battery-grade product against a written spec.",
        7: "Demonstration plant at t/day; permits applied for.",
        8: "Permitted commercial plant with an offtake contract and audited throughput.",
        9: "Sustained operation with audited annual throughput and recovery reporting.",
    },
}
_A_DOMAIN = re.compile(r"\b(?:cathode|anode|capacity|mAh|coin|pouch|cycl\w+|relithiat\w*|regenerat\w*|upcycl\w*|C-rate|electrochemical)", re.I)
_B_DOMAIN = re.compile(r"\b(?:leach\w*|black mass|recover\w*|plant|throughput|hydrometallurg\w*|pyrometallurg\w*|solvent extraction|precipitat\w*|smelt\w*|shredd\w*|feedstock)", re.I)
_PLANNED = re.compile(r"\b(?:will|plan(?:s|ned)?|aim(?:s|ed)? to|intend\w*|future|next (?:step|phase)|propos\w+ to|to be (?:built|tested|scaled)|expected to|would|could|seek\w* to)\b", re.I)


def _sentences(text: str) -> list[str]:
    return chem.sentences(text, min_len=1)


def _scan(text: str, rubric) -> list[TRLEvidence]:
    out = []
    for s in _sentences(text):
        for level, cue, rx in rubric:
            m = re.search(rx, s, re.I)
            if m:
                out.append(TRLEvidence(level=level, cue=cue, quote=s[:400], achieved=not _PLANNED.search(s)))
    return out


def assess(text: str) -> TRLAssessment:
    a, b = _scan(text, TRACK_A), _scan(text, TRACK_B)
    best = lambda ev: max((e.level for e in ev if e.achieved), default=0)  # noqa: E731
    if not a and not b:
        return TRLAssessment(track="unknown", rubric_version=RUBRIC_VERSION, low=None, high=None,
                             note="No TRL evidence found in the text provided. Add methods/results text (scale, cells, feedstock).")
    # Which kind of work is this? Decided by domain vocabulary, not by which track happens to score higher.
    da = len(_A_DOMAIN.findall(text))
    db = len(_B_DOMAIN.findall(text))
    track, ev = ("A_upcycling_materials", a) if (da, best(a)) >= (db, best(b)) else ("B_recycling_process", b)
    other = ("B_recycling_process", b) if track.startswith("A") else ("A_upcycling_materials", a)
    achieved = sorted({e.level for e in ev if e.achieved})
    low = achieved[-1] if achieved else None
    note = (f"Rubric {RUBRIC_VERSION} (proposal, pending review by a battery practitioner). The level is the highest "
            "with a quoted, achieved cue; planned work is listed but not counted. Quotes are the applicant's own text: "
            "levels of 7 and above should be confirmed by third-party documents or on-chain attestations.")
    high = low
    if low and len(achieved) == 1 and low >= 5:
        note += " Only one cue supports this level and no lower-level evidence was found: confirm with documents."
    if low and (prev := [x for x in achieved if x < low]) and low - prev[-1] > 2:
        note += f" Gap: no evidence between TRL {prev[-1]} and TRL {low}."
    if best(other[1]):
        note += f" The text also has {other[0].split('_', 1)[1].replace('_', ' ')} evidence up to TRL {best(other[1])}."
    nxt = [v for k, v in NEXT[track].items() if k > (low or 0)][:2]
    return TRLAssessment(track=track, rubric_version=RUBRIC_VERSION, low=low, high=high,
                         evidence=sorted(ev, key=lambda e: (-e.level, not e.achieved)), next_milestones=nxt, note=note)
