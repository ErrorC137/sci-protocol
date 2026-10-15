"""Runtime settings, read once from the environment. Every external service is optional:
the API degrades to a local, deterministic mode when a key is missing, and /health says so."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = API_DIR.parent.parent


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    # Storage: Postgres + pgvector (Supabase) when set, otherwise in-memory from the seed corpus.
    database_url: str | None = field(default_factory=lambda: _env("DATABASE_URL"))
    seed_path: Path = field(
        default_factory=lambda: Path(_env("SEED_PATH", str(REPO_ROOT / "data" / "seed" / "grants.yaml")))
    )
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", str(API_DIR / ".data"))))

    # LLM (Claude). Explanations and form mapping fall back to deterministic templates without it.
    anthropic_api_key: str | None = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    llm_model: str = field(default_factory=lambda: _env("SCI_LLM_MODEL", "claude-opus-5-5"))
    llm_timeout_s: float = field(default_factory=lambda: float(_env("SCI_LLM_TIMEOUT", "60")))
    explain_top_k: int = field(default_factory=lambda: int(_env("SCI_EXPLAIN_TOP_K", "10")))

    # Embeddings: Voyage (1024-d) when keyed, otherwise a local feature-hashing embedder (also 1024-d).
    voyage_api_key: str | None = field(default_factory=lambda: _env("VOYAGE_API_KEY"))
    voyage_model: str = field(default_factory=lambda: _env("VOYAGE_MODEL", "voyage-3.5"))

    # IPFS: Pinata when keyed, otherwise a local content-addressed store served at /ipfs/{cid}.
    pinata_jwt: str | None = field(default_factory=lambda: _env("PINATA_JWT"))
    ipfs_gateway: str = field(default_factory=lambda: _env("IPFS_GATEWAY", "https://gateway.pinata.cloud/ipfs/"))

    # Chain
    chain_id: int = field(default_factory=lambda: int(_env("CHAIN_ID", "84532")))
    rpc_url: str | None = field(default_factory=lambda: _env("RPC_URL"))
    deployments_dir: Path = field(
        default_factory=lambda: Path(_env("DEPLOYMENTS_DIR", str(REPO_ROOT / "contracts" / "deployments")))
    )
    indexer_enabled: bool = field(default_factory=lambda: _env("INDEXER_ENABLED", "false").lower() == "true")
    indexer_interval_s: float = field(default_factory=lambda: float(_env("INDEXER_INTERVAL", "8")))

    # Grant source connectors run at startup (comma list), e.g. "grants_gov,eu_sedia". Curated always loads.
    startup_connectors: list[str] = field(
        default_factory=lambda: [s.strip() for s in (_env("STARTUP_CONNECTORS", "") or "").split(",") if s.strip()]
    )

    cors_origins: list[str] = field(
        default_factory=lambda: [s.strip() for s in _env("CORS_ORIGINS", "*").split(",") if s.strip()]
    )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
