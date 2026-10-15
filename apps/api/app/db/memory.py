"""In-memory store. Grants live in RAM (re-loaded from the seed corpus on boot); form templates and
application drafts are mirrored to JSON files under DATA_DIR so a restart mid-demo loses nothing."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

from ..embed import cosine
from ..match import filters
from ..models.schemas import Application, FormTemplate, Funder, Grant, ProjectProfile
from .base import GrantQuery, Scored


def _matches_query(g: Grant, q: GrantQuery, now: datetime) -> bool:
    if q.fields and not (set(q.fields) & set(g.fields)):
        return False
    if q.country and g.eligible_countries and "*" not in g.eligible_countries and q.country not in g.eligible_countries:
        return False
    if q.applicant_type and g.applicant_types and q.applicant_type not in g.applicant_types:
        return False
    if q.trl is not None and ((g.trl_min and q.trl < g.trl_min) or (g.trl_max and q.trl > g.trl_max)):
        return False
    if q.source and g.source != q.source:
        return False
    if q.funder_type and g.funder_type != q.funder_type:
        return False
    if q.no_equity and g.equity_taken:
        return False
    if not q.include_closed and g.deadline and not g.rolling and g.deadline <= now:
        return False
    return True


class MemoryStore:
    kind = "memory"

    def __init__(self, data_dir: Path, embedder_name: str):
        self.embedder_name = embedder_name
        self._grants: dict[str, Grant] = {}
        self._vecs: dict[str, list[float]] = {}
        self._funders: dict[str, Funder] = {}
        self._lock = threading.Lock()
        self._dir = data_dir
        (self._dir / "templates").mkdir(parents=True, exist_ok=True)
        (self._dir / "applications").mkdir(parents=True, exist_ok=True)
        self._templates: dict[str, FormTemplate] = {}
        for p in (self._dir / "templates").glob("*.json"):
            t = FormTemplate.model_validate_json(p.read_text())
            self._templates[t.id] = t

    # grants ---------------------------------------------------------------
    def upsert(self, funders: list[Funder], grants: list[Grant], embeddings: list[list[float]]) -> int:
        with self._lock:
            for f in funders:
                self._funders[f.id] = f
            for g, v in zip(grants, embeddings, strict=True):
                self._grants[g.id] = g
                self._vecs[g.id] = v
        return len(grants)

    def count(self) -> int:
        return len(self._grants)

    def sources(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for g in self._grants.values():
            out[g.source] = out.get(g.source, 0) + 1
        return out

    def get_grant(self, grant_id: str) -> Grant | None:
        return self._grants.get(grant_id)

    def search(self, query: GrantQuery, qvec: list[float] | None) -> tuple[list[Scored], int]:
        now = datetime.now(timezone.utc)
        hits = [g for g in self._grants.values() if _matches_query(g, query, now)]
        scored = [Scored(g, cosine(qvec, self._vecs[g.id]) if qvec else 0.0) for g in hits]
        if qvec:
            scored.sort(key=lambda s: -s.similarity)
        else:
            far = datetime.max.replace(tzinfo=timezone.utc)
            scored.sort(key=lambda s: (s.grant.deadline or far, s.grant.title))
        return scored[query.offset : query.offset + query.limit], len(scored)

    def split_for_match(self, profile: ProjectProfile, pvec: list[float]) -> tuple[list[Scored], list[Grant]]:
        eligible, rest = [], []
        for g in self._grants.values():
            if filters.is_eligible(filters.evaluate(g, profile)):
                eligible.append(Scored(g, cosine(pvec, self._vecs[g.id])))
            else:
                rest.append(g)
        return eligible, rest

    # templates & applications ----------------------------------------------
    def get_template_by_url(self, form_url: str) -> FormTemplate | None:
        return next((t for t in self._templates.values() if t.form_url == form_url), None)

    def get_template(self, template_id: str) -> FormTemplate | None:
        return self._templates.get(template_id)

    def save_template(self, t: FormTemplate) -> None:
        for old in [o for o in self._templates.values() if o.form_url == t.form_url and o.id != t.id]:
            self._templates.pop(old.id)
            (self._dir / "templates" / f"{old.id}.json").unlink(missing_ok=True)
        self._templates[t.id] = t
        (self._dir / "templates" / f"{t.id}.json").write_text(t.model_dump_json(indent=1))

    def get_application(self, app_id: str) -> Application | None:
        p = self._dir / "applications" / f"{app_id}.json"
        return Application.model_validate_json(p.read_text()) if p.exists() else None

    def save_application(self, a: Application) -> None:
        (self._dir / "applications" / f"{a.id}.json").write_text(a.model_dump_json(indent=1))
