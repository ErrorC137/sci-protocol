"""1024-d embeddings (matches the `vector(1024)` column). Voyage when keyed; otherwise a deterministic
local feature-hashing embedder so the system works offline and in tests."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

import httpx

from .config import settings

DIM = 1024

_STOP = set(
    "a an and are as at be by for from has have in into is it its of on or that the this to with within "
    "your you our we their they use used using via per who which will can may".split()
    # Boilerplate labels that appear in every profile and grant text carry no signal.
    + "fields topics technology readiness trl evidence applicant funder".split()
)
# Light synonym folding so the local embedder links vocabulary used by funders and by the taxonomy.
_SYN = {
    "materials": "material", "agricultural": "agri", "agriculture": "agri", "agritech": "agri",
    "biotechnology": "biotech", "bio": "biotech", "environmental": "environment", "climate": "environment",
    "sustainability": "environment", "sustainable": "environment", "renewable": "energy", "cleantech": "energy",
    "deeptech": "deep", "deep-tech": "deep", "startups": "startup", "researchers": "research",
    "researcher": "research", "scientific": "science", "sciences": "science", "innovation": "innovate",
    "innovative": "innovate", "commercialization": "commercial", "commercialisation": "commercial",
    "prototype": "prototyp", "prototyping": "prototyp", "prototypes": "prototyp", "pilot": "pilot",
    "universities": "university", "biomass": "biomass", "valorization": "valoriz", "valorisation": "valoriz",
    "composites": "composite", "medical": "health", "healthcare": "health", "longevity": "ageing",
    "aging": "ageing", "food": "food", "foods": "food", "web3": "blockchain", "crypto": "blockchain",
}


def _tokens(text: str) -> list[str]:
    toks = []
    for t in re.findall(r"[a-z0-9][a-z0-9\-]+", text.lower()):
        if t in _STOP or len(t) < 2:
            continue
        t = _SYN.get(t, t)
        if len(t) > 4 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        toks.append(t)
    return toks


def _bucket(feature: str) -> tuple[int, float]:
    h = hashlib.blake2b(feature.encode(), digest_size=8).digest()
    n = int.from_bytes(h, "little")
    return n % DIM, (1.0 if (n >> 63) & 1 else -1.0)


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str], kind: str = "document") -> list[list[float]]: ...


class HashingEmbedder:
    name = "local-hashing-1024"

    def embed(self, texts: list[str], kind: str = "document") -> list[list[float]]:
        out = []
        for text in texts:
            v = [0.0] * DIM
            toks = _tokens(text)
            feats = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
            counts: dict[str, int] = {}
            for f in feats:
                counts[f] = counts.get(f, 0) + 1
            for f, c in counts.items():
                i, sign = _bucket(f)
                v[i] += sign * (1.0 + math.log(c)) * (0.6 if "_" in f else 1.0)
            out.append(_normalize(v))
        return out


class VoyageEmbedder:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.name = f"voyage:{model}"

    def embed(self, texts: list[str], kind: str = "document") -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 128):
            r = httpx.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "input": texts[i : i + 128],
                    "model": self.model,
                    "input_type": "query" if kind == "query" else "document",
                    "output_dimension": DIM,
                },
                timeout=60,
            )
            r.raise_for_status()
            out.extend(_normalize(d["embedding"]) for d in sorted(r.json()["data"], key=lambda d: d["index"]))
        return out


def _normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = (
            VoyageEmbedder(settings.voyage_api_key, settings.voyage_model)
            if settings.voyage_api_key
            else HashingEmbedder()
        )
    return _embedder
