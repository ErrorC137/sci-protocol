"""Polite fetching: robots.txt (RFC 9309), a slow per-host pace, conditional GET, a size cap and a cache.

Funder sites are often small government servers. A crawler that hammers them gets the project blocked,
so the defaults are slow on purpose: one request per host every 5 s (or the site's Crawl-delay, if
longer), at most `max_pages` pages per watched site, and nothing outside the watch list.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urljoin, urlsplit

import httpx
from protego import Protego

from .sites import Site, canonical, same_site
from .textify import Doc, textify

log = logging.getLogger("sci.curate")

BOT = "SCIProtocolCorpusBot"
MAX_BYTES = 15 * 1024 * 1024
MAX_REDIRECTS = 5
STRIKES = 3  # consecutive 5xx/429 answers before a host is left alone for the rest of the run
SKIP_EXT = re.compile(r"\.(?:jpe?g|png|gif|svg|webp|ico|zip|rar|7z|mp4|mp3|avi|mov|xlsx?|pptx?|css|js)(?:\?|$)", re.I)


def user_agent(contact: str | None) -> str:
    return f"{BOT}/0.2 (research funding index{'; contact: ' + contact if contact else ''})"


class RobotsDenied(Exception):
    pass


class SkipURL(ValueError):
    """Not fetched on purpose: redirected outside the watched site, too many redirects, or host backing off."""


@dataclass
class Page:
    url: str
    final_url: str
    status: int
    content_type: str
    data: bytes
    fetched_at: str
    not_modified: bool = False  # 304: body served from the local cache


class Robots:
    """One origin's robots.txt decision. Matching (longest match, Allow wins ties, `*` and `$`, merged groups)
    is done by protego, because Python's stdlib parser before 3.13 gets RFC 9309 precedence wrong."""

    def __init__(self, text: str | None = None, *, allow_all: bool = False, disallow_all: bool = False):
        self.parser = Protego.parse(text) if text is not None else None
        self.allow_all, self.disallow_all = allow_all, disallow_all

    def can_fetch(self, url: str) -> bool:
        if self.disallow_all:
            return False
        if self.allow_all or self.parser is None:
            return True
        return self.parser.can_fetch(url, BOT)

    def crawl_delay(self) -> float | None:
        return self.parser.crawl_delay(BOT) if self.parser is not None else None


class PoliteFetcher:
    def __init__(
        self,
        cache_dir: Path,
        *,
        client: httpx.Client | None = None,
        contact: str | None = None,
        min_delay: float = 5.0,
        max_bytes: int = MAX_BYTES,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.cache_dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = client or httpx.Client(timeout=30, headers={"User-Agent": user_agent(contact)})
        self.client.headers.setdefault("User-Agent", user_agent(contact))
        self.min_delay, self.max_bytes, self.clock, self.sleep = min_delay, max_bytes, clock, sleep
        self._robots: dict[str, Robots] = {}
        self._last: dict[str, float] = {}
        self._strikes: Counter = Counter()
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()
        self._meta_path = cache_dir / "meta.json"
        self.meta: dict[str, dict] = json.loads(self._meta_path.read_text()) if self._meta_path.exists() else {}
        self.stats: Counter = Counter()

    # -- pacing -------------------------------------------------------------------------------------
    def _lock(self, host: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(host, threading.Lock())

    def _wait(self, host: str, origin: str | None = None) -> None:
        rp = self._robots.get(origin) if origin else None
        delay = max(self.min_delay, float((rp.crawl_delay() if rp else None) or 0))
        last = self._last.get(host)
        if last is not None:
            gap = self.clock() - last
            if gap < delay:
                self.sleep(delay - gap)
        self._last[host] = self.clock()

    # -- robots.txt ---------------------------------------------------------------------------------
    def robots(self, url: str) -> Robots:
        s = urlsplit(url)
        origin = f"{s.scheme}://{s.netloc}"
        if origin in self._robots:
            return self._robots[origin]
        try:
            self._wait(s.hostname or "")
            r = self.client.get(origin + "/robots.txt", follow_redirects=True)  # RFC 9309: follow up to 5 hops
            if r.status_code >= 500:
                rp = Robots(disallow_all=True)  # RFC 9309 §2.3.1.4: unreachable -> assume complete disallow
            elif r.status_code >= 400:
                rp = Robots(allow_all=True)  # §2.3.1.3: unavailable (404 etc.) -> crawling allowed
            else:
                rp = Robots(r.text)
        except httpx.HTTPError:
            rp = Robots(disallow_all=True)
        self._robots[origin] = rp
        return rp

    # -- fetch --------------------------------------------------------------------------------------
    def _cache_file(self, url: str) -> Path:
        return self.cache_dir / hashlib.sha256(url.encode()).hexdigest()

    def fetch(self, url: str, allowed: Callable[[str], bool] | None = None) -> Page:
        """GET with redirects followed by hand, so every hop gets the robots check, the watch-list check
        (`allowed`) and the per-host pace of the host it actually lands on."""
        current, conditional = url, True
        for _ in range(MAX_REDIRECTS + 1):
            result = self._get_once(current, url, conditional)
            if isinstance(result, Page):
                return result
            nxt = result
            if allowed is not None and not allowed(nxt):
                self.stats["offsite_redirect"] += 1
                raise SkipURL(f"{url}: redirected outside the watched site to {nxt}")
            current, conditional = nxt, False
        raise SkipURL(f"{url}: more than {MAX_REDIRECTS} redirects")

    def _get_once(self, current: str, original: str, conditional: bool) -> Page | str:
        s = urlsplit(current)
        if s.scheme not in ("http", "https") or not s.hostname:
            raise SkipURL(f"{current}: not an http(s) URL")
        host = s.hostname
        with self._lock(host):
            if self._strikes[host] >= STRIKES:
                raise SkipURL(f"{current}: {host} returned {STRIKES} server errors in a row; leaving it alone this run")
            rp = self.robots(current)
            if not rp.can_fetch(current):
                self.stats["robots_denied"] += 1
                raise RobotsDenied(current)
            headers, prev = {}, self.meta.get(original) if conditional else None
            cached = self._cache_file(original)
            if prev and cached.exists():
                if prev.get("etag"):
                    headers["If-None-Match"] = prev["etag"]
                if prev.get("last_modified"):
                    headers["If-Modified-Since"] = prev["last_modified"]
            self._wait(host, f"{s.scheme}://{s.netloc}")
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with self.client.stream("GET", current, headers=headers, follow_redirects=False) as r:
                if r.status_code in (301, 302, 303, 307, 308):
                    loc = r.headers.get("location")
                    if not loc:
                        raise SkipURL(f"{current}: redirect without a Location header")
                    return urljoin(current, loc)
                if r.status_code == 304 and prev and cached.exists():
                    self._strikes[host] = 0
                    self.stats["not_modified"] += 1
                    return Page(original, prev.get("final_url", current), 304, prev.get("content_type", ""), cached.read_bytes(), now, True)
                if r.status_code >= 500 or r.status_code == 429:
                    self._strikes[host] += 1
                r.raise_for_status()
                buf = bytearray()
                for chunk in r.iter_bytes():
                    buf += chunk
                    if len(buf) > self.max_bytes:
                        raise ValueError(f"{current}: larger than {self.max_bytes // 1_048_576} MB")
                page = Page(original, str(r.url), r.status_code, r.headers.get("content-type", ""), bytes(buf), now)
            self._strikes[host] = 0
            self.meta[original] = {"etag": r.headers.get("etag"), "last_modified": r.headers.get("last-modified"),
                                   "final_url": page.final_url, "content_type": page.content_type, "fetched_at": now}
            cached.write_bytes(page.data)
            self.stats["fetched"] += 1
            return page

    def save(self) -> None:
        self._meta_path.write_text(json.dumps(self.meta, indent=1, sort_keys=True))


@dataclass
class SiteResult:
    site: Site
    docs: list[Doc] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def crawl_site(fetcher: PoliteFetcher, site: Site) -> SiteResult:
    """Breadth-first from the watched URL, following same-site links whose path or anchor text looks
    like a call (DEFAULT_FOLLOW or the site's own `follow` patterns). `max_pages` caps *requests*, so a
    failing server is not hit once per queued link."""
    res = SiteResult(site)
    pats = site.follow_patterns()
    seen = {canonical(site.url)}
    queue: deque[tuple[str, int]] = deque([(site.url, 0)])
    on_site = lambda u: same_site(u, site.url)  # noqa: E731
    attempts = 0
    while queue and attempts < site.max_pages:
        url, depth = queue.popleft()
        attempts += 1
        try:
            doc = textify(fetcher.fetch(url, allowed=on_site))
        except RobotsDenied:
            res.errors.append(f"{url}: disallowed by robots.txt")
            continue
        except Exception as ex:  # HTTP errors, oversize, corrupt PDF/DOCX: one page must not end the run
            res.errors.append(f"{url}: {type(ex).__name__}: {ex}")
            continue
        res.docs.append(doc)
        if depth >= site.depth:
            continue
        for href, anchor in doc.links:
            try:
                key = canonical(href)
                if key in seen or SKIP_EXT.search(href) or not same_site(href, site.url):
                    continue
                parts = urlsplit(href)
            except ValueError:  # malformed link (bad port, broken IPv6 literal): skip just this link
                continue
            target = unquote(parts.path + ("?" + parts.query if parts.query else ""))  # not the host: "fund.go.th/about"
            if any(p.search(target) or p.search(anchor) for p in pats):
                seen.add(key)
                queue.append((href, depth + 1))
    return res


def crawl_all(fetcher: PoliteFetcher, sites: list[Site], workers: int = 6) -> list[SiteResult]:
    """Hosts are crawled in parallel; pages within one host strictly one at a time (per-host lock).
    A failure in one site is recorded against that site and never aborts the batch."""

    def safe(site: Site) -> SiteResult:
        try:
            return crawl_site(fetcher, site)
        except Exception as ex:
            log.exception("crawl of %s failed", site.url)
            return SiteResult(site, errors=[f"{site.url}: crawl aborted: {type(ex).__name__}: {ex}"])

    try:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            return list(pool.map(safe, sites))
    finally:
        fetcher.save()
