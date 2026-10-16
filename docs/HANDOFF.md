# Handoff: UPLO / SCI Protocol (written 16 Oct 2026, after the hackathon)

This file is for the next person or AI agent working on this repo. It covers what the project is, what was built,
what was verified and how, what is deployed where, what is unfinished or uncertain, and what to do next.
**No secret values appear in this file.** Where something was not verified, it says so.

---

## 0. One-paragraph summary

**UPLO** (the brand) / **SCI Protocol** (the codebase name) is a hackathon prototype.
- **Scope** (2026 hackathon brief): a research-funding platform for battery recycling and upcycling.
- **Discover and match:** researchers describe their work in non-confidential terms and get matched to grants,
  accelerators and other funding routes from a curated corpus of 150 programmes.
- **Forms:** application forms are pre-filled from their profile, and a human reviews every field before export.
- **On-chain raise:** projects can raise milestone-gated crowdfunding on **Avalanche Fuji testnet**. Funds sit in an
  escrow, are released when an attestor approves milestone evidence, and are refunded if a deadline is missed.
  ERC-1155 "fraction" receipts demonstrate tokenisation.
- **Evidence engine:** compares a research claim against real papers and patents and estimates TRL from evidence.

It is **not** MatDAO's product. It reuses MatDAO's Vercel team and Supabase org, but as separate projects.
The team did not place at the hackathon (winners were web3 veterans). The code is in a working, tested state.

---

## 1. Names, people, repos

| Thing | Value |
|---|---|
| GitHub repo | `ErrorC137/sci-protocol` (public). Default branch `main`. |
| Branches | `main`, `uplo-rebrand`, `uplo-avalanche` were kept identical at the end. `uplo-rebrand` is the one Render and Vercel deploy. Push to it, then fast-forward the others. `wip/form-safety` is an obsolete snapshot: delete it (the build sandbox could not). |
| Owner | ErrorC137 (the user). |
| Teammate | Supawill (git author "supawillwork-cloud" / "Supawill Lertvongkornkit"). Worked through their own Claude Code sessions on `uplo-rebrand`: UPLO rebrand, landing page, Phases 2-5, infrastructure, Fuji deployment. |
| This session | Claude Code (cloud): built SCI Protocol, the research, the evidence engine, forms and crawler, the Avalanche switch, `/setup`, the spreadsheet import, and the merges. Commits carry `Claude-Session:` trailers. |
| MatDAO repos (context only) | `ErrorC137/MatDAO-Platform-V1`, `ErrorC137/backend`, `ErrorC137/MatDAO-Platform` (private). They were audited early on (section 9). None of their code is used here. |

Brand and design docs: `docs/uplo/brand-brief.md`, `docs/uplo/REBRAND_NOTES.md`. User-facing text says UPLO;
internal identifiers (contracts `SCIFraction`, packages `@sci/*`, env `SCI_*`) keep the SCI name on purpose.

---

## 2. What is deployed (as of the end of the session)

| Piece | Where | Notes |
|---|---|---|
| Web (Next.js 14) | Vercel team **MatDAO** (`mat-dao`), project `sci-protocol` → `https://sci-protocol.vercel.app` | Deployed with the **Vercel CLI** (`npx vercel deploy --prod` from the repo root), **not** git-linked. A dashboard "Redeploy" rebuilds the *last uploaded source*. `NEXT_PUBLIC_*` values are baked in at build time. |
| API (FastAPI, Docker) | Render Blueprint `uplo-hackathon` → service `uplo-api` (Singapore, **free** plan) → `https://uplo-api.onrender.com/health` | Auto-deploys on push to `uplo-rebrand`. Free plan: sleeps after 15 idle minutes, about 50 s cold start, no disk, no cron. |
| Database | Supabase org `MatDAO_V1`, project `uplo-hackathon` (Singapore), Postgres + pgvector, Data API off | Free plan pauses after about 7 idle days. Migrations in `supabase/migrations/` run on every API boot (idempotent). |
| Contracts | **Avalanche Fuji (43113)**, deployed 16 Oct 2026 by the team via `/setup` | Addresses in `contracts/deployments/43113.json` (below). Start block 59543464. Admin and attestor = `0xd5eC963BED4132BA1922E75FeE8C3ae5A499a6a0` (the team's wallet). |
| Wallet connect | Reown (WalletConnect) project `matdao` | The project id is public. |

Fuji addresses (public):
```
MockUSDC            0xd66313481E6cFD9bc459a0571c87e38928e2BED5   (testnet stablecoin with an open faucet)
ProjectRegistry     0x366Dc6DaA48E279A5D1333a3324Ee4e30260Ef51
AttestationRegistry 0x7F61DE1E77Fdd786AB63795332f855A7Db483000
SCIFraction         0x469244e785e6D69b298a64bb841B1Da18966bD0D   (ERC-1155 receipts)
MilestoneEscrow     0xF0487Cc97079Fc65464151fD16e2c88912787b43
FundingPool         0x30fa1DF6abBEb7a684126C8eE2Fe80d7BD560C1a
```

Environment variable **names** and where they live: `docs/uplo/INFRA.md`. Click-by-click setup: `docs/uplo/GO_LIVE.md`.
Key ones:
- **Render:** `DATABASE_URL` (Supabase *Session pooler* URI, port 5432), `CHAIN_ID=43113`, `RPC_URL` (public Fuji
  node), `INDEXER_ENABLED=true`, `CORS_ORIGINS`, optional `ANTHROPIC_API_KEY`, optional `DEPLOYMENT_JSON`.
- **Vercel:** `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_CHAIN_ID=43113`, `NEXT_PUBLIC_RPC_URL`,
  `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID`, optional `NEXT_PUBLIC_DEPLOYMENT_JSON`.

Last known state (from the teammate's `docs/uplo/PITCH_READINESS.md`, not re-checked here):
- API up with `store: postgres`, 150 programmes, chain 43113.
- LLM off on Render (no `ANTHROPIC_API_KEY`), so explanations use templates.
- The web needed a fresh CLI deploy to pick up Phases 4-5.
- At the very end the user saw "Deploy the contracts to Base Sepolia" on `/setup`. That means the live Vercel build
  still had `NEXT_PUBLIC_CHAIN_ID=84532`. The code defaults to Fuji; only that env var, or a stale build, causes it.
  **Check this first if the site shows Base Sepolia.**

**Not verifiable from the build sandbox:** Render, Vercel, Supabase and the Fuji RPC were all blocked by its network
policy. Live behaviour was reported by the teammate's sessions (e.g. "indexer caught up to head on Fuji"), not
observed by this session.

---

## 3. Architecture and repo layout

```
apps/web        Next.js 14 · Tailwind (UPLO tokens) · wagmi 2 + viem 2 + RainbowKit 2
  app/(app)/    discover, profile, matches, apply/[id], evidence, raise, raise/[id], raise/new, vault, setup,
                overview, commercial-finance, validation (Phases 4-5 by the teammate)
  app/page.tsx  landing (teammate's 3D/GSAP landing; wallet stack loads on demand)
  lib/chain-meta.ts  target chain (NEXT_PUBLIC_CHAIN_ID, default 43113) + deployment (env override or @sci/shared)
  lib/bytecode.json  creation bytecode for /setup (generated by scripts/export-abis.mjs)
apps/api        FastAPI · Pydantic v2 · Anthropic SDK (claude-opus-5-5) · psycopg/pgvector
  app/ingest    curated YAML (data/seed/grants.yaml) + Grants.gov + EU SEDIA connectors
  app/match     hard eligibility filters → hybrid rank → explanations (LLM or templates)
  app/forms     PDF AcroForm / flat PDF / Word .docx / HTML forms → field specs → mapper → review → export
  app/evidence  prior-art + literature retrieval, quote-checked claim chart, TRL from evidence, FTO flags
  app/curate    funder-site crawler → verified candidates → review queue → apply into grants.yaml
  app/chain     IPFS (Pinata or Postgres blobs), event indexer, chain config
contracts       Foundry, Solidity 0.8.28, OpenZeppelin 5: ProjectRegistry, MilestoneEscrow, FundingPool,
                SCIFraction (ERC-1155), AttestationRegistry, MockUSDC; script/Deploy.s.sol, SeedDemo.s.sol, Wiring.sol
packages/shared ABIs, deployments, shared TS types
tools/portal-fill  Playwright helper that types reviewed answers into a funder's web portal (never submits)
tools/models/receivables_model.py  numbers behind the business-model critique
data/seed/grants.yaml   corpus: 128 funders, 150 programmes (all verified: false)
data/curate/            crawler watch list (140 sites), the team spreadsheet, review queues
scripts/e2e/smoke.py    full browser smoke test (teammate's)
.claude/agents/         9 subagent definitions (battery scientist, RWA structurer, Thai regulatory, auditor, ...)
docs/                   RESEARCH.md, BUSINESS_MODEL.md, CURATION.md, DEPLOY.md, SHEET_IMPORT.md, uplo/*
```

---

## 4. What was built, in order

1. **SCI Protocol from the hackathon brief.**
   - Aggregator + curated corpus.
   - Non-confidential matching (no free-text invention description).
   - Form pre-fill with mandatory review; export locked until review.
   - Milestone-gated crowdfunding: registry → escrow → pool → attestations → refunds.
   - ERC-1155 fractions on testnet; vault (client-side encryption + hash anchoring).
   - Docs and a demo script.
2. **Pivot to Avalanche.**
   - Fuji is the default target; C-Chain mainnet is defined but warned against without a legal structure.
   - The indexer reads `finalized` blocks on Avalanche (Helicon semantics).
   - Routescan verification config in `contracts/foundry.toml`.
3. **Research sweep** with adversarial fact-checks, written up in `docs/RESEARCH.md`. Topics: Bio Protocol,
   Conception X / IP-NFTs, on-chain receivables, Avalanche, battery recycling, Thai law, DeSci barriers, and
   patent/literature data sources. **§0 of that file says how far to trust each part.** The Thai-law and
   DeSci-barriers sections are largely unverified recall.
4. **Business model critique** of the team's "Circular Innovation Finance" draft (`docs/BUSINESS_MODEL.md`, numbers in
   `tools/models/receivables_model.py`).
   - Verdict: keep the accounting separation, but recycling-finance fees cannot fund meaningful research.
     USD 250k a year of research needs about USD 24M continuously advanced at the draft's own numbers, and about
     USD 48M with a fairer tranched structure.
   - In the receivables example the platform takes 40% of the spread and the funder bears all the risk.
   - The pool is likely a regulated investment product in Thailand.
   - Recommendation:
     - **Two separate entities**: receivables finance must stand alone, and research is funded by corporates and
       grants.
     - **No platform token.**
     - **Fractions stay testnet-only.**
   - The teammate's landing page still pitches the original invoice-financing story, labelled "illustrative".
5. **Evidence engine** (`apps/api/app/evidence`, page `/evidence`).
   - Closed-world judging: every "disclosed" verdict must quote the reference verbatim
     (`app/quotes.py` checks it, with digit-boundary rules).
   - Priority-date filter, chemistry normalisation (NMC/NCM/formulae), TRL rubric `battery-trl-0.1` with two tracks.
   - Confidential mode sends only keywords externally.
   - Sources: OpenAlex (needs a free key since Feb 2026), Crossref, Semantic Scholar, arXiv, EPO OPS, PatentsView
     (key issuance reportedly paused), Lens, and a local BigQuery-exported patent corpus.
   - Tested only offline with fixtures (real EPO XML samples). **Live sources were never reachable from the sandbox.**
6. **Word/Thai forms.**
   - `.docx` parsing and filling (content controls, legacy fields, tables, dotted blanks, ☐ glyphs).
   - Thai placeholders `[ต้องเพิ่ม: …]` and Thai dates/amounts (`app/thai.py`).
   - A demo Thai proposal form (`apps/api/demo_forms/thai-research-proposal-demo.docx`).
   - Exports: PDF, docx, JSON, portal payload, markdown pack.
7. **Corpus crawler** (`python -m app.curate`, docs in `docs/CURATION.md`).
   - Robots.txt via protego, redirects checked hop by hop, per-host pacing.
   - Thai date and amount parsing; values kept only when a verbatim quote supports them.
   - A review queue a human edits, and an apply step that preserves `grants.yaml` layout (ruamel).
8. **Portal helper** (`tools/portal-fill`): fills a funder's web portal from the reviewed payload and never submits.
9. **Merge onto the teammate's UPLO branch** (16 Oct). Their branch had started from an older snapshot (Base Sepolia,
   none of items 2-7). All of it was ported without touching their landing or design system, and the Evidence page
   was restyled to UPLO tokens.
10. **Team spreadsheet import** (`apps/api/scripts/import_sheet.py`, report in `docs/SHEET_IMPORT.md`).
    - The user's xlsx had 100 programmes. 75 were added as `verified: false, confidence: low`, 25 were already in the
      corpus, and every link went onto the crawler watch list.
    - 26 rows are flagged, e.g. NSF rows linking to NIH's page, an inverted KIAT amount range, "Bied ForLab"
      unidentifiable, TSRI listed twice, and US SBIR being US-owned-only, with its authority believed lapsed
      since 1 Oct 2025 but **unconfirmed**.
11. **`/setup`**: deploys all six contracts and wires the 13 role grants from the user's own wallet, so no private key
    sits on a server. Progress is resumable. `DEPLOYMENT_JSON` / `NEXT_PUBLIC_DEPLOYMENT_JSON` overrides exist. The
    team used it to deploy on Fuji.
12. **Hardening.**
    - The indexer refuses an RPC that serves another chain.
    - The curated corpus is upserted on every boot.
    - Export refuses (409) when the source form changed.
    - Form safety rules (next item).
13. **Form safety** (two parallel agents, 193 new tests).
    - The parser never guesses a label: an empty label means red.
    - Merged cells, zip-bomb guard, and every parse error returns a 400.
    - The mapper has one hard gate: declarations, bank/ID/signature, dates, percentages, someone-else's details,
      track record and budget lines are always red.
    - Non-USD amounts are amber estimates; only an explicit USD field can be green.
    - The LLM never sees gated fields and can never produce green.

The teammate's work in the same period: UPLO design system, the landing (Phases 2-3), and the information
architecture (Overview, Commercial Finance and Validation pages, Phase 4). Phase 5 added the battery-upcycling demo
projects, `docs/uplo/PITCH_READINESS.md`, the Fuji deployment, and an indexer fix for the public node's 100-block
`eth_getLogs` cap.

---

## 5. Verification record (what was actually run)

| Check | Result |
|---|---|
| API tests (`apps/api`, `.venv/bin/python -m pytest -q`) | **261 passed, 9 skipped** at `2fdb248`. Also ran on Python 3.11, the Dockerfile's version. The skips are Postgres/anvil suites without their env vars. |
| Contract tests (`forge test`) | 29 tests in `FundingFlow.t.sol` + `Registries.t.sol`. Last run passed (before the hackathon day); contracts unchanged since. |
| portal-fill tests | 3 pass (earlier). |
| Web | `next build`, `tsc --noEmit`, `next lint` clean at `07a9340` (with the teammate's Phases 4-5). |
| Full browser smoke test | **Passed ("ALL GOOD") on a local anvil** with contracts deployed through `/setup` and a headless Chromium with an injected test wallet. Covers profile → matches → pre-filled application → contribute → evidence → approve → release → missed milestone → refund → new raise → vault. Re-run after the form-safety changes: all 9 step screenshots were produced, but the wrapper was killed by a time limit before the final line printed. |
| `/setup` on anvil | 13 steps, roles verified with `cast` (MODULE/MINTER/ATTESTOR/POOL, fraction URI). Re-verified after the review fixes. |
| Docker layout | API booted from the Dockerfile's file layout on Python 3.11 with a fresh `pip install -r requirements.txt`, using about 137 MB RSS (Render free has 512 MB). Docker itself had no daemon in the sandbox. |
| Live Fuji / Render / Vercel | **Not observed by this session** (network-blocked). The teammate reports a deployment and indexer catch-up on Fuji. |

---

## 6. Known issues and open findings

From an adversarial review of the merge. **The setup-page findings were fixed (`07a9340`); the rest were reported by
one reviewer and NOT independently verified**, because the verifiers hit the session limit:

1. **[reported high] Export 409 guard compares against a mutable cached template.** If a *remote* funder form changes,
   new drafts can stay blocked, and after a refresh old drafts might pass. Uploaded and demo forms are unaffected.
   Suggested fix: store the form sha on the Application at creation and version templates by sha.
   `apps/api/app/routers/forms.py` `_source`, `apps/api/app/forms/service.py`.
2. **[reported medium] `DEPLOYMENT_JSON` is only checked for `chainId`.** A malformed `startBlock` or address could
   crash API startup. Validate all fields in `indexer.all_deployments()` and guard `start_indexer()`.
3. **[reported low]** A `DEPLOYMENT_JSON` without known contract keys would run `eth_getLogs` with no address filter.
   Refuse to start in that case.
4. **[reported low]** `render.yaml` pins `RPC_URL` as a value, so a dashboard-set provider URL is overwritten on
   Blueprint sync. Consider `sync: false` plus a code default.
5. **[reported low]** Every Postgres boot re-embeds the whole curated corpus. Cheap with the local hashing embedder,
   but wasteful with Voyage. Skip unchanged rows.
6. **Not reviewed at all** (reviewers hit the limit): the spreadsheet import's per-row accuracy, the web merge
   (class names and tones after the rebrand), and the docs' factual claims.
7. **Mapper limits** the form agent itself listed:
   - A bare "Title" is filled with the project name.
   - "Total budget (USD)" gets the funding need.
   - LLM suggestions for checkbox groups aren't checked against the options.
   - Rules depend on the docx hint format (`[table row]`, ` | prev:`).
8. **Corpus quality:** all 150 programmes are `verified: false`. Amounts, TRL bands, eligibility and deadlines are
   indicative. Run the crawler (`docs/CURATION.md`) or check by hand before trusting them.
9. **Teammate's simulated content:** Overview KPIs, the whole Commercial Finance page and the landing's $100k
   waterfall are demo data, labelled on screen (`apps/web/lib/uplo-demo-data.ts`).
10. **No logo files** yet: `components/Logo.tsx` is a text placeholder (`LOGO_FILES_PRESENT`).

---

## 7. Security notes (action needed)

- **Rotate these API keys.** During setup the user pasted a file of live keys for MatDAO's Render services into a chat
  session: Anthropic, Cohere, DeepSeek, Gemini/Google, OpenRouter, OpenAI, SerpAPI. They were never written to this
  repo, but they left the dashboards. Rotate them.
- **Remove `PRIVATE_KEY` from MatDAO's Vercel project env.** A frontend project must not hold a deployer key. Never put
  secrets in `NEXT_PUBLIC_*` variables: those ship to every browser.
- Repo hygiene: `.gitignore` and `.vercelignore` exclude every `.env*` except `.env.example`. No secret values are
  committed (checked with a pattern scan before each push in this session).
- `MockUSDC` has an open mint/faucet and must never be deployed to mainnet; `/setup` refuses non-testnet chains.
- The Fuji admin/attestor wallet `0xd5eC…a6a0` holds every admin role. It is a testnet key, but treat it as the
  project's identity.

---

## 8. Running it locally

```bash
# API
cd apps/api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8000          # memory store unless DATABASE_URL is set
.venv/bin/python -m pytest -q

# Local chain + contracts + demo projects (needs Foundry)
bash scripts/dev-chain.sh                                     # anvil :8545 (1 s blocks), deploy, export ABIs, seed

# Web
npm ci && NEXT_PUBLIC_CHAIN_ID=31337 NEXT_PUBLIC_RPC_URL=http://127.0.0.1:8545 npm run dev:web

# Full browser smoke test (API with INDEXER_ENABLED=true, web built for 31337)
python scripts/e2e/smoke.py --shots /tmp/shots

# Corpus tools
python -m app.curate --help                                   # crawler (docs/CURATION.md)
python3 apps/api/scripts/import_sheet.py <sheet.xlsx>         # team spreadsheet import (needs openpyxl)
```

Gotchas:
- Anvil without `--block-time` gives stale timestamps and breaks `SeedDemo` deadlines.
- `NEXT_PUBLIC_*` values are build-time.
- After changing contracts, run `forge build` and `node scripts/export-abis.mjs` (this also regenerates
  `apps/web/lib/bytecode.json`).

---

## 9. Research and audit material

In the repo:
- `docs/RESEARCH.md`: what was verified, with sources and licences, and what is recall.
- `docs/BUSINESS_MODEL.md`.
- `docs/uplo/business-model.md`: the team's original Thai draft.
- `docs/SHEET_IMPORT.md`, `docs/CURATION.md`.

**Sent to the user separately, not committed** (it describes a private MatDAO repo, and the raw research contains
unverified material): a zip with
- `audit/synthesis.md`: the MatDAO code audit. Headline finding: MatDAO's "patent corpus" is fabricated —
  `scripts/generate_patent_batch2.py` hand-writes records tagged as Google Patents data. Do not present MatDAO's
  IP/TRL outputs as evidence-based until that is replaced with real patent data.
- `audit/read_*.json`: per-area audit notes.
- `research/*.json|txt` and `research_workflow/*.json`: raw research outputs and adversarial fact-checks for each
  topic. Treat anything not marked verified as a lead, not a fact.

MatDAO's live Render services (`matdao-ip-engine`, `matdao-trl-services`) are a different API and are **not**
integrated. Pointing UPLO's web at them would break it. A future integration would need an adapter.

---

## 10. Suggested next steps (in priority order)

1. **Make the live site consistent.** Vercel env `NEXT_PUBLIC_CHAIN_ID=43113` and `NEXT_PUBLIC_RPC_URL` to the Fuji
   node, then `npx vercel deploy --prod` from `uplo-rebrand`. Check `/setup` says Avalanche Fuji and the sidebar shows
   no "(not deployed)".
2. **Fix open findings 1-3 in section 6**, and re-run the unreviewed parts of the review: spreadsheet rows, web merge,
   docs.
3. **Verify the corpus.** Run the crawler from a machine with normal internet. Start with the Thai funders and the 26
   flagged spreadsheet rows. Set `verified: true` only after a person checks the live page.
4. **Evidence engine against live sources.** Get a free OpenAlex key and EPO OPS credentials. Run the NMC811 example
   and calibrate on a few known patents. It has only been tested offline.
5. **Product direction.**
   - The user's stated target: any battery upcycler that needs money to scale crowdfunds through UPLO, and
     tokenisation is considered only later.
   - That is the milestone-raise flow, which works today.
   - Lead with it, not the invoice-financing story; see the `docs/BUSINESS_MODEL.md` cautions.
   - Before any real money: Thai legal opinions (receivables, investment-token rules, research-IP law B.E. 2564).
   - Also before real money: a decentralised or multi-party attestor, and a real stablecoin
     (Fuji test USDC `0x5425890298aed601595a70AB815c96711a31Bc65`; mainnet native USDC
     `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`).
6. **Optional:** set `ANTHROPIC_API_KEY` on Render for model-written explanations and form drafts. It is a paid API;
   without it, templates are used.
7. **Housekeeping:** add the logo files, delete the `wip/form-safety` branch, and rotate the keys from section 7.

---

## 11. Environment quirks met while building (for the next agent)

- The cloud build sandbox blocked funder sites, Render, Vercel, Supabase, the Fuji RPC and most external APIs.
  PyPI, npm and GitHub (via proxy) worked. Plan verification that needs the internet for a normal machine, or ask the
  user.
- `gh` had no valid token. Repo access went through the session's GitHub integration, and a remote branch delete was
  refused by the proxy.
- The teammate worked concurrently on `uplo-rebrand` through their own Claude sessions. Always `git fetch` and
  fast-forward or rebase before pushing, and never force-push shared branches.
- Session limits interrupted long multi-agent runs several times. Small, committed steps survived; long background
  runs did not.
