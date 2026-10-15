"""Hand-curated corpus (data/seed/grants.yaml): Thai, SEA, deeptech and Web3 opportunities that have
no usable public API. This is the differentiator - nobody else has these structured."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from pathlib import Path

import yaml

from ..models import taxonomy
from ..models.schemas import Funder, Grant, funder_id, grant_id
from .base import Batch, to_usd


def _deadline(v) -> datetime | None:
    if v in (None, "", "null"):
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, date):
        return datetime.combine(v, time(23, 59), tzinfo=timezone.utc)
    return datetime.fromisoformat(str(v)).replace(tzinfo=timezone.utc)


class CuratedConnector:
    source = "curated"

    def __init__(self, path: Path):
        self.path = path

    def fetch(self) -> Batch:
        doc = yaml.safe_load(self.path.read_text())
        batch = Batch(source=self.source)
        funders: dict[str, Funder] = {}
        for f in doc.get("funders", []):
            funders[f["key"]] = Funder(
                id=funder_id(f["name"]), name=f["name"], type=f.get("type"), country=f.get("country"), website=f.get("website")
            )
        batch.funders = list(funders.values())

        for e in doc.get("grants", []):
            try:
                fu = funders[e["funder"]]
                amt = e.get("amount") or {}
                cur = amt.get("currency", "USD")
                trl = e.get("trl") or [None, None]
                fields = e.get("fields") or []
                unknown = [x for x in fields if x not in taxonomy.FIELDS]
                if unknown:
                    raise ValueError(f"unknown fields {unknown}")
                batch.grants.append(
                    Grant(
                        id=grant_id(self.source, e["ref"]),
                        funder_id=fu.id,
                        funder_name=fu.name,
                        funder_type=fu.type,
                        title=e["title"],
                        summary=e.get("summary"),
                        source=self.source,
                        source_ref=e["ref"],
                        url=e.get("url") or fu.website,
                        trl_min=trl[0],
                        trl_max=trl[1],
                        fields=fields,
                        eligible_countries=taxonomy.expand_countries(e.get("countries")),
                        applicant_types=e.get("applicant_types") or [],
                        requires_incorporation=e.get("requires_incorporation"),
                        ip_assignment_required=e.get("ip_assignment_required"),
                        amount_min_usd=to_usd(amt.get("min"), cur),
                        amount_max_usd=to_usd(amt.get("max"), cur),
                        currency=cur,
                        equity_taken=e.get("equity_taken"),
                        deadline=_deadline(e.get("deadline")),
                        rolling=bool(e.get("rolling", False)),
                        cycle_note=e.get("cycle"),
                        application_mode=e.get("application_mode"),
                        form_url=e.get("form_url"),
                        verified=bool(e.get("verified", False)),
                        confidence=e.get("confidence", "medium"),
                        notes=e.get("notes"),
                        raw={
                            "subdomains": e.get("subdomains") or [],
                            "amount_original": amt or None,
                            "countries_original": e.get("countries"),
                            "last_reviewed": str(e["last_reviewed"]) if e.get("last_reviewed") else None,
                            "form_note": e.get("form_note"),
                        },
                    )
                )
            except Exception as ex:  # one bad row must not take the corpus down
                batch.errors.append(f"{e.get('ref', '?')}: {ex}")
        return batch
