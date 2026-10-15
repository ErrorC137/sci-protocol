"""Content-addressed blobs the API must keep across restarts: local-IPFS objects and uploaded forms.
In Postgres (table `blobs`) when DATABASE_URL is set, so a host without a persistent disk loses nothing on
restart; otherwise files under DATA_DIR/<namespace>/, exactly as before. Keys are CIDs or sha256 hex,
validated by the callers."""

from __future__ import annotations

from .config import settings


def _pg():
    if not settings.database_url:
        return None
    from .deps import get_store

    return get_store()


def put(namespace: str, key: str, data: bytes) -> None:
    store = _pg()
    if store is not None:
        store.put_blob(namespace, key, data)  # type: ignore[attr-defined]
        return
    d = settings.data_dir / namespace
    d.mkdir(parents=True, exist_ok=True)
    (d / key).write_bytes(data)


def get(namespace: str, key: str) -> bytes | None:
    store = _pg()
    if store is not None:
        return store.get_blob(namespace, key)  # type: ignore[attr-defined]
    p = settings.data_dir / namespace / key
    return p.read_bytes() if p.exists() else None
