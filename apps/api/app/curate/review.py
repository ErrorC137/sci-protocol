"""Candidates -> review queue (YAML a person edits) -> `apply` merges accepted items into grants.yaml.

The queue is the only path into the corpus. Each item shows what changed, the verified quote behind
every value, what was dropped and why, and starts as `decision: pending`. `apply` writes with
ruamel.yaml so the hand-written comments and layout of grants.yaml survive.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .extract import Candidate
from .sites import Site, canonical, site_key

COMPARED = ("deadline", "amount", "trl", "countries", "applicant_types", "requires_incorporation",
            "ip_assignment_required", "equity_taken", "rolling", "cycle", "application_mode", "form_url")


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:48] or "item"


def to_entry(c: Candidate, funder: str | None) -> dict:
    """Candidate values -> the grants.yaml entry shape (see the field reference atop that file)."""
    v = c.values
    e: dict = {"ref": None, "funder": funder, "title": v.get("title")}
    if v.get("title_en"):
        e["title_en"] = v["title_en"]
    for k in ("summary", "fields", "subdomains"):
        if v.get(k):
            e[k] = v[k]
    if v.get("trl_min") is not None or v.get("trl_max") is not None:
        e["trl"] = [v.get("trl_min"), v.get("trl_max")]
    for k in ("countries", "applicant_types", "requires_incorporation", "ip_assignment_required"):
        if v.get(k) not in (None, []):
            e[k] = v[k]
    if v.get("amount_min") is not None or v.get("amount_max") is not None:
        e["amount"] = {"min": v.get("amount_min"), "max": v.get("amount_max"), "currency": v.get("currency")}  # never a default currency
    for k in ("equity_taken", "deadline", "rolling", "cycle", "application_mode", "form_url"):
        if v.get(k) not in (None, ""):
            e[k] = v[k]
    e["url"] = c.doc.url
    e["confidence"] = "medium" if c.method == "llm" else "low"
    e["verified"] = False
    return e


@dataclass
class Corpus:
    path: Path
    funders: list[dict]
    grants: list[dict]

    @classmethod
    def load(cls, path: Path) -> Corpus:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(path, doc.get("funders", []), doc.get("grants", []))

    def funder_for(self, site: Site, url: str) -> str | None:
        if site.funder:
            return site.funder
        host = site_key(re.sub(r"^https?://", "", url).split("/")[0])
        for f in self.funders:
            fh = site_key(re.sub(r"^https?://", "", f.get("website") or "").split("/")[0])
            if fh and (host == fh or host.endswith("." + fh)):
                return f["key"]
        return None

    def match(self, entry: dict) -> dict | None:
        """Same funder and a near-identical title (several programmes often share one funder URL).
        A page from an unknown funder is never matched to another funder's grant: it is always proposed as new."""
        if not entry.get("funder"):
            return None
        best, score = None, 0.0
        titles = [t for t in (entry.get("title"), entry.get("title_en")) if t]
        for g in self.grants:
            if g.get("funder") != entry["funder"]:
                continue
            r = max(difflib.SequenceMatcher(None, t.casefold(), g["title"].casefold()).ratio() for t in titles)
            if g.get("url") and canonical(g["url"]) == canonical(entry["url"]):
                r += 0.15
            if r > score:
                best, score = g, r
        return best if score >= 0.85 else None


def _norm_val(k: str, v):
    if v is None:
        return None
    if k == "deadline":
        return str(v)[:10]
    if isinstance(v, list) and k in ("countries", "applicant_types"):
        return sorted(v)
    return v


def _merge_parts(old, new, keys):
    """Overwrite only the components the page actually stated (non-None); keep the rest of the curated value."""
    merged = dict(old or {})
    for k in keys:
        if new.get(k) is not None:
            merged[k] = new[k]
    return merged


def _changes(old: dict, new: dict) -> dict:
    out = {}
    for k in COMPARED:
        if k not in new:
            continue
        if k == "amount":
            o = dict(old.get("amount") or {})
            m = _merge_parts(o, new["amount"], ("min", "max", "currency"))
            if any(float(m.get(x) or 0) != float(o.get(x) or 0) for x in ("min", "max")) or (m.get("currency") or None) != (o.get("currency") or None):
                out[k] = {"old": old.get("amount"), "new": m}
        elif k == "trl":
            o = list(old.get("trl") or [None, None]) + [None, None]
            m = [new["trl"][i] if new["trl"][i] is not None else o[i] for i in (0, 1)]
            if m != o[:2]:
                out[k] = {"old": old.get("trl"), "new": m}
        elif _norm_val(k, new[k]) != _norm_val(k, old.get(k)):
            out[k] = {"old": old.get(k), "new": new[k]}
    return out


def build_queue(corpus: Corpus, results: list[tuple[Site, Candidate]], generated: str) -> dict:
    items, seen = [], set()
    for site, c in results:
        funder = corpus.funder_for(site, c.doc.url)
        entry = to_entry(c, funder)
        # the same call linked from several watched pages; distinct calls on one page keep distinct titles
        key = (funder or site_key(site.host), canonical(c.doc.url), (entry["title"] or "").casefold())
        if key in seen:
            continue
        seen.add(key)
        existing = corpus.match(entry)
        item = {"id": f"q{len(items) + 1}", "decision": "pending"}
        if existing:
            changes = _changes(existing, entry)
            if not changes:
                continue  # page confirms what the corpus already says
            item.update(kind="update", ref=existing["ref"], changes=changes)
        else:
            entry["ref"] = _slug(f"{funder or site_key(site.host)}-{entry.get('title_en') or entry['title']}")
            item.update(kind="new", entry=entry)
            if not funder:
                item["new_funder"] = {"key": _slug(site_key(site.host)), "name": None, "type": None,
                                      "country": None, "website": site.url}
        item.update(source_url=c.doc.url, method=c.method, evidence=c.evidence,
                    inferred=[k for k in ("fields", "subdomains", "summary", "title_en") if c.values.get(k)],
                    value_unchecked=c.unchecked, dropped=c.dropped, flags=c.flags, set_verified=False)
        items.append(item)
    return {"generated": generated, "items": items}


def item_key(item: dict) -> tuple:
    title = (item.get("entry") or {}).get("title") or item.get("ref") or ""
    return (item.get("kind"), item.get("ref"), canonical(item.get("source_url") or ""), title.casefold())


def merge_queue(old: dict, new: dict) -> dict:
    """A second run on the same day adds to the existing queue; it never drops items or reviewers' decisions."""
    items = list(old.get("items") or [])
    keys = {item_key(i) for i in items}
    n = len(items)
    for it in new.get("items") or []:
        if item_key(it) in keys:
            continue
        n += 1
        it = dict(it, id=f"q{n}")
        items.append(it)
        keys.add(item_key(it))
    return {"generated": new.get("generated"), "first_generated": old.get("first_generated") or old.get("generated"), "items": items}


QUEUE_HEADER = """# SCI corpus review queue. Nothing here is in the corpus yet.
#
# For each item: open source_url, check the evidence quotes, then set
#   decision: accept   (or reject)
#   set_verified: true only if you confirmed the values on the live page today
# New funders need new_funder.name/type/country filled in (or set entry.funder to an existing key).
# Values without a quote found on the page were removed and are listed under `dropped`.
# `inferred` values (fields, subdomains, summary, title_en) are the model's classification - check them.
# `value_unchecked` fields have a quote on the page, but no program can check the value follows from it.
#
# Then run:  python -m app.curate apply <this file>
"""


def write_queue(queue: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(QUEUE_HEADER + yaml.safe_dump(queue, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")


# --- apply -----------------------------------------------------------------------------------------
def _flow(v):
    if isinstance(v, list):
        s = CommentedSeq(v)
        s.fa.set_flow_style()
        return s
    if isinstance(v, dict):
        m = CommentedMap(v)
        m.fa.set_flow_style()
        return m
    return v


def _yaml() -> YAML:
    """Round-trip settings matching grants.yaml's own layout, so an apply changes only the lines it must."""
    rt = YAML()
    rt.preserve_quotes = True
    rt.width = 4096
    rt.indent(mapping=2, sequence=4, offset=2)
    rt.representer.add_representer(type(None), lambda r, _: r.represent_scalar("tag:yaml.org,2002:null", "null"))
    return rt


def apply_queue(queue_path: Path, seed_path: Path, today: date) -> dict:
    """Merge accepted items. Applied items are marked `decision: applied` in the queue file, so running
    apply twice does not add anything twice."""
    queue = yaml.safe_load(queue_path.read_text(encoding="utf-8"))
    rt = _yaml()
    original = seed_path.read_text(encoding="utf-8")
    doc = rt.load(original)
    funders = {f["key"]: f for f in doc["funders"]}
    by_ref = {g["ref"]: g for g in doc["grants"]}
    report = {"added": [], "updated": [], "skipped": []}
    for item in queue.get("items", []):
        if item.get("decision") != "accept":
            continue
        verified = bool(item.get("set_verified"))
        if item["kind"] == "update":
            g = by_ref.get(item["ref"])
            if g is None:
                report["skipped"].append(f"{item['id']}: ref {item['ref']} no longer in corpus")
                continue
            for k, ch in item["changes"].items():
                g[k] = _flow(ch["new"])
            g["verified"], g["last_reviewed"] = verified, today
            report["updated"].append(item["ref"])
            item["decision"], item["applied_ref"] = "applied", item["ref"]
            continue
        entry = dict(item["entry"])
        nf = item.get("new_funder")
        if not entry.get("funder"):
            if not nf or not all(nf.get(k) for k in ("key", "name", "type", "country")):
                report["skipped"].append(f"{item['id']}: new funder needs key, name, type and country")
                continue
            have = funders.get(nf["key"])
            if have is not None and (have.get("name") != nf["name"] or
                                     site_key(re.sub(r"^https?://", "", have.get("website") or "").split("/")[0]) !=
                                     site_key(re.sub(r"^https?://", "", nf.get("website") or "").split("/")[0])):
                report["skipped"].append(f"{item['id']}: funder key '{nf['key']}' already belongs to {have.get('name')}; choose another key")
                continue
            if have is None:
                f = _flow({k: nf[k] for k in ("key", "name", "type", "country", "website") if nf.get(k)})
                doc["funders"].append(f)
                funders[nf["key"]] = f
            entry["funder"] = nf["key"]
        if entry["funder"] not in funders:
            report["skipped"].append(f"{item['id']}: unknown funder {entry['funder']}")
            continue
        dup = next((g for g in doc["grants"] if g.get("funder") == entry["funder"] and g.get("title") == entry.get("title")
                    and canonical(g.get("url") or "") == canonical(entry.get("url") or "")), None)
        if dup is not None:
            report["skipped"].append(f"{item['id']}: already in the corpus as {dup['ref']}")
            item["decision"], item["applied_ref"] = "applied", dup["ref"]
            continue
        ref, n = entry["ref"], 2
        while ref in by_ref:
            ref, n = f"{entry['ref']}-{n}", n + 1
        entry["ref"] = ref
        if entry.get("title_en") == entry.get("title"):
            entry.pop("title_en")
        entry["verified"], entry["last_reviewed"] = verified, today
        m = CommentedMap((k, _flow(v)) for k, v in entry.items())
        doc["grants"].append(m)
        by_ref[ref] = m
        report["added"].append(ref)
        item["decision"], item["applied_ref"] = "applied", ref
    if report["added"] or report["updated"]:
        with seed_path.open("w", encoding="utf-8") as fh:
            rt.dump(doc, fh)
        write_queue(queue, queue_path)
    return report
