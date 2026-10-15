"""Drives the real Anthropic SDK against a local mock server: checks the exact request we send, and that
adversarial model output can't break the guarantees (no eligibility from the LLM, no pre-ticked
declarations, placeholders always present in narrative drafts)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import anthropic
import pytest

from app import llm
from app.forms.mapper import PLACEHOLDER

REQUESTS: list[dict] = []
MODE = {"value": "ok"}


def _message(payload: dict | None, stop="end_turn") -> dict:
    content = [{"type": "text", "text": json.dumps(payload)}] if payload is not None else []
    return {"id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "content": content,
            "stop_reason": stop, "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        REQUESTS.append({"path": self.path, "headers": dict(self.headers), "body": body})
        user = json.loads(body["messages"][0]["content"].split("\n\n", 1)[1])
        if MODE["value"] == "refusal":
            resp = _message(None, stop="refusal")
        elif "grants" in user:  # explain
            resp = _message({"explanations": [
                {"grant_id": g["grant_id"], "why_matched": f"LLM says {g['title']} fits.", "strengthen": "Add a partner letter."}
                for g in user["grants"]
            ] + [{"grant_id": "not-a-requested-id", "why_matched": "injected", "strengthen": "x"}]})
        else:  # form mapping: deliberately misbehaving model
            out = []
            for f in user["fields"]:
                if f["type"] == "radio" or f["type"] == "select":
                    out.append({"field_id": f["id"], "action": "fill", "value": "Not an option", "rationale": "guess"})
                elif "agree" in f["label"].lower():
                    out.append({"field_id": f["id"], "action": "fill", "value": "true", "rationale": "auto-consent"})
                elif f["type"] == "textarea":
                    out.append({"field_id": f["id"], "action": "draft", "value": "Our catalyst achieves 97% yield.", "rationale": "x"})
                else:
                    out.append({"field_id": f["id"], "action": "fill", "value": "30 days", "rationale": "typical"})
            resp = _message({"fields": out})
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture()
def mock_claude(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(llm, "enabled", lambda: True)
    monkeypatch.setattr(llm, "_client", anthropic.Anthropic(api_key="test-key", base_url=f"http://127.0.0.1:{srv.server_port}", max_retries=0))
    REQUESTS.clear()
    MODE["value"] = "ok"
    from app.match import explain as explainer

    explainer._cache.clear()
    yield
    srv.shutdown()
    monkeypatch.setattr(llm, "_client", None)


def test_explain_request_shape_and_output(client, persona, mock_claude):
    matches = client.post("/match", json={"profile": persona["profile"]}).json()["matches"][:3]
    ids = [m["grant"]["id"] for m in matches]
    r = client.post("/match/explain", json={"profile": persona["profile"], "grant_ids": ids}).json()
    assert r["llm"] is True
    assert set(r["explanations"]) == set(ids)  # the injected unknown id is ignored
    assert all(e["source"] == "llm" for e in r["explanations"].values())

    req = REQUESTS[0]
    assert req["path"].startswith("/v1/messages")
    assert "server-side-fallback-2026-07-01" in req["headers"].get("anthropic-beta", "")
    b = req["body"]
    assert b["model"] == "claude-opus-5-5" and b["fallbacks"] == "default"
    assert b["output_config"]["format"]["type"] == "json_schema" and b["output_config"]["effort"] == "low"
    assert "thinking" not in b and "temperature" not in b
    # The model is told eligibility is decided elsewhere, and only gets the non-confidential projection.
    assert "ALREADY been decided" in b["system"]
    sent = json.loads(b["messages"][0]["content"].split("\n\n", 1)[1])
    assert set(sent["researcher_profile"]) >= {"fields", "trl"} and "keywords" not in json.dumps(sent)
    assert len(sent["grants"]) == 3

    # Second call is served from cache - no new request.
    client.post("/match/explain", json={"profile": persona["profile"], "grant_ids": ids})
    assert len(REQUESTS) == 1


def test_refusal_falls_back_to_template(client, persona, mock_claude):
    MODE["value"] = "refusal"
    ids = [m["grant"]["id"] for m in client.post("/match", json={"profile": persona["profile"]}).json()["matches"][:2]]
    r = client.post("/match/explain", json={"profile": persona["profile"], "grant_ids": ids}).json()
    assert r["llm"] is False and all(e["source"] == "template" for e in r["explanations"].values())


def test_mapper_guards_against_misbehaving_model(client, persona, grants_by_ref, mock_claude):
    out = client.post("/applications", json={"grant_id": grants_by_ref["experiment-com"].id,
                                             "profile": persona["profile"], "applicant": persona["applicant"]}).json()
    by_id = {f["field_id"]: f for f in out["application"]["fields"]}
    assert out["application"]["llm_used"] is True
    # never pre-ticks consent, even if the model tries
    assert by_id["accept_terms"]["value"] is None and by_id["accept_terms"]["status"] == "red"
    # a choice outside the form's options is rejected, not written
    assert by_id["campaign_length"]["value"] is None and by_id["campaign_length"]["status"] == "red"
    # model-written narrative still needs the researcher: placeholder appended, invented figures flagged
    assert PLACEHOLDER in by_id["goals"]["value"]
    assert any("97" in w for w in by_id["goals"]["warnings"])
    # LLM-inferred values are amber, never green
    assert all(f["status"] != "green" for f in out["application"]["fields"] if f["source"] == "llm")
    # deterministic profile values were not sent to (or overwritten by) the model
    assert by_id["country"]["value"] == "Thailand" and by_id["country"]["source"] == "profile"
    sent = json.loads(REQUESTS[-1]["body"]["messages"][0]["content"].split("\n\n", 1)[1])
    assert "country" not in {f["id"] for f in sent["fields"]}
    assert persona["applicant"]["email"] not in json.dumps(sent)  # contact details never go to the LLM
