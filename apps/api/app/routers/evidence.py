"""Evidence engine API: judge a submission against real patents and literature (see app/evidence)."""

from __future__ import annotations

from fastapi import APIRouter

from ..evidence import chem, trl
from ..evidence.engine import REGISTRY, assess
from ..evidence.models import EvidenceReport, Submission

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/sources")
def sources() -> dict:
    """Which sources are configured, and what is missing - shown before a researcher runs an assessment."""
    out = []
    for name, cls in REGISTRY.items():
        src = cls()
        ok, why = src.configured()
        out.append({"source": name, "kind": src.kind, "configured": ok, "detail": why})
    return {"sources": out, "vocab_version": chem.VOCAB_VERSION, "trl_rubric": trl.RUBRIC_VERSION}


@router.post("/assess", response_model=EvidenceReport)
def assess_submission(sub: Submission) -> EvidenceReport:
    return assess(sub)
