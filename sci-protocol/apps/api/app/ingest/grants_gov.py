"""Grants.gov Search2 + fetchOpportunity (public, no key). US federal opportunities.

API reference: https://www.grants.gov/api/common/search2 and .../fetchopportunity
Response shapes below follow the published docs; verify against a live call before relying on
them (brief §3.1) - every field access is defensive so a shape change degrades, not crashes.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import httpx

from ..models.schemas import Funder, Grant, funder_id, grant_id
from .base import Batch

log = logging.getLogger("sci.ingest.grants_gov")

BASE = "https://api.grants.gov/v1/api"

# One keyword query per taxonomy field; results are tagged with that field.
QUERIES: dict[str, str] = {
    "materials": "advanced materials",
    "agritech": "agricultural research",
    "biotech": "biotechnology",
    "energy": "clean energy research",
    "environmental": "environmental technology",
    "food_science": "food science",
    "manufacturing": "advanced manufacturing",
}

# Grants.gov eligibility codes -> our applicant types.
ELIGIBILITY: dict[str, list[str]] = {
    "06": ["university"],  # public institutions of higher education
    "20": ["university"],  # private institutions of higher education
    "21": ["individual"],
    "22": ["sme"],  # for-profits other than small businesses
    "23": ["startup", "sme"],  # small businesses
    "99": ["individual", "university", "startup", "sme", "consortium"],  # unrestricted
}


def _date(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%m/%d/%Y", "%b %d, %Y %I:%M:%S %p %Z", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt).replace(hour=23, minute=59, tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _num(v) -> float | None:
    try:
        n = float(str(v).replace(",", ""))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _strip_html(s: str | None) -> str | None:
    if not s:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()[:2000]


class GrantsGovConnector:
    source = "grants_gov"

    def __init__(self, rows_per_query: int = 25, fetch_details: bool = True, client: httpx.Client | None = None):
        self.rows = rows_per_query
        self.fetch_details = fetch_details
        self.http = client or httpx.Client(timeout=30)

    def search(self, keyword: str) -> list[dict]:
        r = self.http.post(
            f"{BASE}/search2",
            json={"keyword": keyword, "oppStatuses": "forecasted|posted", "rows": self.rows},
        )
        r.raise_for_status()
        body = r.json()
        if body.get("errorcode") not in (0, "0", None):
            raise RuntimeError(f"search2 error: {body.get('msg')}")
        return (body.get("data") or {}).get("oppHits") or []

    def detail(self, opp_id: str) -> dict:
        r = self.http.post(f"{BASE}/fetchOpportunity", json={"opportunityId": int(opp_id)})
        r.raise_for_status()
        return (r.json().get("data") or {})

    def fetch(self) -> Batch:
        batch = Batch(source=self.source)
        seen: dict[str, Grant] = {}
        funders: dict[str, Funder] = {}
        for field, kw in QUERIES.items():
            try:
                hits = self.search(kw)
            except Exception as ex:
                batch.errors.append(f"search '{kw}': {ex}")
                continue
            for h in hits:
                oid = str(h.get("id") or "")
                if not oid:
                    continue
                if oid in seen:
                    if field not in seen[oid].fields:
                        seen[oid].fields.append(field)
                    continue
                agency = h.get("agency") or h.get("agencyName") or h.get("agencyCode") or "US federal agency"
                fu = funders.setdefault(
                    agency, Funder(id=funder_id(agency), name=agency, type="government", country="US", website="https://www.grants.gov")
                )
                syn: dict = {}
                if self.fetch_details:
                    try:
                        syn = self.detail(oid).get("synopsis") or {}
                    except Exception as ex:
                        batch.errors.append(f"detail {oid}: {ex}")
                applicant_types = sorted(
                    {t for a in syn.get("applicantTypes") or [] for t in ELIGIBILITY.get(str(a.get("id")), [])}
                )
                elig_text = (syn.get("applicantEligibilityDesc") or "").lower()
                countries = ["*"] if "foreign" in elig_text and "not eligible" not in elig_text else ["US"]
                seen[oid] = Grant(
                    id=grant_id(self.source, oid),
                    funder_id=fu.id,
                    funder_name=fu.name,
                    funder_type="government",
                    title=h.get("title") or syn.get("opportunityTitle") or f"Opportunity {oid}",
                    summary=_strip_html(syn.get("synopsisDesc")),
                    source=self.source,
                    source_ref=oid,
                    url=f"https://www.grants.gov/search-results-detail/{oid}",
                    fields=[field],
                    eligible_countries=countries,
                    applicant_types=applicant_types,
                    requires_incorporation=None,
                    amount_min_usd=_num(syn.get("awardFloor")),
                    amount_max_usd=_num(syn.get("awardCeiling")),
                    currency="USD",
                    equity_taken=False,
                    deadline=_date(h.get("closeDate") or syn.get("responseDateStr")),
                    rolling=False,
                    cycle_note="Forecasted - dates may change" if h.get("oppStatus") == "forecasted" else None,
                    application_mode="portal",
                    verified=True,  # comes straight from the official source
                    confidence="high",
                    notes="US federal opportunity; most require US-registered applicants and SAM.gov/UEI registration.",
                    raw={"hit": h, "number": h.get("number"), "cfda": h.get("cfdaList")},
                )
        batch.funders = list(funders.values())
        batch.grants = list(seen.values())
        return batch
