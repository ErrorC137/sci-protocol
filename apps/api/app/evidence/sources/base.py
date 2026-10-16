"""Source adapter contract, shared HTTP behaviour and id normalisation.

Every adapter turns one SearchQuery into Reference objects and NEVER hides a failure: the engine records
`ok | empty | error | no_key | disabled | unreachable` per source, with the exact queries sent, so a
report always says what was and was not searched (MatDAO's dead sources failed silently).
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date

import httpx

from ...config import settings
from ..models import Reference, SourceStatus

log = logging.getLogger("sci.evidence")


@dataclass
class SearchQuery:
    text: str  # free-text query; only non-confidential terms (see engine.build_queries)
    phrases: list[str] = field(default_factory=list)  # key phrases for APIs with boolean syntax
    cpc: list[str] = field(default_factory=list)
    until: date | None = None  # priority date: prior art must be published before it
    limit: int = 25


class SourceError(Exception):
    def __init__(self, state: str, detail: str):
        super().__init__(detail)
        self.state, self.detail = state, detail


class Source:
    name = "base"
    kind = "papers"  # papers | patents
    needs_key = False

    def __init__(self, client: httpx.Client | None = None):
        self._client = client

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            contact = f" (mailto:{settings.evidence_mailto})" if settings.evidence_mailto else ""
            self._client = httpx.Client(timeout=25, follow_redirects=True,
                                        headers={"User-Agent": f"SCIProtocolEvidence/0.1{contact}"})
        return self._client

    def configured(self) -> tuple[bool, str | None]:
        return True, None

    def search(self, q: SearchQuery) -> list[Reference]:  # pragma: no cover - interface
        raise NotImplementedError

    # -- helpers ------------------------------------------------------------------------------------
    def request(self, method: str, url: str, **kw) -> httpx.Response:
        """One retry on 429/5xx (honouring a short Retry-After). Errors become SourceError."""
        for attempt in (0, 1):
            try:
                r = self.client.request(method, url, **kw)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ProxyError) as ex:
                raise SourceError("unreachable", f"cannot reach {httpx.URL(url).host}: {type(ex).__name__}") from ex
            except httpx.HTTPError as ex:
                raise SourceError("error", f"{type(ex).__name__}: {ex}") from ex
            if r.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                ra = r.headers.get("retry-after", "")
                time.sleep(min(float(ra), 5.0) if re.fullmatch(r"\d+(\.\d+)?", ra) else 2.0)
                continue
            if r.status_code in (401, 403):
                raise SourceError("no_key" if self.needs_key else "error", f"HTTP {r.status_code}: key missing, invalid or not permitted")
            if r.status_code == 429:
                raise SourceError("error", "rate limited (HTTP 429)")
            if r.status_code >= 400:
                raise SourceError("error", f"HTTP {r.status_code}: {r.text[:200]}")
            return r
        raise SourceError("error", "retries exhausted")


def run(src: Source, q: SearchQuery) -> tuple[SourceStatus, list[Reference]]:
    ok, why = src.configured()
    if not ok:
        return SourceStatus(source=src.name, state="no_key", detail=why, queries=[q.text]), []
    t0 = time.monotonic()
    try:
        refs = src.search(q)
    except SourceError as ex:
        return SourceStatus(source=src.name, state=ex.state, detail=ex.detail, queries=[q.text],
                            ms=int((time.monotonic() - t0) * 1000)), []
    except Exception as ex:  # a malformed response must not take the report down
        log.exception("source %s failed", src.name)
        return SourceStatus(source=src.name, state="error", detail=f"{type(ex).__name__}: {ex}", queries=[q.text],
                            ms=int((time.monotonic() - t0) * 1000)), []
    for r in refs:
        r.source = src.name
    return SourceStatus(source=src.name, state="ok" if refs else "empty", hits=len(refs), queries=[q.text],
                        ms=int((time.monotonic() - t0) * 1000)), refs


# --- identifiers -------------------------------------------------------------------------------------
def doi_key(doi: str | None) -> str | None:
    if not doi:
        return None
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", doi.strip(), flags=re.I).lower()
    return f"doi:{d}" if d.startswith("10.") else None


def patent_key(country: str | None, number: str | None, kind: str | None = None) -> str | None:
    if not number:
        return None
    n = re.sub(r"[\s\-/,.]", "", f"{country or ''}{number}{kind or ''}").upper()
    return f"pat:{n}"


def parse_date(v) -> date | None:
    """'2021-05-04', '20210504', 20210504, '2021', [2021, 5, 4] -> date (year-only -> Jan 1, flagged by caller)."""
    if v in (None, "", 0):
        return None
    if isinstance(v, list):
        parts = [int(x) for x in v if x is not None] + [1, 1]
        try:
            return date(parts[0], parts[1], parts[2])
        except (ValueError, IndexError):
            return None
    s = str(v).strip()
    try:
        if re.fullmatch(r"\d{8}", s):
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        if re.fullmatch(r"\d{4}", s):
            return date(int(s), 1, 1)
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def strip_tags(s: str | None) -> str | None:
    if not s:
        return s
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()
