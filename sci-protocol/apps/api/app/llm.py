"""Thin Claude wrapper: one structured-JSON call, bounded, never fatal. Every caller has a deterministic
fallback, so a missing key, timeout, refusal or malformed output degrades the feature, not the request."""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from .config import settings

log = logging.getLogger("sci.llm")

_client: anthropic.Anthropic | None = None


def enabled() -> bool:
    return settings.llm_enabled


def _get() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_s, max_retries=2
        )
    return _client


def structured(
    *, system: str, user: str, schema: dict[str, Any], effort: str = "low", max_tokens: int = 16000
) -> dict[str, Any] | None:
    """Returns the parsed JSON object, or None on any failure (caller falls back)."""
    if not enabled():
        return None
    try:
        resp = _get().beta.messages.create(
            model=settings.llm_model,
            max_tokens=max_tokens,
            # On a safety-classifier decline, the API re-runs the request on Anthropic's
            # recommended fallback model instead of returning a refusal.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        )
    except anthropic.RateLimitError as e:
        log.warning("LLM rate limited: %s", e.message)
        return None
    except anthropic.APIStatusError as e:
        log.warning("LLM API error %s: %s", e.status_code, e.message)
        return None
    except anthropic.APIConnectionError as e:
        log.warning("LLM connection error: %s", e)
        return None

    if resp.stop_reason == "refusal":
        log.warning("LLM refused (%s)", getattr(resp.stop_details, "category", None))
        return None
    if resp.stop_reason == "max_tokens":
        log.warning("LLM output truncated at max_tokens")
        return None
    text = next((b.text for b in resp.content if b.type == "text"), None)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.warning("LLM returned invalid JSON")
        return None
