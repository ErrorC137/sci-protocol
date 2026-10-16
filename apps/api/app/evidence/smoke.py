"""Live check of every configured source with a NON-confidential query. Run once keys and network are set:

    python -m app.evidence.smoke ["custom query"]

Prints state, latency and the top titles per source, so a broken endpoint or changed response shape is
visible before a researcher relies on a report. Nothing here is confidential; do not put invention text in it."""

from __future__ import annotations

import sys
from datetime import date

from .engine import REGISTRY
from .sources.base import SearchQuery, run


def main() -> int:
    text = sys.argv[1] if len(sys.argv) > 1 else "direct regeneration spent NMC cathode relithiation"
    q = SearchQuery(text=text, cpc=["H01M10/54", "Y02W30/84"], until=date.today(), limit=5)
    bad = 0
    for name, cls in REGISTRY.items():
        status, refs = run(cls(), q)
        print(f"{name:18} {status.state:12} {status.ms or 0:>6} ms  {status.detail or ''}")
        for r in refs[:3]:
            print(f"{'':20}- {r.key}  {r.date}  {r.title[:90]}")
        bad += status.state == "error"
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
