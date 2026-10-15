"""Stage 1: hard eligibility rules. These - not the LLM, not the embedding - decide eligibility.

Each rule returns pass / fail / unknown. "unknown" means the source didn't state the criterion; it
never excludes, but is surfaced so the researcher knows to verify it. The SQL prefilter in
db/postgres.py encodes the same rules and must stay in sync (tests/test_postgres.py checks it).
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import taxonomy
from ..models.schemas import Grant, ProjectProfile, RuleResult

RULES = ["country", "applicant_type", "trl", "amount", "deadline", "incorporation", "equity", "ip"]


def _usd(x: float) -> str:
    return f"${x:,.0f}"


def evaluate(grant: Grant, p: ProjectProfile, now: datetime | None = None) -> list[RuleResult]:
    now = now or datetime.now(timezone.utc)
    out: list[RuleResult] = []
    country = taxonomy.country_name(p.country)

    # country
    ec = grant.eligible_countries
    if not ec:
        out.append(RuleResult(rule="country", status="unknown", detail="Eligible countries not stated by source - verify"))
    elif taxonomy.GLOBAL in ec:
        out.append(RuleResult(rule="country", status="pass", detail="Open to applicants worldwide"))
    elif p.country in ec:
        out.append(RuleResult(rule="country", status="pass", detail=f"Open to applicants in {country}"))
    else:
        shown = ", ".join(ec[:6]) + ("…" if len(ec) > 6 else "")
        out.append(RuleResult(rule="country", status="fail", detail=f"Not open to {country} (eligible: {shown})"))

    # applicant type
    at = grant.applicant_types
    label = taxonomy.APPLICANT_TYPES[p.applicant_type]
    if not at:
        out.append(RuleResult(rule="applicant_type", status="unknown", detail="Applicant types not stated - verify"))
    elif p.applicant_type in at:
        out.append(RuleResult(rule="applicant_type", status="pass", detail=f"Accepts {label.lower()}"))
    else:
        out.append(
            RuleResult(rule="applicant_type", status="fail", detail=f"Does not accept {label.lower()} (accepts: {', '.join(at)})")
        )

    # TRL
    lo, hi = grant.trl_min, grant.trl_max
    if lo is None and hi is None:
        out.append(RuleResult(rule="trl", status="unknown", detail="TRL band not stated"))
    elif (lo is None or p.trl >= lo) and (hi is None or p.trl <= hi):
        out.append(RuleResult(rule="trl", status="pass", detail=f"TRL {p.trl} is within {lo or 1}-{hi or 9}"))
    elif lo is not None and p.trl < lo:
        out.append(RuleResult(rule="trl", status="fail", detail=f"Needs TRL ≥ {lo}; you are TRL {p.trl}"))
    else:
        out.append(RuleResult(rule="trl", status="fail", detail=f"For TRL ≤ {hi}; you are TRL {p.trl}"))

    # funding overlap
    gmin, gmax = grant.amount_min_usd, grant.amount_max_usd
    if gmin is None and gmax is None:
        out.append(RuleResult(rule="amount", status="unknown", detail="Award size not stated"))
    elif gmax is not None and gmax < p.funding_min_usd:
        out.append(
            RuleResult(rule="amount", status="fail", detail=f"Max award {_usd(gmax)} is below your minimum need {_usd(p.funding_min_usd)}")
        )
    elif gmin is not None and gmin > p.funding_max_usd:
        out.append(
            RuleResult(rule="amount", status="fail", detail=f"Min award {_usd(gmin)} exceeds your maximum need {_usd(p.funding_max_usd)}")
        )
    else:
        rng = f"{_usd(gmin) if gmin is not None else '?'}-{_usd(gmax) if gmax is not None else '?'}"
        out.append(RuleResult(rule="amount", status="pass", detail=f"Award range {rng} overlaps your need"))

    # deadline
    if grant.rolling:
        out.append(RuleResult(rule="deadline", status="pass", detail="Rolling / always open"))
    elif grant.deadline is None:
        note = f" ({grant.cycle_note})" if grant.cycle_note else ""
        out.append(RuleResult(rule="deadline", status="unknown", detail=f"Next deadline not confirmed{note}"))
    elif grant.deadline > now:
        out.append(RuleResult(rule="deadline", status="pass", detail=f"Closes {grant.deadline:%Y-%m-%d}"))
    else:
        out.append(RuleResult(rule="deadline", status="fail", detail=f"Closed {grant.deadline:%Y-%m-%d}"))

    # incorporation
    if grant.requires_incorporation and not p.has_entity:
        out.append(RuleResult(rule="incorporation", status="fail", detail="Requires a registered company; you have no entity"))
    elif grant.requires_incorporation is None:
        out.append(RuleResult(rule="incorporation", status="unknown", detail="Entity requirement not stated"))
    else:
        out.append(RuleResult(rule="incorporation", status="pass", detail="No entity required" if not grant.requires_incorporation else "Entity requirement met"))

    # equity
    if grant.equity_taken and "no_equity" in p.constraints:
        out.append(RuleResult(rule="equity", status="fail", detail="Takes equity; you flagged no equity"))
    elif grant.equity_taken is None:
        out.append(RuleResult(rule="equity", status="unknown", detail="Equity terms not stated"))
    else:
        out.append(RuleResult(rule="equity", status="pass", detail="Takes equity" if grant.equity_taken else "Non-dilutive"))

    # IP assignment
    if grant.ip_assignment_required and "no_ip_assignment" in p.constraints:
        out.append(RuleResult(rule="ip", status="fail", detail="Requires IP assignment; you flagged no IP assignment"))
    elif grant.ip_assignment_required:
        out.append(RuleResult(rule="ip", status="pass", detail="Requires IP assignment - check terms"))
    else:
        out.append(RuleResult(rule="ip", status="pass" if grant.ip_assignment_required is False else "unknown",
                              detail="IP stays with applicant" if grant.ip_assignment_required is False else "IP terms not stated"))
    return out


def is_eligible(rules: list[RuleResult]) -> bool:
    return all(r.status != "fail" for r in rules)


def failed(rules: list[RuleResult]) -> list[str]:
    return [r.rule for r in rules if r.status == "fail"]
