"""Postgres + pgvector store (Supabase). Stage-1 hard eligibility runs in SQL; cosine similarity is
computed by pgvector. Python rules (match/filters.py) still run afterwards and are authoritative."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from ..config import REPO_ROOT
from ..models.schemas import Application, FormTemplate, Funder, Grant, ProjectProfile
from .base import GrantQuery, Scored

MIGRATION = REPO_ROOT / "supabase" / "migrations" / "0001_init.sql"

_GRANT_COLS = [
    "id", "funder_id", "title", "summary", "source", "source_ref", "url", "trl_min", "trl_max", "fields",
    "eligible_countries", "applicant_types", "requires_incorporation", "ip_assignment_required",
    "amount_min_usd", "amount_max_usd", "currency", "equity_taken", "deadline", "rolling", "cycle_note",
    "application_mode", "form_url", "verified", "confidence", "notes", "raw", "updated_at",
]

# Stage 1 (brief §4.2) as SQL. Must agree with match/filters.py - see tests/test_postgres.py.
ELIGIBLE_SQL = """
    (cardinality(g.eligible_countries) = 0 or '*' = any(g.eligible_countries) or %(country)s = any(g.eligible_countries))
and (cardinality(g.applicant_types) = 0 or %(applicant_type)s = any(g.applicant_types))
and (g.trl_min is null or g.trl_min <= %(trl)s) and (g.trl_max is null or g.trl_max >= %(trl)s)
and (g.amount_max_usd is null or g.amount_max_usd >= %(need_min)s)
and (g.amount_min_usd is null or g.amount_min_usd <= %(need_max)s)
and (g.rolling or g.deadline is null or g.deadline > now())
and not (coalesce(g.requires_incorporation, false) and not %(has_entity)s)
and not (coalesce(g.equity_taken, false) and %(no_equity)s)
and not (coalesce(g.ip_assignment_required, false) and %(no_ip)s)
"""


def _configure(conn: psycopg.Connection) -> None:
    register_vector(conn)


class PostgresStore:
    kind = "postgres"

    def __init__(self, dsn: str, embedder_name: str):
        self.embedder_name = embedder_name
        # Supabase's transaction pooler (port 6543) doesn't support prepared statements.
        self.pool = ConnectionPool(
            dsn,
            min_size=1,
            max_size=5,
            kwargs={"autocommit": True, "prepare_threshold": None, "row_factory": dict_row},
            configure=_configure,
            open=False,
        )
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(MIGRATION.read_text())
        self.pool.open(wait=True, timeout=30)

    # grants ---------------------------------------------------------------
    @staticmethod
    def _row_to_grant(r: dict) -> Grant:
        d = {k: r[k] for k in _GRANT_COLS if k in r}
        d["id"], d["funder_id"] = str(d["id"]), (str(d["funder_id"]) if d.get("funder_id") else None)
        for k in ("amount_min_usd", "amount_max_usd"):
            d[k] = float(d[k]) if d.get(k) is not None else None
        d["funder_name"], d["funder_type"] = r.get("funder_name"), r.get("funder_type")
        return Grant.model_validate(d)

    def upsert(self, funders: list[Funder], grants: list[Grant], embeddings: list[list[float]]) -> int:
        cols = _GRANT_COLS + ["embedding", "embedding_model"]
        placeholders = ", ".join(f"%({c})s" for c in cols)
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c not in ("id", "source", "source_ref"))
        with self.pool.connection() as c, c.transaction():
            for f in funders:
                c.execute(
                    """insert into funders (id, name, type, country, website) values (%(id)s, %(name)s, %(type)s, %(country)s, %(website)s)
                       on conflict (id) do update set name = excluded.name, type = excluded.type,
                       country = excluded.country, website = excluded.website""",
                    f.model_dump(),
                )
            for g, v in zip(grants, embeddings, strict=True):
                row = g.model_dump(include=set(_GRANT_COLS))
                row["raw"] = Jsonb(row["raw"])
                row["embedding"] = v
                row["embedding_model"] = self.embedder_name
                c.execute(
                    f"insert into grants ({', '.join(cols)}) values ({placeholders}) "
                    f"on conflict (source, source_ref) do update set {updates}",
                    row,
                )
        return len(grants)

    def count(self) -> int:
        with self.pool.connection() as c:
            return c.execute("select count(*) as n from grants").fetchone()["n"]

    def sources(self) -> dict[str, int]:
        with self.pool.connection() as c:
            return {r["source"]: r["n"] for r in c.execute("select source, count(*) as n from grants group by source")}

    _SELECT = (
        "select g.*, f.name as funder_name, f.type as funder_type from grants g left join funders f on f.id = g.funder_id"
    )

    def get_grant(self, grant_id: str) -> Grant | None:
        with self.pool.connection() as c:
            r = c.execute(self._SELECT + " where g.id = %s", (grant_id,)).fetchone()
        return self._row_to_grant(r) if r else None

    def search(self, query: GrantQuery, qvec: list[float] | None) -> tuple[list[Scored], int]:
        where, p = ["true"], {}
        if query.fields:
            where.append("g.fields && %(fields)s")
            p["fields"] = query.fields
        if query.country:
            where.append("(cardinality(g.eligible_countries) = 0 or '*' = any(g.eligible_countries) or %(country)s = any(g.eligible_countries))")
            p["country"] = query.country
        if query.applicant_type:
            where.append("(cardinality(g.applicant_types) = 0 or %(at)s = any(g.applicant_types))")
            p["at"] = query.applicant_type
        if query.trl is not None:
            where.append("(g.trl_min is null or g.trl_min <= %(trl)s) and (g.trl_max is null or g.trl_max >= %(trl)s)")
            p["trl"] = query.trl
        if query.source:
            where.append("g.source = %(source)s")
            p["source"] = query.source
        if query.funder_type:
            where.append("f.type = %(ftype)s")
            p["ftype"] = query.funder_type
        if query.no_equity:
            where.append("not coalesce(g.equity_taken, false)")
        if not query.include_closed:
            where.append("(g.rolling or g.deadline is null or g.deadline > now())")
        w = " and ".join(where)
        sim = "0.0"
        if qvec is not None:
            sim = "1 - (g.embedding <=> %(qvec)s::vector)"
            p["qvec"] = qvec
        order = "similarity desc" if qvec is not None else "g.deadline asc nulls last, g.title"
        with self.pool.connection() as c:
            total = c.execute(
                f"select count(*) as n from grants g left join funders f on f.id = g.funder_id where {w}", p
            ).fetchone()["n"]
            rows = c.execute(
                f"select g.*, f.name as funder_name, f.type as funder_type, {sim} as similarity "
                f"from grants g left join funders f on f.id = g.funder_id where {w} "
                f"order by {order} limit %(limit)s offset %(offset)s",
                {**p, "limit": query.limit, "offset": query.offset},
            ).fetchall()
        return [Scored(self._row_to_grant(r), float(r["similarity"])) for r in rows], total

    def split_for_match(self, profile: ProjectProfile, pvec: list[float]) -> tuple[list[Scored], list[Grant]]:
        p = {
            "country": profile.country,
            "applicant_type": profile.applicant_type,
            "trl": profile.trl,
            "need_min": profile.funding_min_usd,
            "need_max": profile.funding_max_usd,
            "has_entity": bool(profile.has_entity),
            "no_equity": "no_equity" in profile.constraints,
            "no_ip": "no_ip_assignment" in profile.constraints,
            "pvec": pvec,
        }
        base = "from grants g left join funders f on f.id = g.funder_id"
        with self.pool.connection() as c:
            eligible = c.execute(
                f"select g.*, f.name as funder_name, f.type as funder_type, 1 - (g.embedding <=> %(pvec)s::vector) as similarity "
                f"{base} where {ELIGIBLE_SQL} order by similarity desc",
                p,
            ).fetchall()
            rest = c.execute(
                f"select g.*, f.name as funder_name, f.type as funder_type {base} where not ({ELIGIBLE_SQL})", p
            ).fetchall()
        return (
            [Scored(self._row_to_grant(r), float(r["similarity"])) for r in eligible],
            [self._row_to_grant(r) for r in rest],
        )

    # templates & applications ----------------------------------------------
    def _template(self, r: dict | None) -> FormTemplate | None:
        if not r:
            return None
        return FormTemplate.model_validate({**r, "id": str(r["id"])})

    def get_template_by_url(self, form_url: str) -> FormTemplate | None:
        with self.pool.connection() as c:
            return self._template(c.execute("select * from form_templates where form_url = %s", (form_url,)).fetchone())

    def get_template(self, template_id: str) -> FormTemplate | None:
        with self.pool.connection() as c:
            return self._template(c.execute("select * from form_templates where id = %s", (template_id,)).fetchone())

    def save_template(self, t: FormTemplate) -> None:
        with self.pool.connection() as c:
            c.execute(
                """insert into form_templates (id, form_url, kind, title, fields, field_count, source_sha256, extraction, created_at)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   on conflict (form_url) do update set kind = excluded.kind, title = excluded.title, fields = excluded.fields,
                   field_count = excluded.field_count, source_sha256 = excluded.source_sha256, extraction = excluded.extraction""",
                (t.id, t.form_url, t.kind, t.title, Jsonb([f.model_dump() for f in t.fields]), t.field_count,
                 t.source_sha256, t.extraction, t.created_at),
            )

    def get_application(self, app_id: str) -> Application | None:
        with self.pool.connection() as c:
            r = c.execute("select * from applications where id = %s", (app_id,)).fetchone()
        if not r:
            return None
        return Application.model_validate(
            {**r, "id": str(r["id"]), "grant_id": str(r["grant_id"]), "template_id": str(r["template_id"])}
        )

    def save_application(self, a: Application) -> None:
        with self.pool.connection() as c:
            c.execute(
                """insert into applications (id, grant_id, template_id, fields, reviewed, reviewed_at, llm_used, created_at)
                   values (%s, %s, %s, %s, %s, %s, %s, %s)
                   on conflict (id) do update set fields = excluded.fields, reviewed = excluded.reviewed,
                   reviewed_at = excluded.reviewed_at""",
                (a.id, a.grant_id, a.template_id, Jsonb(json.loads(a.model_dump_json(include={"fields"}))["fields"]),
                 a.reviewed, a.reviewed_at, a.llm_used, a.created_at or datetime.now(timezone.utc)),
            )
