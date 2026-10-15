"""IPFS pinning. Pinata when PINATA_JWT is set; otherwise a local content-addressed store that mints
real CIDv1 (raw codec, sha2-256) identifiers and serves them at /ipfs/{cid} - fine for local demos,
clearly reported as `pinned: "local"` so nobody mistakes it for public IPFS."""

from __future__ import annotations

import base64
import hashlib
import json
import re

import httpx

from .. import blobs
from ..config import settings

PINATA = "https://api.pinata.cloud/pinning"
MAX_BYTES = 5 * 1024 * 1024
_CID_RE = re.compile(r"^(Qm[1-9A-HJ-NP-Za-km-z]{44}|b[a-z2-7]{50,})$")


def valid_cid(cid: str) -> bool:
    return bool(_CID_RE.match(cid))


def local_cid(data: bytes) -> str:
    """CIDv1, codec raw (0x55), multihash sha2-256 (0x12, 32 bytes), multibase base32 lower ('b')."""
    digest = hashlib.sha256(data).digest()
    raw = bytes([0x01, 0x55, 0x12, 0x20]) + digest
    return "b" + base64.b32encode(raw).decode().lower().rstrip("=")


def pin_bytes(data: bytes, name: str = "sci-upload") -> dict:
    if len(data) > MAX_BYTES:
        raise ValueError("payload too large (5 MB max)")
    if settings.pinata_jwt:
        r = httpx.post(
            f"{PINATA}/pinFileToIPFS",
            headers={"Authorization": f"Bearer {settings.pinata_jwt}"},
            files={"file": (name, data)},
            data={"pinataMetadata": json.dumps({"name": name}), "pinataOptions": json.dumps({"cidVersion": 1})},
            timeout=60,
        )
        r.raise_for_status()
        cid = r.json()["IpfsHash"]
        return {"cid": cid, "pinned": "pinata", "gateway_url": settings.ipfs_gateway + cid, "size": len(data)}
    cid = local_cid(data)
    blobs.put("ipfs", cid, data)
    return {"cid": cid, "pinned": "local", "gateway_url": f"/ipfs/{cid}", "size": len(data)}


def pin_json(obj: dict, name: str = "sci-metadata") -> dict:
    # Canonical encoding so identical metadata always yields the identical CID.
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return pin_bytes(data, name + ".json")


def get(cid: str) -> bytes | None:
    if not valid_cid(cid):
        raise ValueError("invalid CID")
    local = blobs.get("ipfs", cid)
    if local is not None:
        return local
    try:
        r = httpx.get(settings.ipfs_gateway + cid, timeout=30, follow_redirects=True)
        if r.status_code == 200 and len(r.content) <= MAX_BYTES:
            return r.content
    except httpx.HTTPError:
        pass
    return None
