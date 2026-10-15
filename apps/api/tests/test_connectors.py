"""Connector mapping tests against mock responses shaped like the public API docs.
These prove the normalisation logic, not the live API - verify live before demo day (README)."""

import json

import httpx

from app.ingest.eu_sedia import EUSediaConnector
from app.ingest.grants_gov import GrantsGovConnector


def _gg_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    if request.url.path.endswith("/search2"):
        hits = [{"id": "350001", "number": "NSF-26-001", "title": f"Research on {body['keyword']}",
                 "agency": "National Science Foundation", "openDate": "09/01/2026", "closeDate": "12/15/2027",
                 "oppStatus": "posted", "docType": "synopsis", "cfdaList": ["47.041"]}]
        return httpx.Response(200, json={"errorcode": 0, "msg": "Webservice Succeeds", "data": {"hitCount": 1, "oppHits": hits}})
    return httpx.Response(200, json={"errorcode": 0, "data": {"synopsis": {
        "synopsisDesc": "<p>Supports <b>fundamental</b> research.</p>", "awardCeiling": "500,000", "awardFloor": "0",
        "applicantTypes": [{"id": "20", "description": "Private institutions of higher education"},
                           {"id": "23", "description": "Small businesses"}],
        "applicantEligibilityDesc": "Foreign organizations are eligible to apply.",
    }}})


def test_grants_gov_normalisation():
    c = GrantsGovConnector(client=httpx.Client(transport=httpx.MockTransport(_gg_handler)))
    batch = c.fetch()
    assert not batch.errors
    assert len(batch.grants) == 1  # same opportunity found by several keyword queries is merged
    g = batch.grants[0]
    assert len(g.fields) >= 5
    assert g.source == "grants_gov" and g.source_ref == "350001"
    assert g.amount_max_usd == 500000 and g.amount_min_usd is None
    assert set(g.applicant_types) == {"university", "startup", "sme"}
    assert g.eligible_countries == ["*"]
    assert g.deadline.year == 2027 and g.summary == "Supports fundamental research."
    assert g.funder_name == "National Science Foundation"


def _eu_handler(request: httpx.Request) -> httpx.Response:
    budget = {"budgetTopicActionMap": {"1": [{"action": "RIA", "minContribution": 2000000, "maxContribution": 3000000}]}}
    return httpx.Response(200, json={"totalResults": 1, "results": [{
        "reference": "ref1", "summary": "Novel <i>materials</i> for circularity",
        "metadata": {"identifier": ["HORIZON-CL4-2027-MAT-01"], "title": ["Circular advanced materials"],
                     "deadlineDate": ["2027-02-10T17:00:00.000+0000"], "status": ["31094502"],
                     "budgetOverview": [json.dumps(budget)]},
    }]})


def test_eu_sedia_normalisation():
    c = EUSediaConnector(client=httpx.Client(transport=httpx.MockTransport(_eu_handler)))
    batch = c.fetch()
    assert not batch.errors and len(batch.grants) == 1
    g = batch.grants[0]
    assert g.title == "Circular advanced materials" and g.summary == "Novel materials for circularity"
    assert g.deadline.isoformat().startswith("2027-02-10T17:00")
    assert 2_000_000 < g.amount_min_usd < g.amount_max_usd  # EUR converted to USD
    assert "TH" not in g.eligible_countries and "DE" in g.eligible_countries


def test_connector_failure_is_contained():
    def boom(request):
        return httpx.Response(503)

    batch = GrantsGovConnector(client=httpx.Client(transport=httpx.MockTransport(boom))).fetch()
    assert batch.grants == [] and len(batch.errors) >= 1
