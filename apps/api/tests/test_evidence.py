"""Evidence engine, offline. Patent parsing is tested on REAL EPO OPS XML (fixtures/evidence/epo, Apache-2.0,
see NOTICE); retrieval/judging on an invented corpus whose records are marked _fixture and carry XX-TEST ids."""

from datetime import date
from pathlib import Path

import pytest

from app.config import settings
from app.evidence import chem, engine, judge, trl
from app.evidence.claims import split_claims
from app.evidence.models import Element, Reference, Submission
from app.evidence.sources.base import SearchQuery, Source
from app.evidence.sources.papers import ArXiv, Crossref, OpenAlex, SemanticScholar
from app.evidence.sources.patents import EpoOps, Lens, LocalCorpus, PatentsView

FIX = Path(__file__).parent / "fixtures" / "evidence"
CORPUS = FIX / "local_corpus.jsonl"


@pytest.fixture
def allow_fixtures():
    object.__setattr__(settings, "evidence_allow_fixtures", True)
    yield
    object.__setattr__(settings, "evidence_allow_fixtures", False)


def _sub(**kw):
    base = dict(
        title="Hydrothermal relithiation of spent NMC811 cathodes",
        abstract=("Spent LiNi0.8Mn0.1Co0.1O2 cathode powder was separated from aluminium foil and relithiated in 2.5 M LiOH "
                  "at 220 °C for 4 h, followed by annealing at 850 °C in oxygen. The regenerated NMC811 delivered 192 mAh/g "
                  "at 0.1 C in CR2032 coin cells and retained 91% capacity after 200 cycles."),
        methods=("Process: the spent cathode material is regenerated in three steps. Cathode powder is separated from the "
                 "current collector by ultrasonication. The cathode powder is relithiated in a LiOH solution at 220 °C. "
                 "The relithiated cathode powder is annealed at 850 °C."),
        priority_date=date(2026, 6, 1), keywords=["hydrothermal relithiation", "spent NMC cathode"],
    )
    base.update(kw)
    return Submission(**base)


# --- chemistry -------------------------------------------------------------------------------------
def test_chemistry_equivalence_and_quantities():
    assert {"nmc532", "nmc811"} <= chem.concepts("NCM523 and NMC811")
    assert "nmc811" in chem.concepts("LiNi0.8Mn0.1Co0.1O2")
    assert "nmc622" in chem.concepts("Li[Ni0.6Co0.2Mn0.2]O2")
    assert "nmc111" in chem.concepts("LiNi1/3Mn1/3Co1/3O2")
    q = {x.unit: (x.lo, x.hi) for x in chem.quantities("at 70–90 °C in 2 M H2SO4 for 2 h, 50 g/L, pH 4.5-5, 5 m long")}
    assert q == {"C": (70, 90), "M": (2, 2), "h": (2, 2), "g/L": (50, 50), "pH": (4.5, 5)}  # '5 m' is metres
    assert chem.numeric_overlaps("at 70-90 °C", "at 80 ℃") and not chem.numeric_overlaps("at 70-90 °C", "at 120 °C")


# --- claims ----------------------------------------------------------------------------------------
def test_claim_parser_handles_chemistry_and_dependencies():
    cs = split_claims("""1. A method for regenerating a spent LiNi0.8Mn0.1Co0.1O2 cathode material, comprising:
(a) separating cathode powder from a current collector; (b) relithiating in 2.5 M LiOH at 220 °C; and
(c) annealing at 850 °C, wherein the product has a capacity of at least 190 mAh/g.
2. The method of claim 1, wherein the LiOH concentration is 1.5-4 M.
3. The method according to any one of claims 1 to 2, wherein annealing takes 4 to 6 h.
4. A system for relithiating black mass comprising a hydrothermal reactor and a furnace.""")
    assert [(c.number, c.depends_on) for c in cs] == [(1, None), (2, 1), (3, 1), (4, None)]
    assert cs[0].elements == [
        "A method for regenerating a spent LiNi0.8Mn0.1Co0.1O2 cathode material",
        "separating cathode powder from a current collector", "relithiating in 2.5 M LiOH at 220 °C",
        "annealing at 850 °C", "the product has a capacity of at least 190 mAh/g"]


def test_real_epo_claims_and_biblio_parse():
    claims = EpoOps.parse_claims((FIX / "epo" / "claims_example.xml").read_text())
    cs = split_claims(claims)
    assert cs[0].independent and cs[1].depends_on == 1 and len(cs[0].elements) >= 5
    [r] = EpoOps.parse_biblio((FIX / "epo" / "biblio_example_3.xml").read_text())
    assert r.key == "pat:AU2013290010A1" and r.title == "Novel fuel composition"
    assert r.date == date(2015, 2, 5) and r.priority_date == date(2012, 7, 12) and r.family_id == "49448571"
    assert "C10L1/04" in r.cpc and r.assignees == ["PRIMUS GREEN ENERGY INC"] and r.abstract.startswith("This invention")
    cql = EpoOps.cql(SearchQuery(text="direct regeneration spent cathode", cpc=["H01M10/54"], until=date(2026, 6, 1)))
    assert cql == 'ta all "direct regeneration spent cathode" and (cpc=H01M10/54) and pd within "19000101 20260601"'


# --- source parsers (documented response shapes; live check: python -m app.evidence.smoke) ---------
def test_paper_and_patent_parsers():
    oa = OpenAlex.parse({"results": [{"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1000/ABC", "display_name": "T",
                                      "publication_date": "2020-05-01", "abstract_inverted_index": {"spent": [0], "cathodes": [1]},
                                      "primary_location": {"source": {"display_name": "J"}}, "authorships": [], "type": "article"}]})
    assert oa[0].key == "doi:10.1000/abc" and oa[0].abstract == "spent cathodes" and oa[0].venue == "J"
    cr = Crossref.parse({"message": {"items": [{"DOI": "10.1/x", "title": ["X"], "abstract": "<jats:p>Leaching <i>of</i> black mass</jats:p>",
                                                "issued": {"date-parts": [[2019, 3]]}, "type": "journal-article"}]}})
    assert cr[0].abstract == "Leaching of black mass" and cr[0].date == date(2019, 3, 1)
    s2 = SemanticScholar.parse({"data": [{"paperId": "p", "title": "Y", "externalIds": {"ArXiv": "2101.00001"}, "year": 2021}]})
    assert s2[0].key == "arxiv:2101.00001" and s2[0].kind == "preprint"
    ax = ArXiv.parse("""<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2401.01234v2</id>
        <title>Direct  regeneration</title><summary> NMC </summary><published>2024-01-03T00:00:00Z</published>
        <author><name>A B</name></author></entry></feed>""")
    assert ax[0].key == "arxiv:2401.01234" and ax[0].title == "Direct regeneration" and ax[0].date == date(2024, 1, 3)
    pv = PatentsView.parse({"patents": [{"patent_id": "11000000", "patent_title": "Z", "patent_date": "2021-05-11",
                                         "assignees": [{"assignee_organization": "Org"}], "cpc_current": [{"cpc_group_id": "H01M10/54"}]}]})
    assert pv[0].key == "pat:US11000000" and pv[0].cpc == ["H01M10/54"]
    ln = Lens.parse({"data": [{"lens_id": "1", "jurisdiction": "EP", "doc_number": "1234567", "kind": "A1",
                               "biblio": {"invention_title": [{"text": "W", "lang": "en"}]},
                               "claims": [{"lang": "en", "claims": [{"claim_text": ["1. A method comprising x."]}]}],
                               "legal_status": {"patent_status": "ACTIVE"}}]})
    assert ln[0].key == "pat:EP1234567A1" and ln[0].claims == ["1. A method comprising x."] and ln[0].venue == "legal status: ACTIVE"


# --- TRL -------------------------------------------------------------------------------------------
def test_trl_is_evidence_based_and_not_inflated():
    r = trl.assess(_sub().abstract + " We will scale the process to a pilot line next year.")
    assert r.track == "A_upcycling_materials" and r.low == 4
    assert any(e.level == 6 and not e.achieved for e in r.evidence)  # planned work listed, not counted
    lab = trl.assess("We leached black mass in a beaker and 95% Li recovery was achieved. Manufacturing cost could fall at commercial scale.")
    assert lab.track == "B_recycling_process" and lab.low == 3  # MatDAO's keyword rule scored this kind of text TRL 8-9
    none = trl.assess("A short note with no experimental detail at all.")
    assert none.low is None and none.track == "unknown"


# --- engine ----------------------------------------------------------------------------------------
class Recorder(Source):
    """Stands in for an external API; records exactly what it was sent."""
    name, kind = "fake_papers", "papers"

    def __init__(self):
        super().__init__()
        self.seen = []

    def search(self, q):
        self.seen.append(q.text)
        return []


def test_fixture_records_are_refused_outside_test_mode():
    r = engine.assess(_sub(sources=None), sources=[LocalCorpus(CORPUS)])
    assert r.references == [] and any(s.source == "fixtures" and s.state == "error" for s in r.sources)


def test_confidential_mode_never_sends_invention_text(allow_fixtures):
    rec = Recorder()
    engine.assess(_sub(), sources=[LocalCorpus(CORPUS), rec])
    assert rec.seen == ["hydrothermal relithiation spent NMC cathode"]  # keywords only
    rec2 = Recorder()
    r = engine.assess(_sub(keywords=[]), sources=[rec2])
    assert rec2.seen == [] and r.sources[0].state == "disabled"


def test_end_to_end_lexical(allow_fixtures):
    r = engine.assess(_sub(), sources=[LocalCorpus(CORPUS), Recorder()])
    keys = [x.key for x in r.references]
    assert keys[0] == "pat:XXTEST0001A1"  # the relithiation record ranks first
    assert "pat:XXTEST0004A1" not in keys  # published after the priority date: not prior art
    assert all(x.before_priority for x in r.references)
    assert r.llm_used is False and all(j.method == "lexical" for j in r.judgments)
    assert "not proof of novelty" in r.summary or "No single retrieved reference" in r.summary
    assert "2 of 2 sources searched (local, fake_papers)" in r.coverage  # an empty answer still counts as searched
    for j in r.judgments:  # every quote shown is literally in the reference
        if j.quote:
            ref = next(x for x in r.references if x.key == j.ref)
            assert j.quote in ref.text()
    # FTO direction: every element of fixture claim 1 appears in the submitted process -> flagged for an attorney
    assert [f.ref for f in r.fto_flags] == ["pat:XXTEST0001A1"] and r.fto_flags[0].legal_status == "unknown"
    assert r.trl.low == 4 and len(r.bundle_sha256) == 64
    again = engine.assess(_sub(), sources=[LocalCorpus(CORPUS), Recorder()])
    assert again.bundle_sha256 == r.bundle_sha256  # deterministic bundle hash for on-chain anchoring


def test_llm_judgments_with_fabricated_quotes_are_dropped(monkeypatch):
    ref = Reference(key="pat:XXTEST0001A1", kind="patent", source="local", title="t",
                    abstract="The powder is relithiated in a lithium hydroxide solution and then annealed.", fixture=True)
    els = [Element(id="E1", text="relithiated in LiOH", origin="abstract"),
           Element(id="E2", text="annealed at 850 °C", origin="abstract"),
           Element(id="E3", text="coin cell at 0.1 C", origin="abstract")]
    fake = {"judgments": [
        {"element": "E1", "verdict": "disclosed", "quote": "relithiated in a lithium hydroxide solution", "rationale": "same step"},
        {"element": "E2", "verdict": "disclosed", "quote": "annealed at 850 °C for 6 h in oxygen", "rationale": "invented quote"},
    ]}
    monkeypatch.setattr(judge.llm, "structured", lambda **kw: fake)
    js, dropped = judge.with_llm(els, ref)
    v = {j.element: j.verdict for j in js}
    assert v == {"E1": "disclosed", "E2": "unsupported", "E3": "absent"}
    assert dropped[0]["element"] == "E2" and dropped[0]["reason"].startswith("quote not found")


def test_api_route(client, allow_fixtures):
    object.__setattr__(settings, "patent_corpus", CORPUS)
    try:
        r = client.post("/evidence/assess", json={**_sub().model_dump(mode="json"), "sources": ["local"]})
    finally:
        object.__setattr__(settings, "patent_corpus", None)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["references"][0]["key"] == "pat:XXTEST0001A1" and "not legal advice" in body["disclaimer"]
    assert client.get("/evidence/sources").json()["trl_rubric"] == trl.RUBRIC_VERSION
