"""bq --format=prettyjson output (a JSON array) on stdin -> one JSON object per line on stdout.
Claims arrive as one text blob; the evidence engine's claim parser splits them."""

import json
import sys

rows = json.load(sys.stdin)
for r in rows:
    for k in ("priority_date", "publication_date"):
        if r.get(k) not in (None, ""):
            r[k] = int(r[k])
    for k in ("cpc", "assignees", "cites"):
        r[k] = r.get(k) or []
    r["claims"] = [r["claims"]] if r.get("claims") else []
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")
