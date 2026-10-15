"""IPFS pinning, chain config, indexed activity and ERC-1155 metadata."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from ..chain import indexer, ipfs
from ..config import settings

router = APIRouter()

EXPLORERS = {84532: "https://sepolia.basescan.org", 97: "https://testnet.bscscan.com", 31337: None}


@router.post("/ipfs/pin-json")
async def pin_json(request: Request) -> dict:
    body = await request.body()
    if len(body) > 256 * 1024:
        raise HTTPException(413, "metadata too large")
    try:
        obj = json.loads(body)
    except ValueError as ex:
        raise HTTPException(400, "body must be JSON") from ex
    if not isinstance(obj, dict):
        raise HTTPException(400, "body must be a JSON object")
    return ipfs.pin_json(obj)


@router.post("/ipfs/pin")
async def pin_raw(request: Request) -> dict:
    """Raw bytes - used by the vault for client-side-encrypted ciphertext. The server never sees plaintext."""
    data = await request.body()
    if not data:
        raise HTTPException(400, "empty body")
    try:
        return ipfs.pin_bytes(data, "sci-vault-ciphertext.bin")
    except ValueError as ex:
        raise HTTPException(413, str(ex)) from ex


@router.get("/ipfs/{cid}")
def get_ipfs(cid: str) -> Response:
    try:
        data = ipfs.get(cid)
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex
    if data is None:
        raise HTTPException(404, "not found")
    media = "application/json" if data[:1] in (b"{", b"[") else "application/octet-stream"
    return Response(data, media_type=media, headers={"Cache-Control": "public, max-age=31536000, immutable"})


@router.get("/chain/config")
def chain_config() -> dict:
    deployments = {}
    if settings.deployments_dir.exists():
        for p in settings.deployments_dir.glob("*.json"):
            d = json.loads(p.read_text())
            deployments[str(d["chainId"])] = d
    return {
        "chain_id": settings.chain_id,
        "deployment": deployments.get(str(settings.chain_id)),
        "deployments": deployments,
        "explorer": EXPLORERS.get(settings.chain_id),
    }


def _ix() -> indexer.Indexer:
    ix = indexer.get_indexer()
    if ix is None:
        raise HTTPException(503, "indexer disabled (set INDEXER_ENABLED=true and RPC_URL)")
    return ix


@router.get("/chain/activity")
def activity(project_id: int | None = None, limit: int = 100) -> dict:
    ix = _ix()
    return {"events": ix.activity(project_id, min(limit, 500)), "next_block": ix.next_block}


@router.get("/chain/projects")
def projects() -> dict:
    ix = _ix()
    return {"projects": sorted(ix.projects.values(), key=lambda p: -p["projectId"])}


@router.get("/chain/fractions/{token_id}.json")
def fraction_metadata(token_id: str) -> dict:
    """ERC-1155 metadata. Wallets substitute {id} with 64 hex chars; decimal ids also accepted."""
    try:
        n = int(token_id, 16) if len(token_id) == 64 else int(token_id)
    except ValueError as ex:
        raise HTTPException(400, "bad token id") from ex
    ix = indexer.get_indexer()
    p = ix.projects.get(n, {}) if ix else {}
    return {
        "name": f"UPLO Fraction - Project #{n}",
        "description": (
            "TESTNET mechanism demonstration. One unit per USDC base unit contributed to a successful, "
            "milestone-gated raise. Not a security offering; no real value."
        ),
        "decimals": 6,
        "properties": {"projectId": n, "metadataCID": p.get("metadataCID"), "status": p.get("status")},
    }
