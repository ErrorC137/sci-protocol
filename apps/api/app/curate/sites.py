"""The list of pages to watch. The crawler never goes beyond it (plus same-site links one hop deep).

Accepted formats, so a list of 100+ sites can be pasted in whatever shape it arrives:
    sites.yaml   sites: [ "https://...", {url: ..., funder: nia, follow: [...], max_pages: 20} ]
    sites.csv    url,funder,name,follow,max_pages      (follow = ;-separated regexes)
    sites.txt    one URL per line, optional "| funder_key", # comments
"""

from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yaml

# Links worth following from a watched page: in the URL or in the anchor text.
DEFAULT_FOLLOW = [
    r"grant", r"fund", r"call", r"proposal", r"apply", r"application", r"programme|program\b", r"accelerat",
    r"incubat", r"competition", r"challenge", r"prize", r"fellowship", r"open innovation",
    r"ทุน", r"ประกาศ", r"ข้อเสนอ", r"รับสมัคร", r"สนับสนุน", r"แหล่งทุน", r"เปิดรับ",
]


@dataclass
class Site:
    url: str
    funder: str | None = None  # funder key in grants.yaml; unknown funders are proposed as new
    name: str | None = None
    follow: list[str] = field(default_factory=list)
    max_pages: int = 12
    depth: int = 1
    notes: str | None = None

    @property
    def host(self) -> str:
        return urlsplit(self.url).hostname or ""

    def follow_patterns(self) -> list[re.Pattern]:
        return [re.compile(p, re.I) for p in (self.follow or DEFAULT_FOLLOW)]


def canonical(url: str) -> str:
    """Comparable form of a URL: no fragment, no tracking params, lower-case host, no trailing slash."""
    s = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(s.query, keep_blank_values=True) if not k.lower().startswith("utm_")])
    path = s.path.rstrip("/") or "/"
    return urlunsplit((s.scheme.lower(), (s.hostname or "") + (f":{s.port}" if s.port else ""), path, query, ""))


def site_key(host: str) -> str:
    return host.lower().removeprefix("www.")


def same_site(url: str, base: str) -> bool:
    """Same host or a subdomain of it (agencies often serve call PDFs from a files.* or www2.* host)."""
    h, b = site_key(urlsplit(url).hostname or ""), site_key(urlsplit(base).hostname or "")
    return bool(h) and (h == b or h.endswith("." + b))


def _site(raw) -> Site:
    if isinstance(raw, str):
        return Site(url=raw.strip())
    known = {k: raw[k] for k in ("url", "funder", "name", "follow", "max_pages", "depth", "notes") if raw.get(k) not in (None, "")}
    if isinstance(known.get("follow"), str):
        known["follow"] = [p for p in known["follow"].split(";") if p.strip()]
    for k in ("max_pages", "depth"):
        if k in known:
            known[k] = int(known[k])
    return Site(**known)


def load_sites(path: Path) -> list[Site]:
    text = path.read_text(encoding="utf-8-sig")  # Excel's 'CSV UTF-8' starts with a byte-order mark
    if path.suffix in (".yaml", ".yml"):
        doc = yaml.safe_load(text) or {}
        raws = doc.get("sites", []) if isinstance(doc, dict) else doc
    elif path.suffix == ".csv":
        raws = list(csv.DictReader(text.splitlines()))
    else:
        raws = []
        for line in text.splitlines():
            line = re.split(r"\s+#", line.strip(), maxsplit=1)[0]  # trailing " # comment"; a URL's #fragment stays
            if not line or line.startswith("#"):
                continue
            url, _, funder = (p.strip() for p in line.partition("|"))
            raws.append({"url": url, "funder": funder or None})
    out, seen, problems = [], set(), []
    for raw in raws:
        if isinstance(raw, dict) and not str(raw.get("url") or "").strip():
            problems.append(f"row without a url: {dict(raw)}")
            continue
        s = _site(raw)
        if urlsplit(s.url).scheme not in ("http", "https") or not s.host:
            problems.append(s.url)
            continue
        key = canonical(s.url)
        if key not in seen:
            seen.add(key)
            out.append(s)
    if problems:
        raise ValueError(f"not http(s) URLs: {problems[:5]}{' ...' if len(problems) > 5 else ''}")
    return out


def sites_from_corpus(seed_path: Path) -> list[Site]:
    """Start the watch list from the funders already in the corpus."""
    doc = yaml.safe_load(seed_path.read_text(encoding="utf-8"))
    return [Site(url=f["website"], funder=f["key"], name=f["name"]) for f in doc.get("funders", []) if f.get("website")]


def dump_sites(sites: list[Site], path: Path) -> None:
    rows = []
    for s in sites:
        d = {k: v for k, v in asdict(s).items() if v not in (None, [], "")}
        if d.get("max_pages") == 12:
            d.pop("max_pages")
        if d.get("depth") == 1:
            d.pop("depth")
        rows.append(d)
    header = ("# Pages the corpus crawler watches. Add funders' call/news pages, not just home pages.\n"
              "# Fields: url (required), funder (key in data/seed/grants.yaml), follow (regexes for links to\n"
              "# follow one hop), max_pages (default 12), depth (default 1), notes.\n")
    path.write_text(header + yaml.safe_dump({"sites": rows}, allow_unicode=True, sort_keys=False), encoding="utf-8")
