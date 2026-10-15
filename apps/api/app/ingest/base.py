"""Connector contract: every source implements `fetch() -> list[CanonicalGrant]` (brief §3.3).
Currency is normalized to USD at ingest; the original amount and currency stay in `raw`."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from ..models.schemas import Funder, Grant

log = logging.getLogger("sci.ingest")

# Indicative FX (USD per 1 unit), fixed for reproducibility. Refresh before a real deployment.
FX_AS_OF = "2026-10-01"
USD_PER: dict[str, float] = {
    "USD": 1.0, "THB": 1 / 33.0, "SGD": 1 / 1.30, "MYR": 1 / 4.25, "IDR": 1 / 16_300, "VND": 1 / 26_000,
    "PHP": 1 / 57.0, "EUR": 1.16, "GBP": 1.34, "JPY": 1 / 148.0, "KRW": 1 / 1_390, "AUD": 0.66, "CAD": 0.72,
    "CHF": 1.25, "INR": 1 / 88.0, "CNY": 1 / 7.1, "TWD": 1 / 30.5, "HKD": 1 / 7.8, "NZD": 0.59,
}


def to_usd(amount: float | None, currency: str | None) -> float | None:
    if amount is None:
        return None
    rate = USD_PER.get((currency or "USD").upper())
    if rate is None:
        log.warning("no FX rate for %s; leaving amount unnormalized", currency)
        return None
    return round(amount * rate, 2)


@dataclass
class Batch:
    source: str
    funders: list[Funder] = field(default_factory=list)
    grants: list[Grant] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Connector(Protocol):
    source: str

    def fetch(self) -> Batch: ...
