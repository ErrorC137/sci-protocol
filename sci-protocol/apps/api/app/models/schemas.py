"""Canonical data shapes. `Grant` is the one shape every source is normalized into (brief §3.2);
`ProjectProfile` is the non-confidential intake (brief §4.1)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from . import taxonomy

GRANT_NS = uuid.UUID("6f1c2b1e-9a51-4c43-8a8e-5c1d0b7a2f10")


def grant_id(source: str, source_ref: str) -> str:
    """Stable id so re-ingesting a source upserts instead of duplicating."""
    return str(uuid.uuid5(GRANT_NS, f"{source}:{source_ref}"))


def funder_id(name: str) -> str:
    return str(uuid.uuid5(GRANT_NS, f"funder:{name.strip().lower()}"))


class Funder(BaseModel):
    id: str
    name: str
    type: str | None = None
    country: str | None = None
    website: str | None = None


class Grant(BaseModel):
    id: str
    funder_id: str | None = None
    funder_name: str | None = None
    funder_type: str | None = None
    title: str
    summary: str | None = None
    source: str
    source_ref: str
    url: str | None = None
    # eligibility - the fields hard filters run on
    trl_min: int | None = None
    trl_max: int | None = None
    fields: list[str] = Field(default_factory=list)
    eligible_countries: list[str] = Field(default_factory=list)  # ISO2 list, ["*"] = global, [] = unknown
    applicant_types: list[str] = Field(default_factory=list)  # [] = unknown
    requires_incorporation: bool | None = None
    ip_assignment_required: bool | None = None
    # money & time
    amount_min_usd: float | None = None
    amount_max_usd: float | None = None
    currency: str | None = None
    equity_taken: bool | None = None
    deadline: datetime | None = None
    rolling: bool = False
    cycle_note: str | None = None
    # application mechanics
    application_mode: str | None = None
    form_url: str | None = None
    # provenance
    verified: bool = False
    confidence: Literal["high", "medium", "low"] = "medium"
    notes: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def embedding_text(self) -> str:
        parts = [self.title, self.summary or ""]
        if self.fields:
            parts.append("Fields: " + ", ".join(taxonomy.field_label(f) for f in self.fields))
        subs = self.raw.get("subdomains") or []
        if subs:
            parts.append("Topics: " + ", ".join(subs))
        if self.trl_min or self.trl_max:
            parts.append(f"Technology readiness TRL {self.trl_min or 1}-{self.trl_max or 9}")
        if self.applicant_types:
            parts.append("For: " + ", ".join(self.applicant_types))
        if self.funder_name:
            parts.append(f"Funder: {self.funder_name}")
        return ". ".join(p for p in parts if p)


class Applicant(BaseModel):
    """Contact details used ONLY to fill application forms. Never used for matching, never stored
    server-side beyond the application draft the researcher creates."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    organization: str | None = None
    position: str | None = None
    address: str | None = None


class ProjectProfile(BaseModel):
    """Structured, non-confidential intake. There is deliberately no free-text description field."""

    nickname: str | None = Field(default=None, max_length=80, description="A label for you, not a description of the invention")
    fields: list[str] = Field(min_length=1, max_length=3)
    subdomains: list[str] = Field(default_factory=list, max_length=6)
    trl: int = Field(ge=1, le=9)
    evidence: list[str] = Field(default_factory=list)
    applicant_type: str
    has_entity: bool | None = None
    country: str = Field(min_length=2, max_length=2)
    institution_type: str | None = None
    funding_min_usd: float = Field(ge=0)
    funding_max_usd: float = Field(ge=0)
    uses_of_funds: list[str] = Field(default_factory=list)
    months_to_milestone: int = Field(ge=1, le=120, default=12)
    constraints: list[str] = Field(default_factory=list)

    @field_validator("fields")
    @classmethod
    def _known_fields(cls, v: list[str]) -> list[str]:
        bad = [f for f in v if f not in taxonomy.FIELDS]
        if bad:
            raise ValueError(f"unknown field(s): {bad}")
        return v

    @field_validator("subdomains")
    @classmethod
    def _known_subdomains(cls, v: list[str]) -> list[str]:
        allowed = {s for f in taxonomy.FIELDS.values() for s in f["subdomains"]}
        bad = [s for s in v if s not in allowed]
        if bad:
            # Free text here would be a disclosure channel; only controlled vocabulary is accepted.
            raise ValueError(f"sub-domains must come from the controlled vocabulary: {bad}")
        return v

    @field_validator("applicant_type")
    @classmethod
    def _known_applicant(cls, v: str) -> str:
        if v not in taxonomy.APPLICANT_TYPES:
            raise ValueError(f"unknown applicant_type {v}")
        return v

    @field_validator("evidence", "uses_of_funds", "constraints")
    @classmethod
    def _known_vocab(cls, v: list[str], info) -> list[str]:
        vocab = {
            "evidence": taxonomy.EVIDENCE,
            "uses_of_funds": taxonomy.USES_OF_FUNDS,
            "constraints": taxonomy.CONSTRAINTS,
        }[info.field_name]
        bad = [x for x in v if x not in vocab]
        if bad:
            raise ValueError(f"unknown {info.field_name}: {bad}")
        return v

    @field_validator("country")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def _derive(self) -> "ProjectProfile":
        if self.funding_max_usd < self.funding_min_usd:
            self.funding_min_usd, self.funding_max_usd = self.funding_max_usd, self.funding_min_usd
        if self.has_entity is None:
            self.has_entity = self.applicant_type in taxonomy.ENTITY_APPLICANT_TYPES
        return self

    def embedding_text(self) -> str:
        """Built only from controlled vocabulary - safe to send to an embedding provider."""
        parts = ["Fields: " + ", ".join(taxonomy.field_label(f) for f in self.fields)]
        if self.subdomains:
            parts.append("Topics: " + ", ".join(self.subdomains))
        parts.append(f"Technology readiness TRL {self.trl}: {taxonomy.TRL_LEVELS[self.trl]['name']}")
        if self.evidence:
            parts.append("Evidence: " + ", ".join(taxonomy.EVIDENCE[e]["label"] for e in self.evidence))
        if self.uses_of_funds:
            parts.append("Funding for: " + ", ".join(taxonomy.USES_OF_FUNDS[u] for u in self.uses_of_funds))
        parts.append(f"Applicant: {taxonomy.APPLICANT_TYPES[self.applicant_type]} in {taxonomy.country_name(self.country)}")
        return ". ".join(parts)


RuleStatus = Literal["pass", "fail", "unknown"]


class RuleResult(BaseModel):
    rule: str
    status: RuleStatus
    detail: str


class ScoreBreakdown(BaseModel):
    similarity: float
    field_overlap: float
    trl_centering: float
    amount_fit: float
    deadline_feasibility: float
    total: float


class Explanation(BaseModel):
    why_matched: str
    strengthen: str
    source: Literal["llm", "template"]


class MatchResult(BaseModel):
    grant: Grant
    eligible: bool
    rules: list[RuleResult]
    score: ScoreBreakdown | None = None
    days_left: int | None = None
    effort: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    explanation: Explanation | None = None


class Unlock(BaseModel):
    """'If you changed X, N more opportunities would pass the hard filters.'"""

    change: str
    label: str
    count: int
    examples: list[str]


class MatchResponse(BaseModel):
    matches: list[MatchResult]
    excluded_count: int
    excluded_by_rule: dict[str, int]
    near_misses: list[MatchResult]
    unlocks: list[Unlock] = Field(default_factory=list)
    trl_assessment: dict[str, Any]
    corpus_size: int
    embedder: str


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

FieldType = Literal["text", "textarea", "number", "date", "email", "tel", "checkbox", "radio", "select", "signature"]


class FieldSpec(BaseModel):
    id: str
    label: str
    type: FieldType = "text"
    options: list[str] = Field(default_factory=list)
    maxlen: int | None = None
    required: bool = False
    hint: str | None = None
    page: int | None = None
    narrative: bool = False


class FormTemplate(BaseModel):
    id: str
    form_url: str
    kind: Literal["pdf_acroform", "pdf_flat", "html_form"]
    title: str | None = None
    fields: list[FieldSpec]
    source_sha256: str
    extraction: Literal["acroform", "html", "layout_heuristic", "ocr", "llm"] = "acroform"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def field_count(self) -> int:
        return len(self.fields)


FillStatus = Literal["green", "amber", "red"]


class FilledField(BaseModel):
    field_id: str
    label: str
    type: FieldType = "text"
    value: str | bool | list[str] | None = None  # list = selected options of a checkbox group
    status: FillStatus
    source: Literal["profile", "llm", "template", "user", "none"]
    rationale: str | None = None
    narrative: bool = False
    required: bool = False
    options: list[str] = Field(default_factory=list)
    maxlen: int | None = None
    warnings: list[str] = Field(default_factory=list)
    confirmed: bool = False  # researcher ticked "checked" on an amber field
    acknowledged_blank: bool = False  # researcher chose to leave a red field empty


class Application(BaseModel):
    id: str
    grant_id: str
    template_id: str
    fields: list[FilledField]
    reviewed: bool = False
    reviewed_at: datetime | None = None
    llm_used: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def summary(self) -> dict[str, int]:
        s = {"green": 0, "amber": 0, "red": 0}
        for f in self.fields:
            s[f.status] += 1
        s["total"] = len(self.fields)
        return s
