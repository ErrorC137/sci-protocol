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
    chain_id: int = field(default_factory=lambda: int(_env("CHAIN_ID", "43113")))  # Avalanche Fuji
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

    # Evidence engine (app/evidence). Every source is optional; missing keys show as `no_key` in reports.
    evidence_mailto: str | None = field(default_factory=lambda: _env("EVIDENCE_MAILTO"))  # polite-pool contact
    openalex_api_key: str | None = field(default_factory=lambda: _env("OPENALEX_API_KEY"))  # required since Feb 2026
    s2_api_key: str | None = field(default_factory=lambda: _env("S2_API_KEY"))
    patentsview_api_key: str | None = field(default_factory=lambda: _env("PATENTSVIEW_API_KEY"))
    epo_ops_key: str | None = field(default_factory=lambda: _env("EPO_OPS_KEY"))
    epo_ops_secret: str | None = field(default_factory=lambda: _env("EPO_OPS_SECRET"))
    lens_api_token: str | None = field(default_factory=lambda: _env("LENS_API_TOKEN"))
    patent_corpus: Path | None = field(default_factory=lambda: Path(p) if (p := _env("PATENT_CORPUS")) else None)
    evidence_sources: list[str] = field(
        default_factory=lambda: [s.strip() for s in (_env("EVIDENCE_SOURCES") or
                                 "local,openalex,crossref,semantic_scholar,arxiv,patentsview,epo_ops,lens").split(",") if s.strip()]
    )
    # Test fixtures carry TEST- ids; the engine refuses to put them in a report unless this is set (tests only).
    evidence_allow_fixtures: bool = field(default_factory=lambda: _env("EVIDENCE_ALLOW_FIXTURES", "false").lower() == "true")

    cors_origins: list[str] = field(
        default_factory=lambda: [s.strip() for s in _env("CORS_ORIGINS", "*").split(",") if s.strip()]
    )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
