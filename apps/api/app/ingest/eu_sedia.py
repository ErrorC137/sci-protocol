"""EU Funding & Tenders Portal (SEDIA search API). Horizon Europe / EIC calls.

The API is public (apiKey=SEDIA) but its response shape is awkward: metadata values are arrays of
strings, budgets are JSON-in-a-string. Verify against a live call before demo day (brief §3.1).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import httpx

from ..models import taxonomy
from ..models.schemas import Funder, Grant, funder_id, grant_id
from .base import Batch, to_usd

URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
STATUS_OPEN, STATUS_FORTHCOMING = "31094502", "31094501"

KEYWORDS: dict[str, str] = {
    "materials": "advanced materials",
    "biotech": "biotechnology",
    "energy": "clean energy",
    "agritech": "agriculture innovation",
    "environmental": "circular economy",
    "food_science": "food systems",
    "digital": "deep tech",
}


def _first(meta: dict, key: str) -> str | None:
    v = meta.get(key)
    if isinstance(v, list):
        return str(v[0]) if v else None
    return str(v) if v is not None else None


def _deadline(meta: dict) -> datetime | None:
    s = _first(meta, "deadlineDate")
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("+0000", "+00:00").replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _budget(meta: dict) -> tuple[float | None, float | None]:
    """budgetOverview is a JSON string; per-action min/max contributions live several levels deep."""
    raw = _first(meta, "budgetOverview")
    if not raw:
        return None, None
    try:
        data = json.loads(raw)
    except ValueError:
        return None, None
    mins, maxs = [], []
    for actions in (data.get("budgetTopicActionMap") or {}).values():
        for a in actions or []:
            if a.get("minContribution"):
                mins.append(float(a["minContribution"]))
            if a.get("maxContribution"):
                maxs.append(float(a["maxContribution"]))
    return (to_usd(min(mins), "EUR") if mins else None, to_usd(max(maxs), "EUR") if maxs else None)


class EUSediaConnector:
    source = "eu_sedia"

    def __init__(self, page_size: int = 30, client: httpx.Client | None = None):
        self.page_size = page_size
        self.http = client or httpx.Client(timeout=30)

    def search(self, text: str) -> list[dict]:
        query = {
            "bool": {
                "must": [
                    {"terms": {"type": ["1", "2", "8"]}},  # calls for proposals / topics
                    {"terms": {"status": [STATUS_OPEN, STATUS_FORTHCOMING]}},
                ]
            }
        }
        r = self.http.post(
            URL,
            params={"apiKey": "SEDIA", "text": text, "pageSize": self.page_size, "pageNumber": 1},
            files={
                "query": ("blob", json.dumps(query), "application/json"),
                "languages": ("blob", json.dumps(["en"]), "application/json"),
                "sort": ("blob", json.dumps({"field": "sortStatus", "order": "ASC"}), "application/json"),
            },
        )
        r.raise_for_status()
        return r.json().get("results") or []

    def fetch(self) -> Batch:
        batch = Batch(source=self.source)
        fu = Funder(
            id=funder_id("European Commission"), name="European Commission", type="government", country="EU",
            website="https://ec.europa.eu/info/funding-tenders/opportunities/portal",
        )
        batch.funders = [fu]
        seen: dict[str, Grant] = {}
        for field, kw in KEYWORDS.items():
            try:
                results = self.search(kw)
            except Exception as ex:
                batch.errors.append(f"search '{kw}': {ex}")
                continue
            for res in results:
                meta = res.get("metadata") or {}
                ident = _first(meta, "identifier") or res.get("reference")
                if not ident:
                    continue
                if ident in seen:
                    if field not in seen[ident].fields:
                        seen[ident].fields.append(field)
                    continue
                lo, hi = _budget(meta)
                summary = res.get("summary") or _first(meta, "descriptionByte") or ""
                summary = re.sub(r"<[^>]+>", " ", summary)
                status = _first(meta, "status")
                seen[ident] = Grant(
                    id=grant_id(self.source, ident),
                    funder_id=fu.id,
                    funder_name=fu.name,
                    funder_type="government",
                    title=_first(meta, "title") or res.get("title") or ident,
                    summary=re.sub(r"\s+", " ", summary).strip()[:2000] or None,
                    source=self.source,
                    source_ref=ident,
                    url=f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{ident.lower()}",
                    fields=[field],
                    eligible_countries=taxonomy.expand_countries(["HE_ELIGIBLE"]),
                    applicant_types=["university", "startup", "sme", "consortium"],
                    amount_min_usd=lo,
                    amount_max_usd=hi,
                    currency="EUR",
                    equity_taken=False,
                    deadline=_deadline(meta),
                    cycle_note="Forthcoming" if status == STATUS_FORTHCOMING else None,
                    application_mode="portal",
                    verified=True,
                    confidence="medium",
                    notes="Entities outside EU/associated countries can often join consortia but are usually not funded - check the call's eligibility annex.",
                    raw={"identifier": ident, "status": status, "callIdentifier": _first(meta, "callIdentifier")},
                )
        batch.grants = list(seen.values())
        return batch
