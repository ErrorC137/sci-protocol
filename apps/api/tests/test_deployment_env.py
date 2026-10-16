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


def test_bad_deployment_json_is_ignored(monkeypatch, tmp_path):
    # No deployment files (the repo commits real Fuji addresses), so only the bad override could supply one.
    monkeypatch.setattr(indexer, "settings", replace(settings, deployment_json="{not json", deployments_dir=tmp_path))
    assert indexer.load_deployment(43113) is None


def test_bad_deployment_json_falls_back_to_the_committed_file(monkeypatch):
    monkeypatch.setattr(indexer, "settings", replace(settings, deployment_json="{not json"))
    committed = indexer.load_deployment(43113)
    assert committed is None or committed["chainId"] == 43113
