# Automating the funding corpus

The crawler watches funder pages and proposes corpus changes. A person approves every change. Nothing is marked
`verified: true` by a program.

## 1. Give it your sites (any of these formats)

Paste your list into one of these files. Duplicates and trailing slashes are handled.

**Plain text** (`data/curate/sites.txt`), one URL per line, optionally `| funder_key`:
```
# Thai agencies
https://www.nia.or.th/news | nia
https://www.tsri.or.th/news/ | tsri
https://pmub.or.th/announcement/
```

**CSV** (`data/curate/sites.csv`):
```
url,funder,follow,max_pages
https://www.nrct.go.th/news,nrct,ทุน;ประกาศ;call,20
```

**YAML** (`data/curate/sites.yaml`, the default). `python -m app.curate seed-sites` writes the 68 funder home pages
already in the corpus. Replace them with **call or news pages** where you can, because home pages rarely list calls.

| Field | Meaning |
|---|---|
| `url` | Page to watch (required) |
| `funder` | Key in `data/seed/grants.yaml`. Omit it and the review queue proposes a new funder |
| `follow` | Regexes; a link is followed one hop if its path or anchor text matches. The defaults cover English and Thai call words (ทุน, ประกาศ, ข้อเสนอ, รับสมัคร, สนับสนุน, เปิดรับ…) |
| `max_pages` | Pages per site per run (default 12) |
| `depth` | Link hops from the watched page (default 1) |

## 2. Run it

```bash
cd apps/api
export CURATE_CONTACT="you@yourdomain"     # goes into the User-Agent so site owners can reach you
export ANTHROPIC_API_KEY=...                # optional: without it, Thai/English heuristics extract deadline + max amount
python -m app.curate run --sites ../../data/curate/sites.txt
```

**What it does:**
- Fetching:
  - Obeys robots.txt (RFC 9309: an unreachable robots.txt means *don't crawl*).
  - Waits at least 5 seconds between requests to the same host, longer if the site sets a `Crawl-delay`.
  - Uses conditional GETs, so unchanged pages cost one 304 response.
- Reading:
  - Handles TIS-620 / windows-874 Thai pages, PDFs and Word files.
  - Re-extracts only pages whose text changed since the last run.
- Extracting: every extracted value needs a quote found **verbatim** on the page. Dates and amounts must also
  appear inside their quote. Values that fail are listed under `dropped` instead of being kept. Thai Buddhist-era
  years, Thai digits and ล้าน/แสน/หมื่น amounts are converted.
- Output: a review queue at `data/curate/review/queue-YYYY-MM-DD.yaml`.

**On 100+ sites:** a full run takes roughly (sites × pages × 5 s) ÷ workers. 100 sites × 12 pages ÷ 6 workers is
about 17 minutes. Use `--limit 10` for a first test.

## 3. Review and apply

Open the queue. For each item:
1. Open `source_url` and check the `evidence` quotes against the live page.
2. Set `decision: accept` or `decision: reject`.
3. Set `set_verified: true` only if you confirmed the values on the live page today.
4. For a new funder, fill in `new_funder.name`, `type` and `country`.

Then:
```bash
python -m app.curate apply ../../data/curate/review/queue-YYYY-MM-DD.yaml
python -m app.curate stale --days 90        # entries nobody has checked recently
```

`apply` edits `data/seed/grants.yaml` in place and keeps its comments and layout. It refuses items with missing
funder details, then reloads the corpus to prove it still parses.

## 4. Schedule it

`.github/workflows/curate.yml` runs weekly and opens a pull request containing the review queue. It never edits
`grants.yaml`. Set the repo variable `CURATE_CONTACT`. `ANTHROPIC_API_KEY` is optional as a repo secret.

## Limits, stated plainly

- Login-walled portals (many Thai agency systems) cannot be crawled. For those, upload the call document or form
  instead.
- JavaScript-only sites return little text. [crawl4ai](https://github.com/unclecode/crawl4ai) (Apache-2.0) is the
  upgrade path.
- Respect each site's terms. The crawler identifies itself and is deliberately slow; do not lower `--delay` on
  government servers.
- From the build sandbox no funder site was reachable, so the pipeline was tested against simulated sites only.
  Run `--limit 3` first and read the output.
