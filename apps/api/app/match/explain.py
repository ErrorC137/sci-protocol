"""Stage 3: "why this matched" + "what would strengthen this", for the top-k only (brief §4.2).

The LLM explains decisions the rules already made; it is never asked whether a grant is eligible.
One batched call covers all k grants. Without a key, a deterministic template explains instead."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict

from .. import llm
from ..config import settings
from ..models import taxonomy
from ..models.schemas import Explanation, MatchResult, ProjectProfile

SYSTEM = """You write short, factual explanations for a research-funding matching tool used by scientists.

Eligibility has ALREADY been decided by deterministic rules. You never decide, assert, or deny eligibility - you explain why an already-eligible grant ranks well for this researcher, using ONLY the profile and grant data provided.

The researcher profile is deliberately non-confidential: categories and stage only. Never ask for, guess at, or describe the researcher's method, composition, data, or invention.

For each grant:
- why_matched: exactly two sentences. Cite concrete overlaps from the data (field or sub-domain, TRL band vs. the researcher's TRL, award range vs. funding need, applicant type, deadline or rolling intake). Plain language, no hype, no exclamation marks.
- strengthen: one or two sentences of practical application advice grounded in a visible gap between profile and grant (e.g. evidence stage, an industry partner letter, co-funding, registering an entity, local-language documents). Do not invent requirements; if something must be checked, say "check the call text for ...".

If a grant is marked unverified, or its deadline/amount is unknown, say so briefly instead of presenting it as fact."""

SCHEMA = {
    "type": "object",
    "properties": {
        "explanations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "grant_id": {"type": "string"},
                    "why_matched": {"type": "string"},
                    "strengthen": {"type": "string"},
                },
                "required": ["grant_id", "why_matched", "strengthen"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["explanations"],
    "additionalProperties": False,
}

_cache: OrderedDict[str, Explanation] = OrderedDict()
_CACHE_MAX = 2000


def _key(profile: ProjectProfile, grant_id: str) -> str:
    blob = profile.model_dump_json(exclude={"nickname"}) + grant_id + settings.llm_model
    return hashlib.sha256(blob.encode()).hexdigest()


def _profile_brief(p: ProjectProfile) -> dict:
    return {
        "fields": [taxonomy.field_label(f) for f in p.fields],
        "subdomains": p.subdomains,
        "trl": p.trl,
        "evidence": [taxonomy.EVIDENCE[e]["label"] for e in p.evidence],
        "applicant_type": taxonomy.APPLICANT_TYPES[p.applicant_type],
        "country": taxonomy.country_name(p.country),
        "funding_need_usd": [p.funding_min_usd, p.funding_max_usd],
        "uses_of_funds": [taxonomy.USES_OF_FUNDS[u] for u in p.uses_of_funds],
        "months_to_next_milestone": p.months_to_milestone,
        "constraints": [taxonomy.CONSTRAINTS[c] for c in p.constraints],
    }


def _grant_brief(m: MatchResult) -> dict:
    g = m.grant
    return {
        "grant_id": g.id,
        "title": g.title,
        "funder": g.funder_name,
        "summary": (g.summary or "")[:700],
        "fields": [taxonomy.field_label(f) for f in g.fields] or ["any field"],
        "topics": g.raw.get("subdomains") or [],
        "trl_band": [g.trl_min, g.trl_max],
        "award_usd": [g.amount_min_usd, g.amount_max_usd],
        "equity_taken": g.equity_taken,
        "deadline": g.deadline.date().isoformat() if g.deadline else ("rolling" if g.rolling else "unknown"),
        "cycle": g.cycle_note,
        "verified": g.verified,
        "rule_results": {r.rule: r.detail for r in m.rules},
        "notes": g.notes,
    }


def template(p: ProjectProfile, m: MatchResult) -> Explanation:
    """Deterministic explanation built only from rule outcomes and score components."""
    g, s = m.grant, m.score
    shared = [taxonomy.field_label(f) for f in set(p.fields) & set(g.fields)]
    subs = sorted(set(p.subdomains) & set(g.raw.get("subdomains") or []))
    first = (
        f"Matches on {', '.join(subs or shared)}" if (subs or shared)
        else "This program is open across fields"
    )
    trl = next((r.detail for r in m.rules if r.rule == "trl" and r.status == "pass"), None)
    first += f", and your {trl}" if trl else ""
    first += "."
    amt = next((r.detail for r in m.rules if r.rule == "amount" and r.status == "pass"), None)
    dl = next((r.detail for r in m.rules if r.rule == "deadline"), "")
    parts = [p for p in (amt, dl) if p]
    second = "; ".join([parts[0]] + [p[0].lower() + p[1:] for p in parts[1:]]) + "." if parts else ""

    tips = []
    if s and s.trl_centering < 0.5 and g.trl_min and p.trl <= g.trl_min:
        tips.append("You sit at the low end of this call's TRL band, so lead with your strongest validation data")
    if "pilot" not in p.evidence and "prototype" not in p.evidence and (g.trl_max or 0) >= 5:
        tips.append("a prototype or pilot result would make the readiness case much stronger")
    if not g.verified:
        tips.append("check the official call text - this entry is curated and not yet verified")
    if g.equity_taken:
        tips.append("this program takes equity, so prepare a cap table")
    if not tips:
        tips.append("A short letter of support from an industry or end-user partner usually strengthens applications like this")
    strengthen = "; ".join(tips)
    strengthen = strengthen[0].upper() + strengthen[1:] + "."
    return Explanation(why_matched=f"{first} {second}".strip(), strengthen=strengthen, source="template")


def explain(p: ProjectProfile, matches: list[MatchResult]) -> dict[str, Explanation]:
    out: dict[str, Explanation] = {}
    todo: list[MatchResult] = []
    for m in matches:
        k = _key(p, m.grant.id)
        if k in _cache:
            out[m.grant.id] = _cache[k]
        else:
            todo.append(m)

    if todo and llm.enabled():
        payload = {"researcher_profile": _profile_brief(p), "grants": [_grant_brief(m) for m in todo]}
        result = llm.structured(
            system=SYSTEM,
            user="Explain each of these already-eligible matches.\n\n" + json.dumps(payload, ensure_ascii=False),
            schema=SCHEMA,
            effort="low",
        )
        by_id = {m.grant.id: m for m in todo}
        for e in (result or {}).get("explanations", []):
            if e.get("grant_id") in by_id and e.get("why_matched"):
                exp = Explanation(why_matched=e["why_matched"].strip(), strengthen=e.get("strengthen", "").strip(), source="llm")
                out[e["grant_id"]] = exp
                _cache[_key(p, e["grant_id"])] = exp

    for m in matches:
        if m.grant.id not in out:
            out[m.grant.id] = template(p, m)  # not cached: an LLM answer should replace it when available
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)
    return out
