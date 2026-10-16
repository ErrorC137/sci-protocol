"""Minimal event indexer: polls eth_getLogs for the protocol contracts and decodes them with the ABIs
exported from Foundry (packages/shared/abis.json). Keeps a bounded in-memory log. The web app reads
contract state directly; this feeds /chain/activity and /chain/projects for dashboards and judges."""

from __future__ import annotations

import json
import logging
import os
import threading
from collections import deque

import httpx
from eth_abi import decode as abi_decode
from eth_hash.auto import keccak

from ..config import REPO_ROOT, settings

log = logging.getLogger("sci.indexer")

ABIS_PATH = REPO_ROOT / "packages" / "shared" / "abis.json"
CONTRACTS = ["ProjectRegistry", "FundingPool", "MilestoneEscrow", "SCIFraction", "AttestationRegistry"]
STATUS = ["Draft", "Open", "Funded", "Completed", "Failed"]


def all_deployments() -> dict[str, dict]:
    """contracts/deployments/*.json, then DEPLOYMENT_JSON (from the /setup page) on top."""
    out: dict[str, dict] = {}
    if settings.deployments_dir.exists():
        for p in settings.deployments_dir.glob("*.json"):
            d = json.loads(p.read_text())
            out[str(d["chainId"])] = d
    if settings.deployment_json:
        try:
            d = json.loads(settings.deployment_json)
            out[str(int(d["chainId"]))] = d
        except (ValueError, KeyError, TypeError) as ex:
            log.error("DEPLOYMENT_JSON ignored: %s", ex)
    return out


def load_deployment(chain_id: int | None = None) -> dict | None:
    return all_deployments().get(str(chain_id or settings.chain_id))


def _canonical_type(inp: dict) -> str:
    t = inp["type"]
    if t.startswith("tuple"):
        inner = ",".join(_canonical_type(c) for c in inp["components"])
        return f"({inner}){t[5:]}"
    return t


class EventDecoder:
    def __init__(self, abis: dict[str, list]):
        self.by_topic: dict[str, tuple[str, dict]] = {}
        for contract, abi in abis.items():
            for item in abi:
                if item.get("type") != "event":
                    continue
                sig = f"{item['name']}({','.join(_canonical_type(i) for i in item['inputs'])})"
                self.by_topic["0x" + keccak(sig.encode()).hex()] = (contract, item)

    def decode(self, log_: dict) -> dict | None:
        topics = log_.get("topics") or []
        if not topics:
            return None
        hit = self.by_topic.get(topics[0].lower())
        if not hit:
            return None
        contract, ev = hit
        args: dict = {}
        indexed = [i for i in ev["inputs"] if i.get("indexed")]
        plain = [i for i in ev["inputs"] if not i.get("indexed")]
        for inp, topic in zip(indexed, topics[1:]):
            t = _canonical_type(inp)
            if t in ("string", "bytes") or t.endswith("]") or t.startswith("("):
                args[inp["name"]] = topic  # dynamic types are hashed when indexed
            else:
                args[inp["name"]] = abi_decode([t], bytes.fromhex(topic[2:]))[0]
        if plain:
            vals = abi_decode([_canonical_type(i) for i in plain], bytes.fromhex(log_["data"][2:]))
            args.update({i["name"]: v for i, v in zip(plain, vals)})
        for k, v in list(args.items()):
            if isinstance(v, bytes):
                args[k] = "0x" + v.hex()
            elif isinstance(v, int) and v > 2**53:
                args[k] = str(v)  # keep JSON-safe
        return {
            "contract": contract,
            "event": ev["name"],
            "args": args,
            "block": int(log_["blockNumber"], 16),
            "tx": log_["transactionHash"],
            "log_index": int(log_["logIndex"], 16),
        }


class Indexer:
    def __init__(self, rpc_url: str, deployment: dict, chunk: int = 500, keep: int = 20_000):
        self.rpc = rpc_url
        self.deployment = deployment
        self.addresses = {deployment[c].lower(): c for c in CONTRACTS if c in deployment}
        self.decoder = EventDecoder(json.loads(ABIS_PATH.read_text()))
        self.next_block = int(deployment.get("startBlock", 0))
        self.chunk = chunk
        self.events: deque[dict] = deque(maxlen=keep)
        self.projects: dict[int, dict] = {}
        self._stop = threading.Event()
        self.last_error: str | None = None
        self.http = httpx.Client(timeout=30)
        # Avalanche: settled blocks only (see head()). Dev chains like anvil report `finalized` far behind the head.
        self.head_tag = os.environ.get("INDEXER_HEAD_TAG") or ("finalized" if settings.chain_id in (43113, 43114) else "latest")

    def _rpc(self, method: str, params: list):
        r = self.http.post(self.rpc, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            raise RuntimeError(body["error"])
        return body["result"]

    def head(self) -> int:
        """Index only settled blocks. Since Avalanche's Helicon upgrade (ACP-194, mainnet 2026-09-22) the C-Chain's
        `latest` is the last *executed* block and `finalized`/`safe` the last *settled* one; funds and milestone
        state are credited from settled blocks only. Nodes without the tag fall back to eth_blockNumber."""
        try:
            blk = self._rpc("eth_getBlockByNumber", [self.head_tag, False])
            if blk and blk.get("number"):
                return int(blk["number"], 16)
        except Exception as ex:  # older node / dev chain without the tag
            log.debug("head tag %s unsupported (%s); using eth_blockNumber", self.head_tag, ex)
        return int(self._rpc("eth_blockNumber", []), 16)

    def poll_once(self) -> int:
        head = self.head()
        n = 0
        while self.next_block <= head:
            to = min(head, self.next_block + self.chunk - 1)
            logs = self._rpc(
                "eth_getLogs",
                [{"fromBlock": hex(self.next_block), "toBlock": hex(to), "address": list(self.addresses)}],
            )
            for lg in logs:
                ev = self.decoder.decode(lg)
                if ev:
                    self.events.append(ev)
                    self._apply(ev)
                    n += 1
            self.next_block = to + 1
        return n

    def _apply(self, ev: dict) -> None:
        a = ev["args"]
        pid = a.get("projectId")
        if pid is None:
            return
        pid = int(pid)
        p = self.projects.setdefault(pid, {"projectId": pid})
        name = ev["event"]
        if name == "ProjectRegistered":
            p.update(researcher=a["researcher"], metadataCID=a["metadataCID"], trl=a["trl"], status="Draft", registeredBlock=ev["block"])
        elif name == "StatusChanged":
            p["status"] = STATUS[int(a["status"])]
        elif name == "TRLUpdated":
            p["trl"] = a["newTRL"]
        elif name == "CampaignOpened":
            p.update(target=str(a["target"]), raiseDeadline=a["deadline"], raised="0")
        elif name == "Contributed":
            p["raised"] = str(a["raised"])
        elif name == "MilestonesSet":
            p.update(milestones=a["count"], budget=str(a["budget"]))
        elif name == "MilestoneReleased":
            p["released"] = str(int(p.get("released", "0")) + int(a["amount"]))

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll_once()
                self.last_error = None
            except Exception as ex:
                self.last_error = str(ex)
                log.warning("indexer poll failed: %s", ex)
            self._stop.wait(settings.indexer_interval_s)

    def start(self) -> None:
        threading.Thread(target=self.run, name="sci-indexer", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def activity(self, project_id: int | None = None, limit: int = 100) -> list[dict]:
        evs = [e for e in self.events if project_id is None or str(e["args"].get("projectId")) == str(project_id)]
        return list(reversed(evs))[:limit]


_indexer: Indexer | None = None


def get_indexer() -> Indexer | None:
    return _indexer


def start_indexer() -> Indexer | None:
    global _indexer
    dep = load_deployment()
    if not (settings.indexer_enabled and settings.rpc_url and dep and ABIS_PATH.exists()):
        return None
    _indexer = Indexer(settings.rpc_url, dep)
    _indexer.start()
    log.info("indexer started for chain %s from block %s", settings.chain_id, _indexer.next_block)
    return _indexer

