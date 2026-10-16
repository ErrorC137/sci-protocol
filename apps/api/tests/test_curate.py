"""Corpus curation pipeline, offline: an httpx MockTransport stands in for funder sites."""

import shutil
from datetime import date
from pathlib import Path

import httpx
import pytest
import yaml

from app.curate import extract as ex
from app.curate import review
from app.curate.__main__ import run
from app.curate.crawl import Page, PoliteFetcher, RobotsDenied
from app.curate.sites import load_sites, same_site
from app.curate.textify import textify
from app.ingest.curated import CuratedConnector

TODAY = date(2026, 1, 15)

CALL_TH = """<html><head><meta charset="windows-874">
<title>ประกาศรับข้อเสนอโครงการนวัตกรรมวัสดุหมุนเวียน ปี 2569</title></head><body>
<h1>ประกาศรับข้อเสนอโครงการนวัตกรรมวัสดุหมุนเวียน ปี 2569</h1>
<p>กองทุนตัวอย่างเพื่อนวัตกรรม เปิดรับข้อเสนอโครงการตั้งแต่วันที่ 1 มกราคม 2569
ปิดรับข้อเสนอภายในวันที่ ๓๑ มีนาคม ๒๕๖๙ เวลา 16.30 น.</p>
<p>สนับสนุนทุนวิจัยวงเงินไม่เกิน 1.5 ล้านบาทต่อโครงการ สำหรับนิติบุคคลที่จดทะเบียนในประเทศไทย
ที่พัฒนาวัสดุจากของเสียอุตสาหกรรมหรือวัสดุแบตเตอรี่ที่นำกลับมาใช้ใหม่ ระดับความพร้อมทางเทคโนโลยี TRL 4 ขึ้นไป</p>
<p><a href="/files/form.docx">ดาวน์โหลดแบบฟอร์มข้อเสนอโครงการ</a></p>
</body></html>"""

HOME = """<html><head><title>Example Innovation Fund</title></head><body>
<p>Welcome to the Example Innovation Fund.</p>
<a href="/news/call-2569">ประกาศรับข้อเสนอโครงการ 2569</a>
<a href="/admin/call-drafts">Draft calls</a>
<a href="/about">About us</a>
<a href="https://other.example.com/grant">Partner grant</a>
</body></html>"""


class Site:
    """A fake funder website: per-path responses plus a log of what the crawler asked for."""

    def __init__(self, robots="User-agent: *\nDisallow: /admin/\n", robots_status=200):
        self.pages = {"/": (HOME, "text/html; charset=utf-8"),
                      "/news/call-2569": (CALL_TH.encode("cp874"), "text/html"),  # no charset header: sniffed
                      "/admin/call-drafts": ("secret", "text/html"),
                      "/about": ("<html><title>About</title><body>About</body></html>", "text/html")}
        self.robots, self.robots_status, self.hits, self.etag = robots, robots_status, [], '"v1"'

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.hits.append((request.url.host, request.url.path))
        if request.url.host != "fund.example.th":
            return httpx.Response(200, text="<html><title>other</title></html>")
        if request.url.path == "/robots.txt":
            return httpx.Response(self.robots_status, text=self.robots)
        if request.headers.get("if-none-match") == self.etag:
            return httpx.Response(304)
        body, ct = self.pages.get(request.url.path, (None, None))
        if body is None:
            return httpx.Response(404)
        return httpx.Response(200, content=body if isinstance(body, bytes) else body.encode(), headers={"content-type": ct, "etag": self.etag})


class Clock:
    def __init__(self):
        self.t, self.slept = 1000.0, []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def _fetcher(tmp_path, site, delay=5.0, clock=None):
    clock = clock or Clock()
    client = httpx.Client(transport=httpx.MockTransport(site.handler), follow_redirects=True)
    return PoliteFetcher(tmp_path / "cache", client=client, min_delay=delay, clock=clock, sleep=clock.sleep), clock


def test_load_sites_any_format(tmp_path):
    (tmp_path / "s.txt").write_text("# Thai funders\nhttps://www.nia.or.th | nia\nhttps://www.nia.or.th/  # dup\n\nhttps://x.org/calls#open\n")
    sites = load_sites(tmp_path / "s.txt")
    assert [s.url for s in sites] == ["https://www.nia.or.th", "https://x.org/calls#open"] and sites[0].funder == "nia"
    (tmp_path / "s.csv").write_text("url,funder,follow,max_pages\nhttps://a.org,,tor;call,5\n")
    s = load_sites(tmp_path / "s.csv")[0]
    assert s.follow == ["tor", "call"] and s.max_pages == 5
    (tmp_path / "s.yaml").write_text("sites:\n  - https://b.org\n  - {url: 'https://c.org', funder: c}\n")
    assert [s.funder for s in load_sites(tmp_path / "s.yaml")] == [None, "c"]
    (tmp_path / "bad.txt").write_text("ftp://nope\n")
    with pytest.raises(ValueError):
        load_sites(tmp_path / "bad.txt")
    assert same_site("https://files.nia.or.th/a.pdf", "https://www.nia.or.th") and not same_site("https://evil.com", "https://nia.or.th")


def test_fetcher_robots_pacing_and_conditional_get(tmp_path):
    site = Site(robots="User-agent: *\nDisallow: /admin/\nCrawl-delay: 10\n")
    f, clock = _fetcher(tmp_path, site, delay=5.0)
    with pytest.raises(RobotsDenied):
        f.fetch("https://fund.example.th/admin/call-drafts")
    assert ("fund.example.th", "/admin/call-drafts") not in site.hits  # never requested
    p1 = f.fetch("https://fund.example.th/")
    p2 = f.fetch("https://fund.example.th/")  # second time: If-None-Match -> 304 -> cached body
    assert p1.status == 200 and p2.not_modified and p2.data == p1.data
    assert clock.slept and all(s >= 10 for s in clock.slept)  # site's Crawl-delay beats our 5 s minimum

    down = Site(robots_status=503)  # RFC 9309: robots.txt unreachable -> assume full disallow
    f2, _ = _fetcher(tmp_path / "b", down)
    with pytest.raises(RobotsDenied):
        f2.fetch("https://fund.example.th/")
    missing = Site(robots_status=404)  # no robots.txt -> allowed
    f3, _ = _fetcher(tmp_path / "c", missing)
    assert f3.fetch("https://fund.example.th/").status == 200


def test_textify_sniffs_thai_legacy_encoding():
    page = Page("u", "https://fund.example.th/news/call-2569", 200, "text/html", CALL_TH.encode("cp874"), "now")
    doc = textify(page)
    assert doc.title.startswith("ประกาศรับข้อเสนอ") and doc.lang == "th"
    assert "31 มีนาคม 2569" in doc.text  # Thai digits normalised
    assert ("https://fund.example.th/files/form.docx", "ดาวน์โหลดแบบฟอร์มข้อเสนอโครงการ") in doc.links


def _doc():
    return textify(Page("u", "https://fund.example.th/news/call-2569", 200, "text/html", CALL_TH.encode("cp874"), "now"))


def test_heuristic_extraction_thai():
    doc = _doc()
    score, reasons = ex.relevance(doc)
    assert score >= ex.CANDIDATE_MIN and "deadline cue" in reasons
    [c] = ex.extract(doc, TODAY, use_llm=False)
    assert c.method == "heuristic" and c.values["deadline"] == "2026-03-31"
    assert c.values["amount_max"] == 1_500_000 and c.values["currency"] == "THB"
    assert "31 มีนาคม 2569" in c.evidence["deadline"] and c.dropped == []
    [late] = ex.extract(doc, date(2026, 6, 1), use_llm=False)
    assert any("passed" in f for f in late.flags)


def test_verifier_drops_values_without_a_real_quote():
    doc = _doc()
    item = {
        "title": "ประกาศรับข้อเสนอโครงการนวัตกรรมวัสดุหมุนเวียน ปี 2569",
        "deadline": "2026-04-30", "amount_max": 5_000_000, "currency": "THB", "trl_min": 4,
        "countries": ["TH"], "requires_incorporation": True, "form_url": "https://fund.example.th/files/form.docx",
        "evidence": [
            {"field": "deadline", "quote": "ปิดรับข้อเสนอภายในวันที่ 30 เมษายน 2569"},  # not on the page
            {"field": "amount_max", "quote": "วงเงินไม่เกิน 1.5 ล้านบาท"},  # on the page, but says 1.5M not 5M
            {"field": "trl_min", "quote": "ระดับความพร้อมทางเทคโนโลยี TRL 4 ขึ้นไป"},
            {"field": "countries", "quote": "จดทะเบียนในประเทศไทย"},
            {"field": "requires_incorporation", "quote": "สำหรับนิติบุคคลที่จดทะเบียน ... ในประเทศไทย"},
        ],
    }
    kept, evidence, dropped, unchecked = ex.verify(item, doc)
    assert {d["field"] for d in dropped} == {"deadline", "amount_max"}
    assert unchecked == ["requires_incorporation"]  # quote on the page, value not machine-checkable
    assert kept["deadline"] is None and kept["amount_max"] is None and kept["currency"] is None
    assert kept["trl_min"] == 4 and kept["countries"] == ["TH"] and kept["requires_incorporation"] is True
    assert kept["form_url"] == "https://fund.example.th/files/form.docx"
    item2 = dict(item, form_url="https://fund.example.th/made-up.pdf", evidence=[])
    _, _, dropped2, _ = ex.verify(item2, doc)
    assert "form_url" in {d["field"] for d in dropped2}


def test_llm_extraction_is_verified_too(monkeypatch):
    doc = _doc()
    fake = {"opportunities": [{
        "title": "ประกาศรับข้อเสนอโครงการนวัตกรรมวัสดุหมุนเวียน ปี 2569", "title_en": "Circular Materials Innovation Call 2026",
        "summary": "Grants of up to THB 1.5M for Thai-registered companies developing materials from industrial waste.",
        "fields": ["materials"], "subdomains": ["Recycling & circular materials", "Battery materials"],
        "trl_min": 4, "trl_max": None, "countries": ["TH"], "applicant_types": ["startup", "sme"],
        "requires_incorporation": True, "ip_assignment_required": None, "equity_taken": False,
        "amount_min": None, "amount_max": 1_500_000, "currency": "THB", "deadline": "2026-03-31", "rolling": None,
        "cycle": None, "application_mode": "email", "form_url": "https://fund.example.th/files/form.docx",
        "evidence": [{"field": "deadline", "quote": "ปิดรับข้อเสนอภายในวันที่ 31 มีนาคม 2569"},
                     {"field": "amount_max", "quote": "วงเงินไม่เกิน 1.5 ล้านบาทต่อโครงการ"},
                     {"field": "trl_min", "quote": "TRL 4 ขึ้นไป"},
                     {"field": "countries", "quote": "จดทะเบียนในประเทศไทย"},
                     {"field": "requires_incorporation", "quote": "สำหรับนิติบุคคล"},
                     {"field": "equity_taken", "quote": "no equity is taken"}],  # invented
    }]}
    monkeypatch.setattr(ex.llm, "enabled", lambda: True)
    monkeypatch.setattr(ex.llm, "structured", lambda **kw: fake)
    [c] = ex.extract(doc, TODAY)
    assert c.method == "llm" and c.values["deadline"] == "2026-03-31" and c.values["amount_max"] == 1_500_000
    # equity_taken had an invented quote; applicant_types and application_mode had no quote at all
    assert {d["field"] for d in c.dropped} == {"equity_taken", "applicant_types", "application_mode"}
    assert c.values["fields"] == ["materials"]  # inferred, kept, labelled in the queue


def _sites(tmp_path):
    p = tmp_path / "sites.yaml"
    p.write_text("sites:\n  - url: https://fund.example.th/\n")
    return p


def test_run_queue_and_apply_end_to_end(tmp_path):
    site = Site()
    f, _ = _fetcher(tmp_path, site)
    seed = tmp_path / "grants.yaml"
    shutil.copy(Path(__file__).resolve().parents[3] / "data" / "seed" / "grants.yaml", seed)
    kw = dict(seed=seed, out_dir=tmp_path / "review", state_path=tmp_path / "state.json", cache_dir=tmp_path / "cache",
              today=TODAY, use_llm=False, fetcher=f)
    stats = run(_sites(tmp_path), **kw)
    assert stats["pages"] == 2 and stats["robots_denied"] == 1 and stats["queue_items"] == 1, stats
    paths = [p for h, p in site.hits if h == "fund.example.th"]
    assert "/about" not in paths and "/admin/call-drafts" not in paths  # not call-like / disallowed
    assert not any(h == "other.example.com" for h, _ in site.hits)  # never leaves the watched site

    queue_path = Path(stats["queue"])
    text = queue_path.read_text()
    assert text.startswith("# SCI corpus review queue") and "ปิดรับข้อเสนอ" in text
    q = yaml.safe_load(text)
    [item] = q["items"]
    assert item["kind"] == "new" and item["decision"] == "pending" and item["entry"]["verified"] is False
    assert item["entry"]["deadline"] == "2026-03-31" and item["entry"]["amount"] == {"min": None, "max": 1500000.0, "currency": "THB"}

    # Unchanged pages are not re-extracted on the next run, and the same-day queue keeps its item
    again = run(_sites(tmp_path), **kw)
    assert again["unchanged"] == 2 and again["queue_items"] == 1
    assert len(yaml.safe_load(queue_path.read_text())["items"]) == 1

    # Pending items are never applied
    before = seed.read_text()
    assert review.apply_queue(queue_path, seed, TODAY)["added"] == []
    # Accepting a new-funder item requires the funder details
    item["decision"] = "accept"
    queue_path.write_text(yaml.safe_dump(q, allow_unicode=True))
    assert review.apply_queue(queue_path, seed, TODAY)["skipped"]
    item["new_funder"].update(key="examplefund", name="Example Innovation Fund", type="government", country="TH")
    queue_path.write_text(yaml.safe_dump(q, allow_unicode=True))
    rep = review.apply_queue(queue_path, seed, TODAY)
    assert len(rep["added"]) == 1
    after = seed.read_text()
    assert after.startswith(before.splitlines()[0]) and "READ BEFORE THE DEMO" in after  # comments survive
    batch = CuratedConnector(seed).fetch()
    assert batch.errors == []
    g = next(g for g in batch.grants if g.source_ref == rep["added"][0])
    assert g.verified is False and g.deadline.date() == date(2026, 3, 31) and g.currency == "THB"


def test_existing_entry_becomes_an_update(tmp_path):
    seed = Path(__file__).resolve().parents[3] / "data" / "seed" / "grants.yaml"
    corpus = review.Corpus.load(seed)
    doc = _doc()
    c = ex.Candidate(doc, "llm", {"title": "NIA Open Innovation Grant", "deadline": "2026-03-31"}, {"deadline": "x"})
    site = load_sites(_sites(tmp_path))[0]
    site.funder = "nia"
    q = review.build_queue(corpus, [(site, c)], "now")
    [item] = q["items"]
    assert item["kind"] == "update" and item["ref"] == "nia-open-innovation"
    assert item["changes"] == {"deadline": {"old": None, "new": "2026-03-31"}}


# --- regressions from the adversarial review ---------------------------------------------------------
def test_robots_precedence_and_wildcards(tmp_path):
    """Python <3.13's stdlib parser gets these wrong; protego implements RFC 9309."""
    site = Site(robots="User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /*.pdf$\n\nUser-agent: *\nDisallow: /about\n")
    f, _ = _fetcher(tmp_path, site)
    for path in ("/admin/call-drafts", "/files/x.pdf", "/about"):
        with pytest.raises(RobotsDenied):
            f.fetch("https://fund.example.th" + path)
    assert f.fetch("https://fund.example.th/").status == 200


def test_redirects_are_checked_hop_by_hop(tmp_path):
    from app.curate.crawl import SkipURL

    site = Site()
    base = site.handler

    def handler(req):
        if req.url.path == "/go-admin":
            return httpx.Response(302, headers={"location": "/admin/call-drafts"})
        if req.url.path == "/go-away":
            return httpx.Response(302, headers={"location": "https://other.example.com/private"})
        return base(req)

    site.handler = handler
    f, _ = _fetcher(tmp_path, site)
    with pytest.raises(RobotsDenied):
        f.fetch("https://fund.example.th/go-admin")
    with pytest.raises(SkipURL):
        f.fetch("https://fund.example.th/go-away", allowed=lambda u: same_site(u, "https://fund.example.th/"))
    assert not any(h == "other.example.com" for h, _ in site.hits)


def test_bad_links_and_corrupt_files_do_not_abort_the_run(tmp_path):
    from app.curate.crawl import crawl_all
    from app.curate.sites import Site as WatchSite

    site = Site()
    site.pages["/"] = ('<html><title>Fund</title><a href="http://localhost:99999/grant">bad port</a>'
                       '<a href="/news/call.pdf">ประกาศรับข้อเสนอ</a><a href="/news/call-2569">ประกาศรับข้อเสนอ 2569</a></html>',
                       "text/html")
    site.pages["/news/call.pdf"] = (b"%PDF-1.4 truncated garbage", "application/pdf")
    f, _ = _fetcher(tmp_path, site)
    [res] = crawl_all(f, [WatchSite(url="https://fund.example.th/")])
    assert len(res.docs) == 2 and any("call.pdf" in e for e in res.errors)


def test_max_pages_caps_requests_not_successes(tmp_path):
    from app.curate.crawl import crawl_site
    from app.curate.sites import Site as WatchSite

    site = Site()
    links = "".join(f'<a href="/call/{i}">call {i}</a>' for i in range(30))
    site.pages["/"] = (f"<html><title>Fund</title>{links}</html>", "text/html")  # every /call/i is a 404
    f, _ = _fetcher(tmp_path, site)
    res = crawl_site(f, WatchSite(url="https://fund.example.th/", max_pages=5))
    calls = [p for h, p in site.hits if p.startswith("/call/")]
    assert len(calls) == 4 and len(res.errors) == 4


def test_wrong_charset_header_still_yields_thai():
    page = Page("u", "https://fund.example.th/x", 200, "text/html; charset=ISO-8859-1", CALL_TH.encode("cp874"), "now")
    doc = textify(page)
    assert doc.lang == "th" and doc.title.startswith("ประกาศรับข้อเสนอ")


def test_numbers_cut_from_longer_numbers_are_not_quotes():
    doc = _doc()
    item = {"title": doc.title, "amount_max": 5_000_000, "currency": "THB", "deadline": "2026-03-01",
            "evidence": [{"field": "amount_max", "quote": "5 ล้านบาท"}, {"field": "deadline", "quote": "1 มีนาคม 2569"}]}
    kept, _, dropped, _ = ex.verify(item, doc)
    assert kept["amount_max"] is None and kept["deadline"] is None
    assert all(d["reason"] == "no supporting quote found on the page" for d in dropped)


def test_currency_comes_from_the_page_and_eligibility_must_be_named():
    doc = _doc()
    item = {"title": doc.title, "amount_max": 1_500_000, "currency": "USD", "countries": ["TH", "GLOBAL"],
            "applicant_types": ["startup", "individual"],
            "evidence": [{"field": "amount_max", "quote": "วงเงินไม่เกิน 1.5 ล้านบาท"},
                         {"field": "countries", "quote": "จดทะเบียนในประเทศไทย"},
                         {"field": "applicant_types", "quote": "สำหรับนิติบุคคลที่จดทะเบียนในประเทศไทย"}]}
    kept, _, dropped, _ = ex.verify(item, doc)
    assert kept["amount_max"] == 1_500_000 and kept["currency"] == "THB"  # corrected, never defaulted
    assert kept["countries"] == ["TH"] and kept["applicant_types"] == ["startup"]
    assert {(d["field"], d["value"]) for d in dropped} >= {("countries", "GLOBAL"), ("applicant_types", "individual")}


def test_thai_date_and_amount_formats():
    from app import thai

    assert thai.find_deadline("ปิดรับข้อเสนอภายในวันที่ 31/03/2569")[0] == date(2026, 3, 31)
    assert thai.find_deadline("Applications close on 31 March 2569")[0] == date(2026, 3, 31)
    assert thai.find_deadline("ปิดรับข้อเสนอภายในวันที่ 31 มีนาคม 2569 ระยะเวลาโครงการตั้งแต่ 1 ตุลาคม 2569 ถึง 30 กันยายน 2570")[0] == date(2026, 3, 31)
    assert thai.find_deadline("Deadline: April 30, 2026 (results announced 15 June 2026)")[0] == date(2026, 4, 30)
    assert thai.find_deadline("ส่งข้อเสนอภายในวันที่ 31 มีนาคม 2569 ประกาศผลการพิจารณาภายในวันที่ 30 มิถุนายน 2569")[0] == date(2026, 3, 31)
    assert thai.find_dates("31 มีนาคม ค.ศ. 2026")[0][0] == date(2026, 3, 31)
    assert thai.find_max_amount("up to $1.5M per project")[:2] == (1_500_000, "USD")
    assert thai.find_max_amount("up to S$250k")[:2] == (250_000, "SGD")
    assert thai.find_max_amount("maximum A$50,000")[:2] == (50_000, "AUD")
    assert thai.find_max_amount("max. 20 pages; use the official form 3B") is None
    assert thai.find_max_amount("วงเงินงบประมาณทั้งสิ้น 50 ล้านบาท โดยสนับสนุนโครงการละไม่เกิน 1.5 ล้านบาท")[:2] == (1_500_000, "THB")
    assert thai.find_max_amount("ไม่เกิน 5 แสน บาท")[:2] == (500_000, "THB")


def _seed_copy(tmp_path):
    seed = tmp_path / "grants.yaml"
    shutil.copy(Path(__file__).resolve().parents[3] / "data" / "seed" / "grants.yaml", seed)
    return seed


def test_update_merges_partial_ranges_and_ignores_same_dates(tmp_path):
    corpus = review.Corpus.load(_seed_copy(tmp_path))
    site = load_sites(_sites(tmp_path))[0]
    site.funder = "nia"
    c = ex.Candidate(_doc(), "llm", {"title": "NIA Open Innovation Grant", "trl_min": 5, "amount_max": 1_500_000,
                                     "currency": "THB"}, {"amount_max": "x"})
    q = review.build_queue(corpus, [(site, c)], "now")
    assert q["items"] == []  # page agrees with the corpus (trl [5, 8], max 1.5M THB): nothing to change
    c2 = ex.Candidate(_doc(), "llm", {"title": "NIA Open Innovation Grant", "trl_min": 4, "amount_max": 2_000_000,
                                      "currency": "THB"}, {"amount_max": "x"})
    [item] = review.build_queue(corpus, [(site, c2)], "now")["items"]
    assert item["changes"]["trl"]["new"] == [4, 8] and item["changes"]["amount"]["new"]["min"] == 0


def test_unknown_funder_is_never_an_update_and_dedup_keeps_distinct_calls(tmp_path):
    corpus = review.Corpus.load(_seed_copy(tmp_path))
    site = load_sites(_sites(tmp_path))[0]
    d = _doc()
    a = ex.Candidate(d, "llm", {"title": "Open Innovation Grant", "deadline": "2026-04-30"}, {"title": "x"})
    b = ex.Candidate(d, "llm", {"title": "Open Innovation Grant 2", "deadline": "2026-05-30"}, {"title": "x"})
    items = review.build_queue(corpus, [(site, a), (site, b)], "now")["items"]
    assert [i["kind"] for i in items] == ["new", "new"] and items[0]["new_funder"]["key"] == "fund-example-th"


def test_apply_is_idempotent_rejects_key_collisions_and_keeps_layout(tmp_path):
    seed = _seed_copy(tmp_path)
    before = seed.read_text()
    empty = tmp_path / "empty.yaml"
    review.write_queue({"items": []}, empty)
    review.apply_queue(empty, seed, TODAY)
    assert seed.read_text() == before  # nothing accepted -> file untouched, byte for byte
    corpus = review.Corpus.load(seed)
    site = load_sites(_sites(tmp_path))[0]
    c = ex.Candidate(_doc(), "llm", {"title": "Circular call", "deadline": "2026-03-31"}, {"title": "x"})
    q = review.build_queue(corpus, [(site, c)], "now")
    q["items"][0].update(decision="accept")
    q["items"][0]["new_funder"].update(key="nia", name="Example Org", type="government", country="TH")
    qp = tmp_path / "q.yaml"
    review.write_queue(q, qp)
    rep = review.apply_queue(qp, seed, TODAY)
    assert rep["added"] == [] and "already belongs" in rep["skipped"][0]
    q["items"][0]["new_funder"]["key"] = "examplefund"
    review.write_queue(q, qp)
    assert len(review.apply_queue(qp, seed, TODAY)["added"]) == 1
    assert review.apply_queue(qp, seed, TODAY)["added"] == []  # second apply: item is marked applied
    import difflib

    removed = [ln for ln in difflib.unified_diff(before.splitlines(), seed.read_text().splitlines(), lineterm="", n=0)
               if ln.startswith("-") and not ln.startswith("---")]
    assert removed == []  # only insertions (the new funder and grant); no existing line rewritten


def test_seed_sites_keeps_a_curated_list_and_csv_bom(tmp_path):
    from app.curate.__main__ import main

    out = tmp_path / "sites.yaml"
    out.write_text("sites:\n  - {url: 'https://www.nia.or.th/calls', funder: nia}\n  - https://hand-added.example.org/calls\n")
    main(["seed-sites", "--out", str(out)])
    urls = [s.url for s in load_sites(out)]
    assert "https://hand-added.example.org/calls" in urls and "https://www.nia.or.th/calls" in urls
    csv_path = tmp_path / "s.csv"
    csv_path.write_bytes("\ufeffurl,funder\nhttps://a.org,\n".encode("utf-8"))
    assert load_sites(csv_path)[0].url == "https://a.org"
