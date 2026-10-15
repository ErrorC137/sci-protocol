"""Process-wide singletons."""

from __future__ import annotations

import logging
from functools import lru_cache

from .config import settings
from .db.base import Store
from .embed import get_embedder

log = logging.getLogger("sci")


def build_store(load: bool = True) -> Store:
    name = get_embedder().name
    if settings.database_url:
        from .db.postgres import PostgresStore

        store: Store = PostgresStore(settings.database_url, name)
    else:
        from .db.memory import MemoryStore

        store = MemoryStore(settings.data_dir, name)
    if load:
        from .ingest.run import run

        # Memory store: always load the curated corpus. Postgres: only if empty (ingest runs on a schedule).
        if store.kind == "memory" or store.count() == 0:
            for r in run(store, ["curated", *settings.startup_connectors]):
                log.info("ingest %s: %s rows, %s errors", r["source"], r["upserted"], len(r["errors"]))
    return store


@lru_cache(maxsize=1)
def get_store() -> Store:
    return build_store()
