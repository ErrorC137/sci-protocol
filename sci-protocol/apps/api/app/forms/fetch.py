"""Resolve a form reference to bytes and classify it (brief §5.1).

Accepted references (never arbitrary user URLs - only a grant's own form_url, or an upload):
    local:<file>     a form shipped in apps/api/demo_forms/
    upload:<sha256>  a form the researcher uploaded (many funders' forms sit behind a login)
    http(s)://...    the grant's published form_url
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx
from pypdf import PdfReader

from ..config import API_DIR, settings

DEMO_DIR = API_DIR / "demo_forms"
MAX_BYTES = 15 * 1024 * 1024

Kind = Literal["pdf_acroform", "pdf_flat", "html_form"]


@dataclass
class FetchedForm:
    ref: str
    data: bytes
    kind: Kind
    sha256: str


def uploads_dir() -> Path:
    d = settings.data_dir / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def store_upload(data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise ValueError("file too large (15 MB max)")
    sha = hashlib.sha256(data).hexdigest()
    (uploads_dir() / sha).write_bytes(data)
    return f"upload:{sha}"


def _load(ref: str) -> bytes:
    if ref.startswith("local:"):
        p = (DEMO_DIR / ref.removeprefix("local:")).resolve()
        if DEMO_DIR.resolve() not in p.parents:
            raise ValueError("invalid local form path")
        return p.read_bytes()
    if ref.startswith("upload:"):
        sha = ref.removeprefix("upload:")
        if not all(c in "0123456789abcdef" for c in sha) or len(sha) != 64:
            raise ValueError("invalid upload reference")
        return (uploads_dir() / sha).read_bytes()
    if ref.startswith(("http://", "https://")):
        with httpx.stream("GET", ref, follow_redirects=True, timeout=30) as r:
            r.raise_for_status()
            buf = bytearray()
            for chunk in r.iter_bytes():
                buf += chunk
                if len(buf) > MAX_BYTES:
                    raise ValueError("form larger than 15 MB")
            return bytes(buf)
    raise ValueError(f"unsupported form reference {ref!r}")


def classify(data: bytes) -> Kind:
    if data[:1024].lstrip().startswith(b"%PDF"):
        try:
            fields = PdfReader(io.BytesIO(data)).get_fields()
        except Exception:
            fields = None
        return "pdf_acroform" if fields else "pdf_flat"
    head = data[:200_000].lower()
    if b"<form" in head or b"<input" in head or b"<html" in head:
        return "html_form"
    raise ValueError("form is neither a PDF nor an HTML page")


def fetch(ref: str) -> FetchedForm:
    data = _load(ref)
    return FetchedForm(ref=ref, data=data, kind=classify(data), sha256=hashlib.sha256(data).hexdigest())
