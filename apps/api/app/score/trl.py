"""TRL readiness check: does the self-declared TRL agree with the evidence the researcher ticked?
Used on intake (a gentle warning) and to explain why early-stage projects miss later-stage calls."""

from __future__ import annotations

from ..models import taxonomy


def plausible_range(evidence: list[str]) -> tuple[int, int] | None:
    ranges = [taxonomy.EVIDENCE[e]["trl_range"] for e in evidence if e in taxonomy.EVIDENCE]
    if not ranges:
        return None
    return min(r[0] for r in ranges), max(r[1] for r in ranges)


def assess(trl: int, evidence: list[str]) -> dict:
    rng = plausible_range(evidence)
    level = taxonomy.TRL_LEVELS[trl]
    out = {"trl": trl, "name": level["name"], "plain": level["plain"], "evidence_range": list(rng) if rng else None}
    if rng is None:
        out.update(consistent=None, note="Tick the evidence you have so funders' TRL bands can be checked against it.")
    elif trl > rng[1] + 1:
        out.update(
            consistent=False,
            note=f"TRL {trl} is ahead of your evidence (which supports about TRL {rng[0]}-{rng[1]}). "
            "Reviewers will check this - claim the level your evidence supports.",
        )
    elif trl < rng[0] - 1:
        out.update(
            consistent=False,
            note=f"Your evidence suggests TRL {rng[0]}-{rng[1]}; you may be under-selling the project at TRL {trl}.",
        )
    else:
        out.update(consistent=True, note=f"Consistent with your evidence (TRL {rng[0]}-{rng[1]}).")
    return out
