"""Request / response models for the evidence engine (shape follows MatDAO's PriorArtSearch contract,
platform lib/ai-studio/types.ts, extended with dates, jurisdictions, quotes and provenance)."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

RefKind = Literal["patent", "paper", "preprint"]
SourceState = Literal["ok", "empty", "error", "no_key", "disabled", "unreachable"]
Verdict = Literal["disclosed", "partial", "absent", "unsupported"]


class Submission(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    abstract: str = Field(min_length=20, max_length=20_000)
    claims: str | None = Field(None, max_length=60_000, description="numbered claims, if a patent application exists")
    methods: str | None = Field(None, max_length=60_000, description="methods / results text used for TRL evidence")
    keywords: list[str] = Field(default_factory=list, max_length=30)
    priority_date: dt.date | None = Field(None, description="earliest filing or public disclosure; prior art must predate it")
    jurisdictions: list[str] = Field(default_factory=lambda: ["TH", "CN", "KR", "JP", "EP", "US"])
    sources: list[str] | None = Field(None, description="subset of source names; default all configured")
    confidential: bool = Field(True, description="unpublished invention: only `keywords` are sent to external search APIs")
    allow_llm: bool = Field(True, description="send the submission to the configured LLM for element extraction and judging")
    max_references: int = Field(40, ge=5, le=200)
    judge_top: int = Field(8, ge=0, le=30, description="references compared element-by-element")


class Reference(BaseModel):
    key: str  # canonical id: doi:10.x/y | pat:US11234567B2 | arxiv:2401.01234 | openalex:W123
    kind: RefKind
    source: str  # which adapter found it first
    also_in: list[str] = Field(default_factory=list)
    title: str
    abstract: str | None = None
    claims: list[str] = Field(default_factory=list)  # patents: independent claims first when known
    date: dt.date | None = None  # publication date (papers) / publication date (patents)
    priority_date: dt.date | None = None
    venue: str | None = None
    assignees: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    cpc: list[str] = Field(default_factory=list)
    country: str | None = None
    family_id: str | None = None
    url: str | None = None
    cited_by: int | None = None
    score: float = 0.0  # retrieval relevance, 0..1
    before_priority: bool | None = None  # None when either date is unknown
    fixture: bool = False  # True only for test data; never served outside test mode

    def text(self) -> str:
        return "\n".join([self.title, self.abstract or "", *self.claims])


class SourceStatus(BaseModel):
    source: str
    state: SourceState
    hits: int = 0
    queries: list[str] = Field(default_factory=list)
    detail: str | None = None
    ms: int | None = None


class Element(BaseModel):
    id: str  # E1, E2 ...
    text: str  # verbatim from the submission (claims or abstract)
    origin: Literal["claim", "abstract", "model"]
    claim_no: int | None = None


class Judgment(BaseModel):
    element: str
    ref: str
    verdict: Verdict
    quote: str | None = None  # verbatim from the reference; verified
    rationale: str | None = None
    method: Literal["llm", "lexical"]


class ElementSignal(BaseModel):
    element: str
    status: Literal["disclosed_before_priority", "disclosed_date_unknown", "partially_disclosed", "not_found_in_retrieved"]
    refs: list[str] = Field(default_factory=list)


class TRLEvidence(BaseModel):
    level: int
    cue: str
    quote: str
    achieved: bool  # False for planned work ("we will scale to a pilot line")


class TRLAssessment(BaseModel):
    track: Literal["A_upcycling_materials", "B_recycling_process", "unknown"]
    rubric_version: str
    low: int | None
    high: int | None
    evidence: list[TRLEvidence] = Field(default_factory=list)
    next_milestones: list[str] = Field(default_factory=list)
    note: str


class FTOFlag(BaseModel):
    ref: str
    country: str | None
    elements_disclosed: list[str]
    legal_status: Literal["unknown", "in_force", "lapsed", "expired", "pending"] = "unknown"
    note: str


class EvidenceReport(BaseModel):
    submission_title: str
    generated_at: str
    sources: list[SourceStatus]
    queries: list[str]
    references: list[Reference]
    elements: list[Element]
    judgments: list[Judgment]
    element_signals: list[ElementSignal]
    summary: str
    coverage: str
    trl: TRLAssessment
    fto_flags: list[FTOFlag]
    dropped_judgments: list[dict] = Field(default_factory=list)  # model claims that failed quote checks
    llm_used: bool
    bundle_sha256: str
    disclaimer: str = ("Automated evidence search, not legal advice. Recall is limited to the sources and queries "
                       "listed; absence of a match is not proof of novelty, and FTO flags need a patent attorney "
                       "with full claims and legal status for each jurisdiction.")
