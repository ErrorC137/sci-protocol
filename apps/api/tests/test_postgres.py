"""Runs the Postgres + pgvector store end to end and checks that the SQL prefilter (ELIGIBLE_SQL) agrees
exactly with the Python rules for a spread of profiles. Needs a Postgres with pgvector:

    PG_TEST_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres pytest tests/test_postgres.py
"""

import json
import os
from pathlib import Path

import pytest

PG = os.environ.get("PG_TEST_URL")
pytestmark = pytest.mark.skipif(not PG, reason="set PG_TEST_URL to a Postgres with pgvector")

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def pg_store():
    import psycopg

    from app.config import settings
    from app.db.postgres import PostgresStore
    from app.embed import get_embedder
    from app.ingest.curated import CuratedConnector
    from app.ingest.run import ingest

    with psycopg.connect(PG, autocommit=True) as c:
        c.execute("drop table if exists applications, form_templates, matches, projects, grants, funders, blobs cascade")
    store = PostgresStore(PG, get_embedder().name)
    ingest(store, CuratedConnector(settings.seed_path).fetch())
    ingest(store, CuratedConnector(settings.seed_path).fetch())  # idempotent upsert
    return store


def test_blobs_survive_in_postgres(pg_store):
    pg_store.put_blob("ipfs", "bafk-test", b"\x00ciphertext")
    pg_store.put_blob("ipfs", "bafk-test", b"\x00ciphertext")  # content-addressed: re-put is a no-op
    assert pg_store.get_blob("ipfs", "bafk-test") == b"\x00ciphertext"
    assert pg_store.get_blob("uploads", "bafk-test") is None


def test_upsert_is_idempotent(pg_store):
    assert pg_store.count() == 75
    assert pg_store.sources() == {"curated": 75}


PROFILES = [
    {},  # the demo persona
    {"applicant_type": "startup"},
    {"applicant_type": "individual", "country": "SG", "trl": 2},
    {"trl": 7, "constraints": [], "funding_min_usd": 200000, "funding_max_usd": 2000000, "applicant_type": "sme", "country": "US"},
    {"applicant_type": "consortium", "country": "DE", "trl": 3, "constraints": ["no_ip_assignment"]},
]


@pytest.mark.parametrize("override", PROFILES)
def test_sql_prefilter_agrees_with_python_rules(pg_store, override):
    from app.embed import get_embedder
    from app.match import filters
    from app.models.schemas import ProjectProfile

    base = json.loads((REPO / "data" / "demo" / "persona.json").read_text())["profile"]
    p = ProjectProfile(**{**base, **override, "has_entity": None})
    vec = get_embedder().embed([p.embedding_text()])[0]
    eligible, rest = pg_store.split_for_match(p, vec)
    for s in eligible:
        assert filters.is_eligible(filters.evaluate(s.grant, p)), (s.grant.title, filters.failed(filters.evaluate(s.grant, p)))
    for g in rest:
        assert not filters.is_eligible(filters.evaluate(g, p)), g.title
    sims = [s.similarity for s in eligible]
    assert sims == sorted(sims, reverse=True)


def test_search_and_templates_roundtrip(pg_store):
    from app.db.base import GrantQuery
    from app.embed import get_embedder
    from app.forms.service import create_application, get_template
    from app.models.schemas import Applicant, ProjectProfile

    q = get_embedder().embed(["agricultural research thailand"])[0]
    items, total = pg_store.search(GrantQuery(country="TH", limit=5), q)
    assert total >= 20 and len(items) == 5
    grant = next(s.grant for s in pg_store.search(GrantQuery(limit=200, include_closed=True), None)[0]
                 if s.grant.source_ref == "nrct-research-grants")
    t = get_template(pg_store, grant.form_url)
    assert pg_store.get_template_by_url(grant.form_url).id == t.id
    base = json.loads((REPO / "data" / "demo" / "persona.json").read_text())
    a = create_application(pg_store, grant, t, ProjectProfile(**base["profile"]), Applicant(**base["applicant"]))
    assert pg_store.get_application(a.id).summary() == a.summary()
