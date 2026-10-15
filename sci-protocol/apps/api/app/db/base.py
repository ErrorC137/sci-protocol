"""Storage interface. Two implementations: MemoryStore (seed corpus in RAM, zero setup) and
PostgresStore (Supabase + pgvector). Both return the same shapes so the services don't care."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..models.schemas import Application, FormTemplate, Funder, Grant, ProjectProfile


@dataclass
class GrantQuery:
    q: str | None = None
    fields: list[str] = field(default_factory=list)
    country: str | None = None
    applicant_type: str | None = None
    trl: int | None = None
    source: str | None = None
    funder_type: str | None = None
    no_equity: bool = False
    include_closed: bool = False
    limit: int = 50
    offset: int = 0


@dataclass
class Scored:
    grant: Grant
    similarity: float


class Store(Protocol):
    kind: str
    embedder_name: str

    def upsert(self, funders: list[Funder], grants: list[Grant], embeddings: list[list[float]]) -> int: ...
    def count(self) -> int: ...
    def sources(self) -> dict[str, int]: ...
    def get_grant(self, grant_id: str) -> Grant | None: ...
    def search(self, query: GrantQuery, qvec: list[float] | None) -> tuple[list[Scored], int]: ...
    def split_for_match(self, profile: ProjectProfile, pvec: list[float]) -> tuple[list[Scored], list[Grant]]:
        """(eligible-by-prefilter with cosine similarity, everything else). Python rules then run on both."""
        ...

    def get_template_by_url(self, form_url: str) -> FormTemplate | None: ...
    def get_template(self, template_id: str) -> FormTemplate | None: ...
    def save_template(self, t: FormTemplate) -> None: ...
    def get_application(self, app_id: str) -> Application | None: ...
    def save_application(self, a: Application) -> None: ...
