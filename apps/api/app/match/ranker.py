"""Stage 2: hybrid ranking over grants that already passed the hard filters (brief §4.2).

    score = 0.45 * cosine(project, grant)
          + 0.20 * field_overlap_jaccard
          + 0.15 * trl_centering          # closer to band midpoint = better
          + 0.10 * amount_fit
          + 0.10 * deadline_feasibility   # penalize <14 days out
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models.schemas import FormTemplate, Grant, ProjectProfile, ScoreBreakdown

W_SIM, W_FIELD, W_TRL, W_AMOUNT, W_DEADLINE = 0.45, 0.20, 0.15, 0.10, 0.10
NEUTRAL = 0.5  # used when the source didn't state the criterion


def field_overlap(p: ProjectProfile, g: Grant) -> float:
    if not g.fields:
        return NEUTRAL  # field-agnostic program
    a, b = set(p.fields), set(g.fields)
    jac = len(a & b) / len(a | b)
    # Sub-domain hits are a stronger signal than top-level field overlap alone.
    subs = set(g.raw.get("subdomains") or [])
    if subs and set(p.subdomains) & subs:
        jac = min(1.0, jac + 0.25)
    return jac


def trl_centering(p: ProjectProfile, g: Grant) -> float:
    if g.trl_min is None and g.trl_max is None:
        return NEUTRAL
    lo, hi = g.trl_min or 1, g.trl_max or 9
    mid, half = (lo + hi) / 2, (hi - lo) / 2
    return max(0.0, 1.0 - abs(p.trl - mid) / (half + 1))


def amount_fit(p: ProjectProfile, g: Grant) -> float:
    if g.amount_min_usd is None and g.amount_max_usd is None:
        return NEUTRAL
    lo = g.amount_min_usd or 0.0
    hi = g.amount_max_usd if g.amount_max_usd is not None else max(p.funding_max_usd, lo) * 2
    need_lo, need_hi = p.funding_min_usd, p.funding_max_usd
    if need_hi == need_lo:
        return 1.0 if lo <= need_lo <= hi else 0.0
    overlap = max(0.0, min(hi, need_hi) - max(lo, need_lo))
    return overlap / (need_hi - need_lo)


def days_left(g: Grant, now: datetime | None = None) -> int | None:
    if g.rolling or g.deadline is None:
        return None
    now = now or datetime.now(timezone.utc)
    return (g.deadline - now).days


def deadline_feasibility(g: Grant, now: datetime | None = None) -> float:
    if g.rolling:
        return 1.0
    d = days_left(g, now)
    if d is None:
        return NEUTRAL
    if d < 14:
        return 0.2
    if d < 30:
        return 0.7
    return 1.0


def score(p: ProjectProfile, g: Grant, similarity: float, now: datetime | None = None) -> ScoreBreakdown:
    sim = max(0.0, min(1.0, similarity))
    parts = {
        "similarity": sim,
        "field_overlap": field_overlap(p, g),
        "trl_centering": trl_centering(p, g),
        "amount_fit": amount_fit(p, g),
        "deadline_feasibility": deadline_feasibility(g, now),
    }
    total = (
        W_SIM * parts["similarity"]
        + W_FIELD * parts["field_overlap"]
        + W_TRL * parts["trl_centering"]
        + W_AMOUNT * parts["amount_fit"]
        + W_DEADLINE * parts["deadline_feasibility"]
    )
    return ScoreBreakdown(**{k: round(v, 4) for k, v in parts.items()}, total=round(total, 4))


_MODE_HOURS = {"email": (1, 3), "web_form": (2, 6), "pdf_form": (4, 10), "portal": (8, 20)}


def estimate_effort(g: Grant, template: FormTemplate | None) -> dict:
    """Derived from the cached form's field count when we have it; otherwise from application mode."""
    if template:
        n = len(template.fields)
        narrative = sum(1 for f in template.fields if f.narrative)
        lo = round(0.5 + n * 0.03 + narrative * 0.5, 1)
        return {"hours_low": lo, "hours_high": round(lo * 2, 1), "field_count": n, "narrative_fields": narrative,
                "basis": "form field count", "prefill_available": True}
    lo_hi = _MODE_HOURS.get(g.application_mode or "")
    if lo_hi:
        return {"hours_low": lo_hi[0], "hours_high": lo_hi[1], "basis": f"typical for {g.application_mode.replace('_', ' ')}",
                "prefill_available": False}
    return {"basis": "unknown", "prefill_available": False}
