"""Patent sources: EPO OPS (worldwide bibliographic + EP/WO claims), PatentsView PatentSearch (US),
Lens.org, and a local corpus exported from Google Patents Public Data on BigQuery.

Verification status, stated plainly:
  * EPO OPS parsing is tested against real OPS XML responses (fixtures from the Apache-2.0
    patent_client project, see tests/fixtures/evidence/epo/NOTICE).
  * PatentsView and Lens request/response shapes follow their public docs and could not be exercised
    from the build sandbox; PatentsView key issuance was reported paused in 2026. Run
    `python -m app.evidence.smoke` before relying on either.
  * The local corpus is whatever you export with scripts/patent_corpus.sql - nothing is bundled.
"""

from __future__ import annotations

import json
import math
import re
import threading
import time
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from pathlib import Path

from ...config import settings
from .. import chem
from ..models import Reference
from .base import SearchQuery, Source, SourceError, parse_date, patent_key

NS = {"ops": "http://ops.epo.org", "epo": "http://www.epo.org/exchange", "ft": "http://www.epo.org/fulltext"}


def _words(text: str, n: int) -> list[str]:
    seen, out = set(), []
    for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]+", text):
        lw = w.lower()
        if len(lw) > 2 and lw not in chem._STOP and lw not in seen:
            seen.add(lw)
            out.append(w)
    return out[:n]


# --- EPO Open Patent Services ------------------------------------------------------------------------
class EpoOps(Source):
    name, kind, needs_key = "epo_ops", "patents", True
    AUTH = "https://ops.epo.org/3.2/auth/accesstoken"
    SEARCH = "https://ops.epo.org/3.2/rest-services/published-data/search/biblio"
    CLAIMS = "https://ops.epo.org/3.2/rest-services/published-data/publication/docdb/{n}/claims"

    _token: tuple[str, float] | None = None
    _lock = threading.Lock()

    def configured(self):
        ok = bool(settings.epo_ops_key and settings.epo_ops_secret)
        return (True, None) if ok else (False, "set EPO_OPS_KEY and EPO_OPS_SECRET (free registration, weekly fair-use quota)")

    def token(self) -> str:
        with self._lock:
            if EpoOps._token and EpoOps._token[1] > time.time() + 30:
                return EpoOps._token[0]
            r = self.request("POST", self.AUTH, data={"grant_type": "client_credentials"},
                             auth=(settings.epo_ops_key, settings.epo_ops_secret))
            j = r.json()
            EpoOps._token = (j["access_token"], time.time() + float(j.get("expires_in", 1200)))
            return EpoOps._token[0]

    @staticmethod
    def cql(q: SearchQuery) -> str:
        parts = [f'ta all "{" ".join(_words(q.text, 8))}"']
        if q.cpc:
            parts.append("(" + " or ".join(f"cpc={c.replace(' ', '')}" for c in q.cpc[:6]) + ")")
        if q.until:
            parts.append(f'pd within "19000101 {q.until.strftime("%Y%m%d")}"')
        return " and ".join(parts)

    def search(self, q: SearchQuery) -> list[Reference]:
        r = self.request("GET", self.SEARCH, params={"q": self.cql(q), "Range": f"1-{min(q.limit, 100)}"},
                         headers={"Authorization": f"Bearer {self.token()}", "Accept": "application/xml"})
        return self.parse_biblio(r.text)

    def claims(self, ref: Reference) -> list[str]:
        """Claims for EP/WO publications (OPS full text covers a limited set of offices)."""
        m = re.fullmatch(r"pat:([A-Z]{2})(\d+)([A-Z]\d?)", ref.key)
        if not m or m.group(1) not in ("EP", "WO"):
            return []
        n = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
        try:
            r = self.request("GET", self.CLAIMS.format(n=n), headers={"Authorization": f"Bearer {self.token()}"})
        except SourceError:
            return []
        return self.parse_claims(r.text)

    @staticmethod
    def parse_biblio(xml: str) -> list[Reference]:
        out = []
        for d in ET.fromstring(xml).iter(f"{{{NS['epo']}}}exchange-document"):
            cc, num, kind = d.get("country"), d.get("doc-number"), d.get("kind")
            b = d.find("epo:bibliographic-data", NS)
            if b is None:
                continue
            title = b.findtext('epo:invention-title[@lang="en"]', None, NS) or b.findtext("epo:invention-title", "", NS)
            ab = d.find('.//epo:abstract[@lang="en"]', NS)
            abstract = " ".join("".join(p.itertext()).strip() for p in ab.findall("epo:p", NS)) if ab is not None else None
            pub = b.findtext('epo:publication-reference/epo:document-id[@document-id-type="docdb"]/epo:date', None, NS)
            prio = [parse_date(x.text) for x in b.findall(".//epo:priority-claim/epo:document-id/epo:date", NS)]
            prio = [p for p in prio if p]
            cpc = []
            for pc in b.findall(".//epo:patent-classifications/epo:patent-classification", NS):
                f = lambda t: (pc.findtext(f"epo:{t}", "", NS) or "").strip()  # noqa: E731
                code = f"{f('section')}{f('class')}{f('subclass')}{f('main-group')}/{f('subgroup')}"
                if len(code) > 5 and code not in cpc:
                    cpc.append(code)
            applicants = [re.sub(r"\s*\[[A-Z]{2}\]$", "", re.sub(r"\s+", " ", n.text)).strip()
                          for n in b.findall('.//epo:applicant[@data-format="epodoc"]//epo:name', NS) if n.text]
            out.append(Reference(
                key=patent_key(cc, num, kind), kind="patent", source="epo_ops", title=(title or "(untitled)").strip(),
                abstract=abstract, date=parse_date(pub), priority_date=min(prio) if prio else None, cpc=cpc,
                assignees=applicants[:5], country=cc, family_id=d.get("family-id"),
                url=f"https://worldwide.espacenet.com/patent/search?q=pn%3D{cc}{num}{kind}",
            ))
        return out

    @staticmethod
    def parse_claims(xml: str) -> list[str]:
        root = ET.fromstring(xml)
        blocks = root.findall(".//ft:claims", NS)
        en = [c for c in blocks if (c.get("lang") or "").upper() == "EN"] or blocks
        if not en:
            return []
        return [re.sub(r"\s+", " ", "".join(t.itertext())).strip() for t in en[0].iter(f"{{{NS['ft']}}}claim-text")]


# --- PatentsView PatentSearch API (US) ----------------------------------------------------------------
class PatentsView(Source):
    name, kind, needs_key = "patentsview", "patents", True
    URL = "https://search.patentsview.org/api/v1/patent/"

    def configured(self):
        return (True, None) if settings.patentsview_api_key else (False, "set PATENTSVIEW_API_KEY (issuance reported paused in 2026)")

    def search(self, q: SearchQuery) -> list[Reference]:
        words = " ".join(_words(q.text, 5))
        cond = [{"_text_all": {"patent_abstract": words}}]
        if q.until:
            cond.append({"_lte": {"patent_date": q.until.isoformat()}})
        body = {"q": {"_and": cond} if len(cond) > 1 else cond[0],
                "f": ["patent_id", "patent_title", "patent_abstract", "patent_date",
                      "assignees.assignee_organization", "cpc_current.cpc_group_id"],
                "o": {"size": min(q.limit, 100)}}
        r = self.request("POST", self.URL, json=body, headers={"X-Api-Key": settings.patentsview_api_key})
        return self.parse(r.json())

    @staticmethod
    def parse(data: dict) -> list[Reference]:
        out = []
        for p in data.get("patents") or []:
            pid = str(p.get("patent_id") or "")
            out.append(Reference(
                key=patent_key("US", pid), kind="patent", source="patentsview", title=p.get("patent_title") or "(untitled)",
                abstract=p.get("patent_abstract"), date=parse_date(p.get("patent_date")), country="US",
                assignees=[a.get("assignee_organization") for a in (p.get("assignees") or []) if a.get("assignee_organization")][:5],
                cpc=sorted({c.get("cpc_group_id") for c in (p.get("cpc_current") or []) if c.get("cpc_group_id")}),
                url=f"https://patents.google.com/patent/US{pid}",
            ))
        return out


# --- Lens.org -----------------------------------------------------------------------------------------
class Lens(Source):
    name, kind, needs_key = "lens", "patents", True
    URL = "https://api.lens.org/patent/search"

    def configured(self):
        return (True, None) if settings.lens_api_token else (False, "set LENS_API_TOKEN (access is approval-gated)")

    def search(self, q: SearchQuery) -> list[Reference]:
        must = {"query_string": {"query": " ".join(_words(q.text, 10)), "fields": ["title", "abstract", "claims"],
                                 "default_operator": "and"}}
        query = {"bool": {"must": [must]}}
        if q.until:
            query["bool"]["filter"] = [{"range": {"date_published": {"lte": q.until.isoformat()}}}]
        body = {"query": query, "size": min(q.limit, 100),
                "include": ["lens_id", "jurisdiction", "doc_number", "kind", "date_published", "biblio", "abstract",
                            "claims", "families", "legal_status"]}
        r = self.request("POST", self.URL, json=body, headers={"Authorization": f"Bearer {settings.lens_api_token}"})
        return self.parse(r.json())

    @staticmethod
    def _en(items) -> str | None:
        items = items or []
        en = [i for i in items if (i.get("lang") or "").lower() == "en"] or items
        return en[0].get("text") if en else None

    @classmethod
    def parse(cls, data: dict) -> list[Reference]:
        out = []
        for p in data.get("data") or []:
            bib = p.get("biblio") or {}
            claims = []
            for block in p.get("claims") or []:
                if (block.get("lang") or "en").lower() != "en" and claims:
                    continue
                for c in block.get("claims") or []:
                    claims.append(" ".join(c.get("claim_text") or []))
            cpc = [c.get("symbol") for c in ((bib.get("classifications_cpc") or {}).get("classifications") or []) if c.get("symbol")]
            applicants = [((a.get("extracted_name") or {}).get("value")) for a in ((bib.get("parties") or {}).get("applicants") or [])]
            prio = ((bib.get("priority_claims") or {}).get("earliest_claim") or {}).get("date")
            status = (p.get("legal_status") or {}).get("patent_status")
            out.append(Reference(
                key=patent_key(p.get("jurisdiction"), p.get("doc_number"), p.get("kind")), kind="patent", source="lens",
                title=cls._en(bib.get("invention_title")) or "(untitled)", abstract=cls._en(p.get("abstract")),
                claims=[c for c in claims if c][:30], date=parse_date(p.get("date_published")), priority_date=parse_date(prio),
                cpc=cpc[:20], assignees=[a for a in applicants if a][:5], country=p.get("jurisdiction"),
                url=f"https://www.lens.org/lens/patent/{p.get('lens_id')}" if p.get("lens_id") else None,
                venue=f"legal status: {status}" if status else None,
            ))
        return out


# --- Local corpus (Google Patents Public Data export) -------------------------------------------------
class LocalCorpus(Source):
    """BM25 over title + abstract + claims of a JSONL export (scripts/patent_corpus.sql), with
    chemistry-normalised tokens, CPC boost and a publication-date filter. Loaded once per process."""

    name, kind = "local", "patents"
    _cache: dict[str, tuple] = {}

    def __init__(self, path: Path | None = None, client=None):
        super().__init__(client)
        self.path = path or settings.patent_corpus

    def configured(self):
        if not self.path:
            return False, "no local corpus: export one with scripts/patent_corpus.sql and set PATENT_CORPUS"
        if not Path(self.path).exists():
            return False, f"PATENT_CORPUS file not found: {self.path}"
        return True, None

    def _load(self):
        key = f"{self.path}:{Path(self.path).stat().st_mtime}"
        if key in self._cache:
            return self._cache[key]
        refs, docs, df = [], [], Counter()
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = self.row(json.loads(line))
                toks = Counter()
                for t in chem.tokens(r.text()):
                    toks[t] += 1
                refs.append(r)
                docs.append(toks)
                df.update(toks.keys())
        avg = sum(sum(d.values()) for d in docs) / max(1, len(docs))
        self._cache[key] = (refs, docs, df, avg)
        return self._cache[key]

    @staticmethod
    def row(j: dict) -> Reference:
        pub = str(j.get("publication_number") or "")
        m = re.fullmatch(r"([A-Z]{2})-?(\w+?)-?([A-Z]\d?)?", pub)
        cc, num, kind = (m.group(1), m.group(2), m.group(3)) if m else (j.get("country_code"), pub, j.get("kind_code"))
        claims = j.get("claims")
        claims = claims if isinstance(claims, list) else ([claims] if claims else [])
        return Reference(
            key=patent_key(cc, num, kind), kind="patent", source="local", title=j.get("title") or "(untitled)",
            abstract=j.get("abstract"), claims=claims, date=parse_date(j.get("publication_date")),
            priority_date=parse_date(j.get("priority_date")), cpc=list(j.get("cpc") or [])[:30],
            assignees=list(j.get("assignees") or [])[:5], country=cc, family_id=str(j.get("family_id") or "") or None,
            url=f"https://patents.google.com/patent/{cc}{num}{kind or ''}", fixture=bool(j.get("_fixture")),
        )

    def search(self, q: SearchQuery) -> list[Reference]:
        refs, docs, df, avg = self._load()
        qt = chem.tokens(q.text)
        n, k1, b = len(docs), 1.4, 0.75
        cpc = tuple(c.replace(" ", "") for c in q.cpc)
        scored = []
        for r, d in zip(refs, docs):
            if q.until and r.date and r.date >= q.until:
                continue
            dl = sum(d.values())
            s = sum(math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) * d[t] * (k1 + 1) / (d[t] + k1 * (1 - b + b * dl / avg))
                    for t in qt if t in d)
            if s and cpc and any(c.startswith(cpc) for c in r.cpc):
                s *= 1.25
            if s:
                scored.append((s, r))
        scored.sort(key=lambda x: -x[0])
        top = scored[: q.limit]
        hi = top[0][0] if top else 1
        return [r.model_copy(update={"score": round(s / hi, 3)}) for s, r in top]


def date_before(a: date | None, b: date | None) -> bool | None:
    return None if a is None or b is None else a < b
