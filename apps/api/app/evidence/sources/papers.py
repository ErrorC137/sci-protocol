"""Literature sources: OpenAlex, Crossref, Semantic Scholar, arXiv.

Request/response shapes follow each API's documentation and the maintained client libraries
(pyalex 0.21, semanticscholar 0.12); they could not be exercised live from the build sandbox, so run
`python -m app.evidence.smoke` once network access and keys are in place.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ...config import settings
from ..models import Reference
from .base import SearchQuery, Source, doi_key, parse_date, strip_tags


def invert_abstract(inv: dict | None) -> str | None:
    """OpenAlex ships abstracts as {word: [positions]} (publisher licensing); rebuild the text."""
    if not inv:
        return None
    pos = sorted((i, w) for w, idxs in inv.items() for i in idxs)
    return " ".join(w for _, w in pos)


class OpenAlex(Source):
    name, kind, needs_key = "openalex", "papers", True
    URL = "https://api.openalex.org/works"

    def configured(self):
        # Keys became mandatory in Feb 2026 with usage-based pricing (search calls are metered).
        return (True, None) if settings.openalex_api_key else (False, "set OPENALEX_API_KEY (free key, metered usage)")

    def search(self, q: SearchQuery) -> list[Reference]:
        params = {"search": q.text, "per-page": min(q.limit, 200),
                  "select": "id,doi,display_name,publication_date,abstract_inverted_index,primary_location,"
                            "authorships,cited_by_count,type"}
        if q.until:
            params["filter"] = f"to_publication_date:{q.until.isoformat()}"
        headers = {"Authorization": f"Bearer {settings.openalex_api_key}"}
        if settings.evidence_mailto:
            headers["From"] = settings.evidence_mailto
        return self.parse(self.request("GET", self.URL, params=params, headers=headers).json())

    @staticmethod
    def parse(data: dict) -> list[Reference]:
        out = []
        for w in data.get("results", []):
            loc = (w.get("primary_location") or {})
            src = (loc.get("source") or {})
            key = doi_key(w.get("doi")) or f"openalex:{str(w.get('id', '')).rsplit('/', 1)[-1]}"
            out.append(Reference(
                key=key, kind="preprint" if w.get("type") == "preprint" else "paper", source="openalex",
                title=w.get("display_name") or "(untitled)", abstract=invert_abstract(w.get("abstract_inverted_index")),
                date=parse_date(w.get("publication_date")), venue=src.get("display_name"),
                authors=[(a.get("author") or {}).get("display_name", "") for a in (w.get("authorships") or [])][:8],
                url=w.get("doi") or loc.get("landing_page_url") or w.get("id"), cited_by=w.get("cited_by_count"),
            ))
        return out


class Crossref(Source):
    name, kind = "crossref", "papers"
    URL = "https://api.crossref.org/works"

    def search(self, q: SearchQuery) -> list[Reference]:
        params = {"query.bibliographic": q.text, "rows": min(q.limit, 100),
                  "select": "DOI,title,abstract,issued,container-title,author,is-referenced-by-count,URL,type"}
        if q.until:
            params["filter"] = f"until-pub-date:{q.until.isoformat()}"
        if settings.evidence_mailto:
            params["mailto"] = settings.evidence_mailto
        return self.parse(self.request("GET", self.URL, params=params).json())

    @staticmethod
    def parse(data: dict) -> list[Reference]:
        out = []
        for it in (data.get("message") or {}).get("items", []):
            key = doi_key(it.get("DOI"))
            if not key:
                continue
            out.append(Reference(
                key=key, kind="preprint" if it.get("type") == "posted-content" else "paper", source="crossref",
                title=(it.get("title") or ["(untitled)"])[0], abstract=strip_tags(it.get("abstract")),
                date=parse_date(((it.get("issued") or {}).get("date-parts") or [[None]])[0]),
                venue=(it.get("container-title") or [None])[0],
                authors=[" ".join(x for x in (a.get("given"), a.get("family")) if x) for a in (it.get("author") or [])][:8],
                url=it.get("URL"), cited_by=it.get("is-referenced-by-count"),
            ))
        return out


class SemanticScholar(Source):
    name, kind = "semantic_scholar", "papers"
    URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def search(self, q: SearchQuery) -> list[Reference]:
        params = {"query": q.text, "limit": min(q.limit, 100),
                  "fields": "title,abstract,year,publicationDate,externalIds,url,venue,authors,citationCount"}
        if q.until:
            params["publicationDateOrYear"] = f":{q.until.isoformat()}"
        headers = {"x-api-key": settings.s2_api_key} if settings.s2_api_key else {}
        return self.parse(self.request("GET", self.URL, params=params, headers=headers).json())

    @staticmethod
    def parse(data: dict) -> list[Reference]:
        out = []
        for p in data.get("data") or []:
            ext = p.get("externalIds") or {}
            key = doi_key(ext.get("DOI")) or (f"arxiv:{ext['ArXiv']}" if ext.get("ArXiv") else f"s2:{p.get('paperId')}")
            out.append(Reference(
                key=key, kind="preprint" if key.startswith("arxiv:") else "paper", source="semantic_scholar",
                title=p.get("title") or "(untitled)", abstract=p.get("abstract"),
                date=parse_date(p.get("publicationDate") or p.get("year")), venue=p.get("venue") or None,
                authors=[a.get("name", "") for a in (p.get("authors") or [])][:8], url=p.get("url"),
                cited_by=p.get("citationCount"),
            ))
        return out


class ArXiv(Source):
    name, kind = "arxiv", "papers"
    URL = "https://export.arxiv.org/api/query"
    NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    def search(self, q: SearchQuery) -> list[Reference]:
        words = [w for w in re.findall(r"[A-Za-z0-9]+", q.text) if len(w) > 2][:8]
        query = " AND ".join(f"all:{w}" for w in words) or "all:battery"
        if q.until:
            query += f" AND submittedDate:[190001010000 TO {q.until.strftime('%Y%m%d')}2359]"
        params = {"search_query": query, "start": 0, "max_results": min(q.limit, 50), "sortBy": "relevance"}
        return self.parse(self.request("GET", self.URL, params=params).text)

    @classmethod
    def parse(cls, xml: str) -> list[Reference]:
        out = []
        root = ET.fromstring(xml)
        for e in root.findall("a:entry", cls.NS):
            raw_id = (e.findtext("a:id", "", cls.NS) or "").rsplit("/abs/", 1)[-1]
            aid = re.sub(r"v\d+$", "", raw_id)
            doi = e.findtext("arxiv:doi", None, cls.NS)
            out.append(Reference(
                key=doi_key(doi) or f"arxiv:{aid}", kind="preprint", source="arxiv",
                title=re.sub(r"\s+", " ", e.findtext("a:title", "", cls.NS)).strip(),
                abstract=re.sub(r"\s+", " ", e.findtext("a:summary", "", cls.NS)).strip(),
                date=parse_date((e.findtext("a:published", "", cls.NS) or "")[:10]),
                authors=[a.findtext("a:name", "", cls.NS) for a in e.findall("a:author", cls.NS)][:8],
                url=f"https://arxiv.org/abs/{aid}",
            ))
        return out
