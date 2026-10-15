"""Health, taxonomy, grant discovery and matching."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .. import llm
from ..chain import indexer
from ..config import settings
from ..db.base import GrantQuery
from ..deps import get_store
from ..embed import get_embedder
from ..match import service as match_service
from ..models import taxonomy
from ..models.schemas import Explanation, Grant, MatchResponse, ProjectProfile
from ..score import trl as trl_score

router = APIRouter()


@router.get("/health")
def health() -> dict:
    store = get_store()
    ix = indexer.get_indexer()
    return {
        "status": "ok",
        "store": store.kind,
        "corpus_size": store.count(),
        "sources": store.sources(),
        "embedder": get_embedder().name,
        "llm": {"enabled": llm.enabled(), "model": settings.llm_model if llm.enabled() else None},
        "ipfs": "pinata" if settings.pinata_jwt else "local",
        "chain": {"chain_id": settings.chain_id, "deployment": indexer.load_deployment() is not None},
        "indexer": None if ix is None else {"next_block": ix.next_block, "events": len(ix.events), "error": ix.last_error},
    }


@router.get("/meta/taxonomy")
def get_taxonomy() -> dict:
    return taxonomy.as_dict()


class TRLCheck(BaseModel):
    trl: int = Field(ge=1, le=9)
    evidence: list[str] = []


@router.post("/meta/trl-check")
def trl_check(body: TRLCheck) -> dict:
    return trl_score.assess(body.trl, body.evidence)


class GrantHit(BaseModel):
    grant: Grant
    similarity: float


class GrantPage(BaseModel):
    items: list[GrantHit]
    total: int


@router.get("/grants", response_model=GrantPage)
def list_grants(
    q: str | None = Query(None, max_length=200),
    field: list[str] = Query(default=[]),
    country: str | None = None,
    applicant_type: str | None = None,
    trl: int | None = Query(None, ge=1, le=9),
    source: str | None = None,
    funder_type: str | None = None,
    no_equity: bool = False,
    include_closed: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> GrantPage:
    qvec = get_embedder().embed([q], kind="query")[0] if q else None
    items, total = get_store().search(
        GrantQuery(q=q, fields=field, country=country.upper() if country else None, applicant_type=applicant_type,
                   trl=trl, source=source, funder_type=funder_type, no_equity=no_equity,
                   include_closed=include_closed, limit=limit, offset=offset),
        qvec,
    )
    return GrantPage(items=[GrantHit(grant=s.grant, similarity=round(s.similarity, 4)) for s in items], total=total)


@router.get("/grants/{grant_id}", response_model=Grant)
def get_grant(grant_id: str) -> Grant:
    g = get_store().get_grant(grant_id)
    if not g:
        raise HTTPException(404, "grant not found")
    return g


class MatchRequest(BaseModel):
    profile: ProjectProfile
    limit: int = Field(50, ge=1, le=200)


@router.post("/match", response_model=MatchResponse)
def match(body: MatchRequest) -> MatchResponse:
    return match_service.run(get_store(), body.profile, body.limit)


class ExplainRequest(BaseModel):
    profile: ProjectProfile
    grant_ids: list[str] = Field(min_length=1, max_length=25)


class ExplainResponse(BaseModel):
    explanations: dict[str, Explanation]
    llm: bool


@router.post("/match/explain", response_model=ExplainResponse)
def explain(body: ExplainRequest) -> ExplainResponse:
    out = match_service.explain(get_store(), body.profile, body.grant_ids, settings.explain_top_k)
    return ExplainResponse(explanations=out, llm=any(e.source == "llm" for e in out.values()))
