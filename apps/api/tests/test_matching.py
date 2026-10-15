from datetime import datetime, timedelta, timezone

from app.match import filters, ranker
from app.models.schemas import Grant, ProjectProfile


def _g(**kw) -> Grant:
    base = dict(id="g", title="t", source="test", source_ref="r")
    base.update(kw)
    return Grant(**base)


def _p(**kw) -> ProjectProfile:
    base = dict(fields=["materials"], trl=4, applicant_type="university", country="TH",
                funding_min_usd=5000, funding_max_usd=50000)
    base.update(kw)
    return ProjectProfile(**base)


def _status(rules, name):
    return next(r.status for r in rules if r.rule == name)


# --- Stage 1: hard filters ------------------------------------------------------

def test_country_rule():
    assert _status(filters.evaluate(_g(eligible_countries=["TH"]), _p()), "country") == "pass"
    assert _status(filters.evaluate(_g(eligible_countries=["*"]), _p()), "country") == "pass"
    assert _status(filters.evaluate(_g(eligible_countries=["SG"]), _p()), "country") == "fail"
    assert _status(filters.evaluate(_g(eligible_countries=[]), _p()), "country") == "unknown"


def test_trl_band():
    assert _status(filters.evaluate(_g(trl_min=3, trl_max=6), _p(trl=4)), "trl") == "pass"
    r = filters.evaluate(_g(trl_min=6, trl_max=8), _p(trl=4))
    assert _status(r, "trl") == "fail" and "TRL ≥ 6" in next(x.detail for x in r if x.rule == "trl")


def test_amount_overlap():
    assert _status(filters.evaluate(_g(amount_min_usd=0, amount_max_usd=3000), _p()), "amount") == "fail"
    assert _status(filters.evaluate(_g(amount_min_usd=100000, amount_max_usd=None), _p()), "amount") == "fail"
    assert _status(filters.evaluate(_g(amount_min_usd=10000, amount_max_usd=20000), _p()), "amount") == "pass"


def test_deadline():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    assert _status(filters.evaluate(_g(deadline=past), _p()), "deadline") == "fail"
    assert _status(filters.evaluate(_g(deadline=past, rolling=True), _p()), "deadline") == "pass"
    assert _status(filters.evaluate(_g(), _p()), "deadline") == "unknown"


def test_incorporation_equity_ip():
    assert _status(filters.evaluate(_g(requires_incorporation=True), _p()), "incorporation") == "fail"
    assert _status(filters.evaluate(_g(requires_incorporation=True), _p(applicant_type="startup")), "incorporation") == "pass"
    assert _status(filters.evaluate(_g(equity_taken=True), _p(constraints=["no_equity"])), "equity") == "fail"
    assert _status(filters.evaluate(_g(equity_taken=True), _p()), "equity") == "pass"
    assert _status(filters.evaluate(_g(ip_assignment_required=True), _p(constraints=["no_ip_assignment"])), "ip") == "fail"


def test_unknown_never_excludes():
    rules = filters.evaluate(_g(), _p())
    assert filters.is_eligible(rules)
    assert any(r.status == "unknown" for r in rules)


# --- Stage 2: ranking ------------------------------------------------------------

def test_trl_centering_prefers_band_middle():
    p = _p(trl=4)
    assert ranker.trl_centering(p, _g(trl_min=3, trl_max=5)) > ranker.trl_centering(p, _g(trl_min=4, trl_max=9))


def test_deadline_feasibility_penalises_short_runway():
    soon = _g(deadline=datetime.now(timezone.utc) + timedelta(days=5))
    later = _g(deadline=datetime.now(timezone.utc) + timedelta(days=60))
    assert ranker.deadline_feasibility(soon) < ranker.deadline_feasibility(later)


def test_weights_sum_to_one():
    assert abs(ranker.W_SIM + ranker.W_FIELD + ranker.W_TRL + ranker.W_AMOUNT + ranker.W_DEADLINE - 1.0) < 1e-9


# --- Profile is non-confidential by construction ---------------------------------

def test_profile_rejects_free_text_subdomains():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _p(subdomains=["water hyacinth biochar with lignin binder at 3:1"])


# --- End to end over the curated corpus -------------------------------------------

def test_match_demo_persona(client, persona):
    r = client.post("/match", json={"profile": persona["profile"]})
    assert r.status_code == 200, r.text
    body = r.json()
    ids = [m["grant"]["source_ref"] for m in body["matches"]]
    assert len(ids) >= 8
    # Thai sources the persona is eligible for are present...
    assert {"nrct-research-grants", "pmuc-competitiveness"} <= set(ids)
    # ...and ones it is not eligible for are excluded by the rules, never ranked.
    assert "nia-open-innovation" not in ids  # needs a registered company
    assert "yc" not in ids  # takes equity; persona said no equity
    assert "eic-pathfinder-open" not in ids  # country + consortium
    assert body["excluded_by_rule"]["incorporation"] >= 1
    assert all(m["eligible"] and m["score"]["total"] > 0 for m in body["matches"])
    scores = [m["score"]["total"] for m in body["matches"]]
    assert scores == sorted(scores, reverse=True)
    # near misses fail exactly one rule the researcher could act on
    for m in body["near_misses"]:
        assert [r["rule"] for r in m["rules"] if r["status"] == "fail"] != ["country"]
    # what-if: registering a company is the single biggest unlock for a university researcher
    unlocks = {u["change"]: u for u in body["unlocks"]}
    assert unlocks["incorporate"]["count"] >= 5
    assert body["unlocks"][0]["change"] == "incorporate"
    assert body["trl_assessment"]["consistent"] is True


def test_explain_uses_template_without_key(client, persona):
    r = client.post("/match", json={"profile": persona["profile"]})
    top = [m["grant"]["id"] for m in r.json()["matches"][:3]]
    e = client.post("/match/explain", json={"profile": persona["profile"], "grant_ids": top})
    assert e.status_code == 200
    body = e.json()
    assert body["llm"] is False
    for gid in top:
        exp = body["explanations"][gid]
        assert exp["source"] == "template" and exp["why_matched"] and exp["strengthen"]


def test_explain_refuses_ineligible_grants(client, persona, grants_by_ref):
    nia = grants_by_ref["nia-open-innovation"].id
    e = client.post("/match/explain", json={"profile": persona["profile"], "grant_ids": [nia]})
    assert e.json()["explanations"] == {}


def test_discover_search(client):
    r = client.get("/grants", params={"q": "biomass construction materials", "country": "TH"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items and items[0]["similarity"] >= items[-1]["similarity"]
    r = client.get("/grants", params={"field": "digital", "funder_type": "web3"})
    assert all(i["grant"]["funder_type"] == "web3" for i in r.json()["items"])


def test_health(client):
    h = client.get("/health").json()
    assert h["store"] == "memory" and h["corpus_size"] >= 60 and h["llm"]["enabled"] is False
