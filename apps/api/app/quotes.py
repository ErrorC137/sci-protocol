"""Verbatim-quote checking, shared by the corpus crawler and the evidence engine.

A model may paraphrase; a quote may not. Every quote a model returns is checked here against the text it
claims to come from: whitespace-insensitive (PDF and HTML extraction break lines unpredictably, and Thai
has no word spaces), Thai digits and typographic quotes normalised, case-folded. '...' may join
fragments, which must then appear in order.
"""

from __future__ import annotations

import re
import unicodedata

from . import thai

_QUOTE_CHARS = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", "−": "-", "​": ""})


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", thai.normalize(s or "")).translate(_QUOTE_CHARS).casefold()
    return re.sub(r"\s+", "", s)


def _boundary_ok(hay: str, start: int, end: int, part: str) -> bool:
    """A quote that starts or ends with a digit must not be cut out of a longer number on the page:
    '5ล้าน' inside '1.5ล้าน', or '1มีนาคม' inside '31มีนาคม', is not a quote of that number."""
    if part[0].isdigit() and start > 0:
        prev = hay[start - 1]
        if prev.isdigit() or (prev in ".," and start > 1 and hay[start - 2].isdigit()):
            return False
    if part[-1].isdigit() and end < len(hay):
        nxt = hay[end]
        if nxt.isdigit() or (nxt in ".," and end + 1 < len(hay) and hay[end + 1].isdigit()):
            return False
    return True


def quote_in(quote: str, haystack_norm: str, min_len: int = 4) -> bool:
    """`haystack_norm` must already be norm()-ed (callers check many quotes against one text)."""
    parts = [norm(p) for p in re.split(r"\.\.\.|…", quote or "")]
    parts = [p for p in parts if p]
    if not parts or sum(len(p) for p in parts) < min_len:
        return False
    pos = 0
    for p in parts:
        i = haystack_norm.find(p, pos)
        while i >= 0 and not _boundary_ok(haystack_norm, i, i + len(p), p):
            i = haystack_norm.find(p, i + 1)
        if i < 0:
            return False
        pos = i + len(p)
    return True
