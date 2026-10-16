import json
from dataclasses import replace

from app.chain import indexer
from app.config import settings

DEP = {"chainId": 43113, "startBlock": 7, "deployer": "0x" + "1" * 40, "attestor": "0x" + "1" * 40, "MockUSDC": "0x" + "2" * 40,
       "ProjectRegistry": "0x" + "3" * 40, "AttestationRegistry": "0x" + "4" * 40, "SCIFraction": "0x" + "5" * 40,
       "MilestoneEscrow": "0x" + "6" * 40, "FundingPool": "0x" + "7" * 40}


def test_deployment_json_overrides_files(monkeypatch):
    monkeypatch.setattr(indexer, "settings", replace(settings, deployment_json=json.dumps(DEP)))
    assert indexer.load_deployment(43113)["FundingPool"] == DEP["FundingPool"]
    assert indexer.load_deployment(31337) is not None  # files still load for other chains


def test_bad_deployment_json_is_ignored(monkeypatch):
    monkeypatch.setattr(indexer, "settings", replace(settings, deployment_json="{not json"))
    assert indexer.load_deployment(43113) is None
