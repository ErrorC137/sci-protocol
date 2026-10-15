"""Orchestrates the three matching stages. Explanations are a separate call so ranked results render
instantly and the (slower) LLM text streams in after - and so the browser can re-rank locally with
private keywords first and ask to explain its own top 10."""

from __future__ import annotations

from ..db.base import Scored, Store
from ..embed import get_embedder
from ..models.schemas import Explanation, MatchResponse, MatchResult, ProjectProfile, Unlock
from ..models.taxonomy import COUNTRIES
from ..score import trl as trl_score
from . import explain as explainer
from . import filters, ranker


def _template_for(store: Store, form_url: str | None):
    return store.get_template_by_url(form_url) if form_url else None


def _normalized(eligible: list[Scored]) -> dict[str, float]:
    """Min-max normalise cosine across the eligible set so the 0.45 similarity weight discriminates,
    whatever the embedder's absolute cosine range (local hashing vs. Voyage differ a lot)."""
    if not eligible:
        return {}
    sims = [s.similarity for s in eligible]
    lo, hi = min(sims), max(sims)
    span = hi - lo
    return {s.grant.id: ((s.similarity - lo) / span if span > 1e-9 else 0.5) for s in eligible}


def _unlocks(store: Store, profile: ProjectProfile, pvec: list[float], eligible_ids: set[str]) -> list[Unlock]:
    """What-if analysis on the hard filters only: which single change to the profile opens the most doors."""
    variants: list[tuple[str, str, ProjectProfile]] = []
    if not profile.has_entity:
        variants.append(("incorporate", "Register a company (startup)",
                         profile.model_copy(update={"applicant_type": "startup", "has_entity": True})))
    if profile.applicant_type != "individual":
        variants.append(("as_individual", "Apply as an individual researcher",
                         profile.model_copy(update={"applicant_type": "individual"})))
    for step in (1, 2):
        if profile.trl + step <= 9:
            variants.append((f"trl_{profile.trl + step}", f"Reach TRL {profile.trl + step}",
                             profile.model_copy(update={"trl": profile.trl + step})))
    if "no_equity" in profile.constraints:
        variants.append(("allow_equity", "Accept equity investment",
                         profile.model_copy(update={"constraints": [c for c in profile.constraints if c != "no_equity"]})))
    out = []
    for change, label, variant in variants:
        newly, _ = store.split_for_match(variant, pvec)
        gained = [s.grant for s in newly if s.grant.id not in eligible_ids and filters.is_eligible(filters.evaluate(s.grant, variant))]
        if gained:
            out.append(Unlock(change=change, label=label, count=len(gained), examples=[g.title for g in gained[:4]]))
    return sorted(out, key=lambda u: -u.count)


def run(store: Store, profile: ProjectProfile, limit: int = 50) -> MatchResponse:
    pvec = get_embedder().embed([profile.embedding_text()], kind="query")[0]
    prefiltered, rest = store.split_for_match(profile, pvec)

    eligible: list[tuple[Scored, list]] = []
    for s in prefiltered:
        rules = filters.evaluate(s.grant, profile)
        if filters.is_eligible(rules):
            eligible.append((s, rules))
        else:
            rest.append(s.grant)  # Python rules are authoritative over the SQL prefilter
    norm = _normalized([s for s, _ in eligible])
    local_currency = COUNTRIES.get(profile.country, ("", None))[1]

    matches: list[MatchResult] = []
    for s, rules in eligible:
        g = s.grant
        effort = ranker.estimate_effort(g, _template_for(store, g.form_url))
        effort["prefill_available"] = effort["prefill_available"] or bool(g.form_url)
        warnings = [f"Unconfirmed: {r.detail}" for r in rules
                    if r.status == "unknown" and r.rule in ("deadline", "country", "applicant_type")]
        if not g.verified:
            warnings.append("Curated entry - verify details on the funder's site before applying")
        if "local_currency" in profile.constraints and g.currency and g.currency != local_currency:
            warnings.append(f"Pays in {g.currency}, not your local currency")
        if g.ip_assignment_required:
            warnings.append("Requires assigning or licensing IP to the funder - review terms with your tech-transfer office")
        matches.append(MatchResult(
            grant=g, eligible=True, rules=rules, score=ranker.score(profile, g, norm[g.id]),
            days_left=ranker.days_left(g), effort=effort, warnings=warnings,
        ))
    matches.sort(key=lambda m: -(m.score.total if m.score else 0))

    excluded_by_rule: dict[str, int] = {}
    near: list[MatchResult] = []
    for g in rest:
        rules = filters.evaluate(g, profile)
        failed = filters.failed(rules)
        for r in failed:
            excluded_by_rule[r] = excluded_by_rule.get(r, 0) + 1
        if len(failed) != 1:
            continue
        # Only misses the researcher could act on: a higher TRL is reachable, a lower one isn't.
        if failed[0] == "trl" and not (g.trl_min and profile.trl < g.trl_min):
            continue
        if failed[0] in NEAR_MISS_ORDER:
            near.append(MatchResult(grant=g, eligible=False, rules=rules, days_left=ranker.days_left(g)))
    near.sort(key=lambda m: NEAR_MISS_ORDER[filters.failed(m.rules)[0]])

    return MatchResponse(
        matches=matches[:limit],
        excluded_count=len(rest),
        excluded_by_rule=dict(sorted(excluded_by_rule.items(), key=lambda kv: -kv[1])),
        near_misses=near[:12],
        unlocks=_unlocks(store, profile, pvec, {m.grant.id for m in matches}),
        trl_assessment=trl_score.assess(profile.trl, profile.evidence),
        corpus_size=store.count(),
        embedder=get_embedder().name,
    )


NEAR_MISS_ORDER = {"trl": 0, "incorporation": 1, "applicant_type": 2, "equity": 3, "amount": 4}


def explain(store: Store, profile: ProjectProfile, grant_ids: list[str], k: int) -> dict[str, Explanation]:
    """Explain specific (already-eligible) grants - the client's own top-k after local re-ranking."""
    pvec = get_embedder().embed([profile.embedding_text()], kind="query")[0]
    prefiltered, _ = store.split_for_match(profile, pvec)
    norm = _normalized(prefiltered)
    by_id = {s.grant.id: s for s in prefiltered}
    picked: list[MatchResult] = []
    for gid in grant_ids[:k]:
        s = by_id.get(gid)
        if not s:
            continue  # never explain something the rules excluded
        rules = filters.evaluate(s.grant, profile)
        if not filters.is_eligible(rules):
            continue
        picked.append(MatchResult(grant=s.grant, eligible=True, rules=rules, score=ranker.score(profile, s.grant, norm[gid])))
    return explainer.explain(profile, picked)
