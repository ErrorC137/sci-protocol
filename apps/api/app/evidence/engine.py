"""Orchestration: queries -> sources -> dedupe/rank -> elements -> judgments -> signals -> report + hash."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .. import llm
from ..config import settings
from . import chem, elements as elements_mod, judge, trl
from .claims import split_claims
from .models import (Element, ElementSignal, EvidenceReport, FTOFlag, Judgment, Reference, SourceStatus,
                     Submission)
from .sources.base import SearchQuery, Source, run
from .sources.papers import ArXiv, Crossref, OpenAlex, SemanticScholar
from .sources.patents import EpoOps, Lens, LocalCorpus, PatentsView, date_before

log = logging.getLogger("sci.evidence")

REGISTRY: dict[str, type[Source]] = {
    "local": LocalCorpus, "openalex": OpenAlex, "crossref": Crossref, "semantic_scholar": SemanticScholar,
    "arxiv": ArXiv, "patentsview": PatentsView, "epo_ops": EpoOps, "lens": Lens,
}

# CPC seed codes per concept family. Verify against the current CPC scheme before relying on them
# (ip-literature-analyst subagent); used only to narrow patent searches, never as a classification.
CPC_SEEDS = {
    "recycling": ["Y02W30/84", "H01M10/54", "H01M6/52", "C22B7/00"],
    "lithium": ["C22B26/12", "C01D15/00"],
    "nickel_cobalt": ["C22B23/00", "C01G53/00", "C01G51/00"],
    "cathode": ["H01M4/505", "H01M4/525"],
    "lfp": ["H01M4/5825"],
}


def _cpc_for(concepts: set[str]) -> list[str]:
    out = []
    if concepts & {"black_mass", "spent_lib", "hydrometallurgy", "pyrometallurgy", "direct_recycling", "relithiation"}:
        out += CPC_SEEDS["recycling"]
    if concepts & {"li2co3", "lioh", "relithiation"}:
        out += CPC_SEEDS["lithium"]
    if concepts & {"solvent_extraction", "precipitation", "pcam"}:
        out += CPC_SEEDS["nickel_cobalt"]
    if any(c.startswith("nmc") for c in concepts) or concepts & {"nca", "lco", "lmo", "single_crystal"}:
        out += CPC_SEEDS["cathode"]
    if concepts & {"lfp", "lmfp"}:
        out += CPC_SEEDS["lfp"]
    return list(dict.fromkeys(out))


def build_queries(sub: Submission) -> tuple[SearchQuery | None, SearchQuery, list[str]]:
    """(external query or None, local query, notes). Confidential submissions send only the researcher's
    own non-confidential keywords to third-party APIs; full text stays on this server."""
    full = "\n".join(x for x in (sub.title, sub.abstract, sub.claims or "", sub.methods or "") if x)
    concepts = chem.concepts(full)
    cpc = _cpc_for(concepts)
    notes = []
    local = SearchQuery(text=full[:20_000], cpc=cpc, until=sub.priority_date, limit=sub.max_references)
    if sub.confidential:
        if not sub.keywords:
            notes.append("Confidential mode with no public keywords: external sources were not queried. Add "
                         "non-confidential search keywords to search them.")
            return None, local, notes
        text = " ".join(sub.keywords)
        notes.append("Confidential mode: queries to external sources were limited to your keywords: " + text)
    else:
        expansions = [f for c in sorted(concepts) if not c.startswith("nmc") or len(c) == 6 for f in chem.expansions(c, 1)]
        text = " ".join(dict.fromkeys([sub.title, *sub.keywords, *expansions[:6]]))
    return SearchQuery(text=text[:500], phrases=sub.keywords, cpc=cpc, until=sub.priority_date,
                       limit=min(25, sub.max_references)), local, notes


def _title_key(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.lower())[:80]


def merge(results: list[tuple[str, list[Reference]]]) -> list[Reference]:
    """Dedupe by id, then patent family, then normalised title; reciprocal-rank fusion across sources."""
    by_key: dict[str, Reference] = {}
    alias: dict[str, str] = {}
    rrf: dict[str, float] = {}
    for src, refs in results:
        for rank, r in enumerate(refs):
            k = r.key
            cands = [k, f"fam:{r.family_id}" if r.family_id else None, f"title:{_title_key(r.title)}"]
            hit = next((alias[c] for c in cands if c and c in alias), None)
            if hit:
                base = by_key[hit]
                if src not in base.also_in and src != base.source:
                    base.also_in.append(src)
                if not base.abstract and r.abstract:
                    base.abstract = r.abstract
                if not base.claims and r.claims:
                    base.claims = r.claims
                k = hit
            else:
                by_key[k] = r
            for c in cands:
                if c:
                    alias.setdefault(c, k)
            rrf[k] = rrf.get(k, 0.0) + 1.0 / (60 + rank)
    return [by_key[k].model_copy(update={"score": round(v, 5)}) for k, v in sorted(rrf.items(), key=lambda x: -x[1])]


def rank(refs: list[Reference], sub: Submission) -> list[Reference]:
    """Fused source rank (RRF) blended with chemistry-aware term overlap with the submission."""
    st = chem.tokens(" ".join(x for x in (sub.title, sub.abstract, sub.claims or "") if x))
    top_rrf = max((r.score for r in refs), default=1) or 1
    out = []
    for r in refs:
        rt = chem.tokens(r.text())
        overlap = len(st & rt) / max(1, len(st))
        out.append(r.model_copy(update={"score": round(0.5 * r.score / top_rrf + 0.5 * min(1.0, overlap * 2), 3),
                                        "before_priority": date_before(r.date, sub.priority_date)}))
    return sorted(out, key=lambda r: -r.score)


def _judge_refs(els: list[Element], refs: list[Reference], use_llm: bool) -> tuple[list[Judgment], list[dict], bool]:
    js, dropped, used = [], [], False

    def one(ref):
        if use_llm and llm.enabled():
            res, drop = judge.with_llm(els, ref)
            if res is not None:
                return res, drop, True
        return judge.lexical(els, ref), [], False

    with ThreadPoolExecutor(max_workers=4) as pool:
        for res, drop, u in pool.map(one, refs):
            js += res
            dropped += drop
            used = used or u
    return js, dropped, used


def _signals(els: list[Element], js: list[Judgment], refs: dict[str, Reference]) -> list[ElementSignal]:
    out = []
    for e in els:
        mine = [j for j in js if j.element == e.id]
        disc = [j.ref for j in mine if j.verdict == "disclosed"]
        prior = [k for k in disc if refs[k].before_priority is True]
        unk = [k for k in disc if refs[k].before_priority is None]
        part = [j.ref for j in mine if j.verdict == "partial" and refs[j.ref].before_priority is not False]
        if prior:
            out.append(ElementSignal(element=e.id, status="disclosed_before_priority", refs=prior))
        elif unk:
            out.append(ElementSignal(element=e.id, status="disclosed_date_unknown", refs=unk))
        elif part:
            out.append(ElementSignal(element=e.id, status="partially_disclosed", refs=part))
        else:
            out.append(ElementSignal(element=e.id, status="not_found_in_retrieved"))
    return out


def _fto(sub: Submission, refs: list[Reference], use_llm: bool, epo: EpoOps | None) -> list[FTOFlag]:
    """Reverse direction: does the submitted process contain every element of a patent's independent claim?
    Only patents with claim text; legal status stays 'unknown' unless a source reported one."""
    proc = Reference(key="submission", kind="paper", source="submission", title=sub.title,
                     abstract="\n".join(x for x in (sub.abstract, sub.methods or "", sub.claims or "") if x))
    flags = []
    for r in [r for r in refs if r.kind == "patent"][:6]:
        if not r.claims and epo is not None:
            r.claims = epo.claims(r)
        for c in [c for c in split_claims(r.claims) if c.independent][:2] if r.claims else []:
            if len(c.elements) < 2:
                continue
            els = [Element(id=f"C{c.number}.{i + 1}", text=t, origin="claim", claim_no=c.number) for i, t in enumerate(c.elements)]
            if use_llm and llm.enabled():
                js, _ = judge.with_llm(els, proc)
                js = js or judge.lexical(els, proc)
            else:
                js = judge.lexical(els, proc)
            hit = [j.element for j in js if j.verdict == "disclosed"]
            if len(hit) == len(els):
                status = "unknown"
                if r.venue and r.venue.startswith("legal status:"):
                    s = r.venue.split(":", 1)[1].strip().upper()
                    status = {"ACTIVE": "in_force", "PENDING": "pending", "EXPIRED": "expired", "INACTIVE": "lapsed"}.get(s, "unknown")
                flags.append(FTOFlag(ref=r.key, country=r.country, elements_disclosed=hit, legal_status=status,
                                     note=f"Every element of independent claim {c.number} appears in your described process "
                                          f"({js[0].method} comparison). Have a patent attorney check claim scope, "
                                          "legal status and territory before operating."))
    return flags


def _summary(sub: Submission, statuses: list[SourceStatus], refs: list[Reference], els: list[Element],
             sig: list[ElementSignal], js: list[Judgment]) -> tuple[str, str]:
    searched = [s.source for s in statuses if s.state in ("ok", "empty")]
    missing = {s.source: s.state for s in statuses if s.state not in ("ok", "empty")}
    n_prior = sum(1 for r in refs if r.before_priority is True)
    coverage = (f"{len(searched)} of {len(statuses)} sources searched ({', '.join(searched) or 'none'}); "
                + (f"not searched: {', '.join(f'{k} ({v})' for k, v in missing.items())}; " if missing else "")
                + f"{len(refs)} references kept"
                + (f", {n_prior} published before the priority date {sub.priority_date}" if sub.priority_date else
                   " (no priority date given, so dates were not used to filter prior art)") + ".")
    disclosed = [s for s in sig if s.status in ("disclosed_before_priority", "disclosed_date_unknown")]
    lines = [f"{len(disclosed)} of {len(els)} elements have a verified disclosing passage in at least one retrieved reference."]
    by_ref: dict[str, set[str]] = {}
    for j in js:
        if j.verdict == "disclosed":
            by_ref.setdefault(j.ref, set()).add(j.element)
    full = [k for k, v in by_ref.items() if len(v) == len(els) and els]
    if full:
        lines.append("Possible anticipation: " + ", ".join(full) + " disclose(s) every element (verify dates and context).")
    elif els:
        lines.append(f"No single retrieved reference discloses all {len(els)} elements.")
        covered, combo = set(), []
        for k, v in sorted(by_ref.items(), key=lambda x: -len(x[1])):
            if v - covered and len(combo) < 3:
                combo.append(k)
                covered |= v
        if combo and len(covered) == len(els):
            lines.append("Together, " + " + ".join(combo) + " cover all elements; whether that combination is obvious is a question for a patent attorney.")
    nf = [s.element for s in sig if s.status == "not_found_in_retrieved"]
    if nf:
        lines.append(f"Not found in the retrieved set: {', '.join(nf)}. That is a statement about this search, not proof of novelty.")
    return " ".join(lines), coverage


def bundle_hash(report: EvidenceReport) -> str:
    """sha256 over the canonical JSON of everything except the timestamp, per-source latency and the hash itself:
    the value an attestor anchors in AttestationRegistry (bytes32)."""
    d = report.model_dump(mode="json", exclude={"generated_at": True, "bundle_sha256": True, "sources": {"__all__": {"ms"}}})
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def assess(sub: Submission, sources: list[Source] | None = None) -> EvidenceReport:
    use_llm = sub.allow_llm and llm.enabled()
    ext_q, local_q, notes = build_queries(sub)
    if sources is None:
        names = [n for n in (sub.sources or settings.evidence_sources) if n in REGISTRY]
        sources = [REGISTRY[n]() for n in names]

    def go(src: Source):
        if src.name == "local":
            return run(src, local_q)
        if ext_q is None:
            return SourceStatus(source=src.name, state="disabled", detail="confidential mode without public keywords"), []
        return run(src, ext_q)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(go, sources))
    statuses = [s for s, _ in results]

    refs = merge([(s.source, r) for s, r in results])
    if not settings.evidence_allow_fixtures and any(r.fixture for r in refs):
        refs = [r for r in refs if not r.fixture]
        statuses.append(SourceStatus(source="fixtures", state="error", detail="test fixture records refused outside test mode"))
    refs = rank(refs, sub)[: sub.max_references]

    els, dropped, llm_el = elements_mod.extract(sub, use_llm)
    candidates = [r for r in refs if r.before_priority is not False][: sub.judge_top]
    js, dropped_j, llm_j = _judge_refs(els, candidates, use_llm) if els and candidates else ([], [], False)
    ref_map = {r.key: r for r in refs}
    sig = _signals(els, js, ref_map)
    epo = next((s for s in sources if isinstance(s, EpoOps) and s.configured()[0]), None)
    fto = _fto(sub, refs, use_llm, epo)
    summary, coverage = _summary(sub, statuses, refs, els, sig, js)
    if notes:
        coverage += " " + " ".join(notes)
    report = EvidenceReport(
        submission_title=sub.title, generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        sources=statuses, queries=[q for s in statuses for q in s.queries], references=refs, elements=els,
        judgments=js, element_signals=sig, summary=summary, coverage=coverage,
        trl=trl.assess("\n".join(x for x in (sub.title, sub.abstract, sub.methods or "") if x)),
        fto_flags=fto, dropped_judgments=dropped + dropped_j, llm_used=llm_el or llm_j, bundle_sha256="",
    )
    report.bundle_sha256 = bundle_hash(report)
    return report
