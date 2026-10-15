import json
import os
import tempfile
from pathlib import Path

import pytest

# Isolate every test run: fresh data dir, no external keys, in-memory store.
_tmp = tempfile.mkdtemp(prefix="sci-test-")
os.environ["DATA_DIR"] = _tmp
for k in ("DATABASE_URL", "ANTHROPIC_API_KEY", "VOYAGE_API_KEY", "PINATA_JWT", "INDEXER_ENABLED", "STARTUP_CONNECTORS"):
    os.environ.pop(k, None)

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def persona() -> dict:
    return json.loads((REPO / "data" / "demo" / "persona.json").read_text())


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def grants_by_ref(client) -> dict:
    from app.db.base import GrantQuery
    from app.deps import get_store

    items, _ = get_store().search(GrantQuery(limit=1000, include_closed=True), None)
    return {s.grant.source_ref: s.grant for s in items}
