"""Corpus curation CLI.

    python -m app.curate seed-sites                 # write data/curate/sites.yaml from the corpus funders
    python -m app.curate run [--sites FILE] [--no-llm] [--force] [--limit N]
                                                    # crawl -> extract -> verify -> review queue YAML
    python -m app.curate apply data/curate/review/queue-YYYY-MM-DD.yaml
                                                    # merge accepted items into data/seed/grants.yaml
    python -m app.curate stale [--days 90]          # entries never or long ago checked by a person

Set CURATE_CONTACT (an email or URL) so site operators can reach you; it goes in the User-Agent.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from .. import llm
from ..config import REPO_ROOT, settings
from ..ingest.curated import CuratedConnector
from . import review
from .crawl import PoliteFetcher, crawl_all
from .extract import CANDIDATE_MIN, extract, relevance
from .sites import canonical, dump_sites, load_sites, sites_from_corpus

CURATE_DIR = REPO_ROOT / "data" / "curate"
log = logging.getLogger("sci.curate")


def _state(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def run(sites_path: Path, *, seed: Path, out_dir: Path, state_path: Path, cache_dir: Path, today: date,
        use_llm: bool = True, force: bool = False, limit: int | None = None, delay: float = 5.0, workers: int = 6,
        fetcher: PoliteFetcher | None = None) -> dict:
    sites = load_sites(sites_path)[:limit] if limit else load_sites(sites_path)
    fetcher = fetcher or PoliteFetcher(cache_dir, contact=os.environ.get("CURATE_CONTACT"), min_delay=delay)
    state = _state(state_path)
    stats = {"sites": len(sites), "pages": 0, "unchanged": 0, "irrelevant": 0, "extracted": 0, "candidates": 0,
             "dropped_values": 0, "errors": []}
    pairs = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    want = "llm" if use_llm and llm.enabled() else "heuristic"
    for res in crawl_all(fetcher, sites, workers=workers):
        stats["errors"] += res.errors
        for doc in res.docs:
            stats["pages"] += 1
            prev = state.get(doc.url, {})
            # unchanged = same text AND already extracted with the best method available now
            # (a page that fell back to heuristics while the LLM was down is re-extracted once it is back)
            if prev.get("sha") == doc.sha and (prev.get("method") == want or prev.get("method") == "irrelevant") and not force:
                stats["unchanged"] += 1
                continue
            score, _ = relevance(doc)
            if score < CANDIDATE_MIN:
                stats["irrelevant"] += 1
                state[doc.url] = {"sha": doc.sha, "changed": now, "title": doc.title, "method": "irrelevant"}
                continue
            stats["extracted"] += 1
            cands = extract(doc, today, use_llm=use_llm)
            state[doc.url] = {"sha": doc.sha, "changed": now, "title": doc.title,
                              "method": cands[0].method if cands else want}
            for c in cands:
                stats["candidates"] += 1
                stats["dropped_values"] += len(c.dropped)
                pairs.append((res.site, c))
    queue = review.build_queue(review.Corpus.load(seed), pairs, now)
    out = out_dir / f"queue-{today.isoformat()}.yaml"
    if out.exists():  # a second run the same day: add to the queue, never drop items or decisions
        queue = review.merge_queue(yaml.safe_load(out.read_text(encoding="utf-8")) or {}, queue)
    if queue["items"]:
        review.write_queue(queue, out)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True))
    stats.update(queue_items=len(queue["items"]), queue=str(out) if queue["items"] else None,
                 robots_denied=fetcher.stats["robots_denied"], not_modified=fetcher.stats["not_modified"])
    return stats


def stale(seed: Path, today: date, days: int) -> list[str]:
    doc = yaml.safe_load(seed.read_text(encoding="utf-8"))
    out = []
    for g in doc.get("grants", []):
        lr = g.get("last_reviewed")
        lr = date.fromisoformat(str(lr)) if lr else None
        dl = g.get("deadline")
        if not g.get("verified") or lr is None or today - lr > timedelta(days=days):
            out.append(f"{g['ref']}: {'never reviewed' if lr is None else f'last reviewed {lr}'}"
                       f"{'' if g.get('verified') else ', unverified'}")
        elif dl and date.fromisoformat(str(dl)[:10]) < today and not g.get("rolling"):
            out.append(f"{g['ref']}: deadline {dl} has passed - next cycle?")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m app.curate", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=Path, default=settings.seed_path)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seed-sites")
    s.add_argument("--out", type=Path, default=CURATE_DIR / "sites.yaml")
    s.add_argument("--force", action="store_true", help="overwrite an existing watch list (default: add new funders only)")
    r = sub.add_parser("run")
    r.add_argument("--sites", type=Path, default=CURATE_DIR / "sites.yaml")
    r.add_argument("--out", type=Path, default=CURATE_DIR / "review")
    r.add_argument("--state", type=Path, default=CURATE_DIR / "state.json")
    r.add_argument("--no-llm", action="store_true", help="heuristic extraction only (no API key needed)")
    r.add_argument("--force", action="store_true", help="re-extract pages whose text has not changed")
    r.add_argument("--limit", type=int)
    r.add_argument("--delay", type=float, default=5.0, help="seconds between requests to one host (min)")
    r.add_argument("--workers", type=int, default=6, help="hosts crawled in parallel")
    a = sub.add_parser("apply")
    a.add_argument("queue", type=Path)
    st = sub.add_parser("stale")
    st.add_argument("--days", type=int, default=90)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    today = date.today()

    if args.cmd == "seed-sites":
        sites = sites_from_corpus(args.seed)
        if args.out.exists() and not args.force:
            have = load_sites(args.out)
            known = {canonical(x.url) for x in have} | {x.funder for x in have if x.funder}
            added = [x for x in sites if canonical(x.url) not in known and x.funder not in known]
            dump_sites(have + added, args.out)
            print(f"{args.out} exists: kept its {len(have)} sites and added {len(added)} funders not yet watched "
                  "(use --force to overwrite).")
        else:
            dump_sites(sites, args.out)
            print(f"wrote {len(sites)} sites to {args.out}. Add funders' call/news pages - home pages rarely list calls.")
    elif args.cmd == "run":
        stats = run(args.sites, seed=args.seed, out_dir=args.out, state_path=args.state,
                    cache_dir=settings.data_dir / "curate-cache", today=today, use_llm=not args.no_llm,
                    force=args.force, limit=args.limit, delay=args.delay, workers=args.workers)
        errors = stats.pop("errors")
        print(json.dumps(stats, indent=1))
        for e in errors[:20]:
            print("  !", e)
        if len(errors) > 20:
            print(f"  ... {len(errors) - 20} more errors")
    elif args.cmd == "apply":
        rep = review.apply_queue(args.queue, args.seed, today)
        print(json.dumps(rep, indent=1, ensure_ascii=False))
        batch = CuratedConnector(args.seed).fetch()  # the corpus must still load after the merge
        print(f"corpus now loads {len(batch.grants)} grants; {len(batch.errors)} errors")
        for e in batch.errors:
            print("  !", e)
        return 1 if batch.errors else 0
    elif args.cmd == "stale":
        rows = stale(args.seed, today, args.days)
        print("\n".join(rows) or "nothing stale")
        print(f"{len(rows)} entries need a human look")
    return 0


if __name__ == "__main__":
    sys.exit(main())
