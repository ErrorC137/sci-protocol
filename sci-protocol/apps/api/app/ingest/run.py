"""Run connectors and upsert into the store.

    python -m app.ingest.run                      # curated only
    python -m app.ingest.run curated grants_gov   # + live Grants.gov
    DATABASE_URL=... python -m app.ingest.run curated grants_gov eu_sedia   # into Supabase

Schedule it with Render cron or a GitHub Action (see docs/DEPLOY.md).
"""

from __future__ import annotations

import logging
import sys

from ..config import settings
from ..db.base import Store
from ..embed import get_embedder
from .base import Batch, Connector
from .curated import CuratedConnector
from .eu_sedia import EUSediaConnector
from .grants_gov import GrantsGovConnector

log = logging.getLogger("sci.ingest")


def make(name: str) -> Connector:
    if name == "curated":
        return CuratedConnector(settings.seed_path)
    if name == "grants_gov":
        return GrantsGovConnector()
    if name == "eu_sedia":
        return EUSediaConnector()
    raise ValueError(f"unknown connector {name}")


def ingest(store: Store, batch: Batch) -> dict:
    vecs = get_embedder().embed([g.embedding_text() for g in batch.grants]) if batch.grants else []
    n = store.upsert(batch.funders, batch.grants, vecs)
    for e in batch.errors:
        log.warning("[%s] %s", batch.source, e)
    return {"source": batch.source, "upserted": n, "errors": batch.errors}


def run(store: Store, names: list[str]) -> list[dict]:
    results = []
    for name in names:
        try:
            results.append(ingest(store, make(name).fetch()))
        except Exception as ex:  # a dead API must never block boot - the curated corpus still loads
            log.exception("connector %s failed", name)
            results.append({"source": name, "upserted": 0, "errors": [str(ex)]})
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from ..deps import build_store

    names = sys.argv[1:] or ["curated"]
    for r in run(build_store(load=False), names):
        print(f"{r['source']}: upserted {r['upserted']}, errors {len(r['errors'])}")
        for e in r["errors"][:10]:
            print("   ", e)
