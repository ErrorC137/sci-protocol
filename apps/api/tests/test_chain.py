import json
import os

import pytest

from app.chain import ipfs


def test_local_cid_matches_ipfs_raw_cidv1():
    # Well-known CIDv1 (raw, sha2-256) of the empty byte string.
    assert ipfs.local_cid(b"") == "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku"
    assert ipfs.valid_cid(ipfs.local_cid(b"hello"))
    assert not ipfs.valid_cid("../../etc/passwd")


def test_pin_and_fetch(client):
    meta = {"schema": "sci-protocol/project-metadata@1", "fields": ["materials"], "trl": 4}
    a = client.post("/ipfs/pin-json", json=meta).json()
    b = client.post("/ipfs/pin-json", json=dict(reversed(list(meta.items())))).json()
    assert a["cid"] == b["cid"] and a["pinned"] == "local"  # canonical encoding -> same CID
    assert client.get(f"/ipfs/{a['cid']}").json() == meta

    cipher = os.urandom(512)
    r = client.post("/ipfs/pin", content=cipher, headers={"content-type": "application/octet-stream"}).json()
    assert client.get(f"/ipfs/{r['cid']}").content == cipher
    assert client.get("/ipfs/not-a-cid").status_code == 400


def test_chain_config_and_fraction_metadata(client):
    cfg = client.get("/chain/config").json()
    assert "deployments" in cfg
    meta = client.get(f"/chain/fractions/{'0' * 63}1.json").json()
    assert meta["properties"]["projectId"] == 1 and "TESTNET" in meta["description"]


ANVIL = os.environ.get("ANVIL_RPC")


@pytest.mark.skipif(not ANVIL, reason="set ANVIL_RPC (and run scripts/dev-chain.sh) to test the indexer")
def test_indexer_decodes_protocol_events():
    from app.chain.indexer import Indexer, load_deployment

    dep = load_deployment(31337)
    assert dep, "deploy to anvil first (scripts/dev-chain.sh)"
    ix = Indexer(ANVIL, dep)
    ix.poll_once()
    names = {e["event"] for e in ix.events}
    assert {"ProjectRegistered", "MilestonesSet", "CampaignOpened", "Contributed", "CampaignFinalized"} <= names
    # seeded projects: B starts Funded (Failed once the demo refund ran), A starts Open (Funded after the demo)
    assert ix.projects[2]["status"] in ("Funded", "Failed")
    assert ix.projects[1]["status"] in ("Open", "Funded")
    assert ix.activity(project_id=2)
    json.dumps(list(ix.events))  # JSON-safe
