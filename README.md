# SCI Protocol

> Researchers describe their work once, in non-confidential terms, and get matched to every grant, accelerator and
> crowdfunding route they're eligible for, with the application paperwork pre-filled for them. Projects that
> traditional grants won't reach get on-chain, milestone-gated funding.

**Testnet only. No real value. Not a securities offering.** The milestone attestor is centralized; see
[Scope boundaries](#scope-boundaries).

> **UPLO hackathon deployment:** the user-facing brand is UPLO ([docs/uplo/](docs/uplo/)). To put it live on Avalanche
> Fuji, follow [docs/uplo/GO_LIVE.md](docs/uplo/GO_LIVE.md): contracts are deployed from a browser wallet at `/setup`,
> with no private key on any server.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  apps/web  Next.js 14 · Tailwind · wagmi + viem + RainbowKit       (Vercel)  │
│   /discover  /profile (wizard)  /matches  /apply/[id]  /evidence  /raise     │
│   /vault  - private keywords + vault crypto never leave the browser          │
└───────────────┬───────────────────────────────────────────┬──────────────────┘
                │ REST                                      │ JSON-RPC (wallet)
┌───────────────▼─────────────────────────────┐   ┌─────────▼──────────────────┐
│  apps/api  FastAPI (Render / Docker)        │   │  Avalanche Fuji C-Chain    │
│   ingest/   curated YAML + Grants.gov + EU  │   │   ProjectRegistry          │
│   curate/   funder-site watch → review YAML │   │   MilestoneEscrow          │
│   match/    hard filters → hybrid rank →    │   │   FundingPool              │
│             Claude explanations             │   │   SCIFraction (ERC-1155)   │
│   forms/    PDF / Word / HTML → map → review│   │   AttestationRegistry      │
│   evidence/ patents + papers → claim chart, │◄──┤   MockUSDC (testnet)       │
│             TRL from evidence, FTO flags    │   └────────────────────────────┘
│   chain/    IPFS pinning · event indexer    │
└───────┬───────────────┬─────────────────────┘   tools/portal-fill: Playwright helper
        │               │                         that types reviewed answers into a
┌───────▼───────┐ ┌─────▼──────────────────────────────┐  funder's web portal (never submits)
│ Postgres +    │ │ Anthropic (Claude) · Voyage embeds │
│ pgvector      │ │ Pinata IPFS · Fuji RPC · OpenAlex, │
│ (Supabase)    │ │ Crossref, S2, arXiv, EPO OPS, Lens │
└───────────────┘ │ all optional - local fallbacks     │
                  └────────────────────────────────────┘
```

## What's built, and how it was verified

| Brief tier | Feature | State | Verified in this build |
|---|---|---|---|
| T1 Aggregator | Canonical schema (`supabase/migrations/0001_init.sql`), pgvector + HNSW | done | API booted against Postgres 18 + pgvector (PGlite); SQL ↔ Python rule parity test |
| | Hand-curated corpus: **75 opportunities / 68 funders**, 25 open to Thai applicants | **drafted, unverified** | Loads with 0 errors. Every entry is `verified: false`. See [Before demo day](#before-demo-day) |
| | Grants.gov Search2 + EU Funding & Tenders connectors | done | Mapping tested against responses shaped like the published docs. **Live endpoints were not reachable from the build sandbox. Verify them live** |
| T1 Matching | Non-confidential intake wizard (controlled vocabulary only, privacy copy on screen) | done | Browser E2E |
| | Stage 1 hard filters (SQL prefilter + authoritative Python rules) | done | Unit tests + parity across 5 profiles |
| | Stage 2 hybrid ranker (0.45/0.20/0.15/0.10/0.10) | done | Tests; ranking inspected by hand |
| | Stage 3 Claude explanations, top 10 only, with template fallback | done | Real Anthropic SDK against a mock server (request shape, refusal fallback, injection). **Not run against the live API (no key here)** |
| | "What would unlock more funding" + near misses | added | Tests + E2E |
| | Private keywords: local re-rank in the browser, never sent | added | E2E |
| | Private vault (WebCrypto AES-GCM, key from wallet signature, keccak256 + CID anchored) | done | E2E: seal → anchor → verify → decrypt |
| T2 Forms | Fillable PDF (AcroForm), HTML form, flat PDF (layout heuristic → optional LLM, OCR if Tesseract) | done | 3 demo forms + an uploaded flat PDF |
| | Green / amber / red per field, narrative scaffolds with `[YOU MUST ADD: …]`, declarations never pre-ticked | done | Tests incl. a deliberately misbehaving LLM |
| | Mandatory, server-enforced review; export (filled PDF / .md pack / .json) only after it; **no submit endpoint** | done | Tests + E2E |
| T3 Chain | 5 contracts + MockUSDC (Foundry, OpenZeppelin 5) | done | **29 forge tests** incl. 5,000-run fuzz of refund conservation |
| | Deploy + demo-seeding scripts | done | Deployed and seeded on local anvil. **Avalanche Fuji deploy needs your key + faucet AVAX** ([docs/DEPLOY.md](docs/DEPLOY.md)); nothing is on Fuji yet |
| | Raise → escrow → evidence → approve → release; **missed milestone → refund** | done | Browser E2E against local chain ([scripts/e2e/smoke.py](scripts/e2e/smoke.py)) |
| | ERC-1155 fractions + pro-rata revenue distribution | done | forge tests (transfer-safe accounting) |
| **Pivot (battery upcycling, Avalanche)** | Avalanche Fuji default; C-Chain mainnet wired; Helicon-aware indexer (`finalized` head on 43113/43114); Routescan verification | done | Indexer test against local anvil; forge config parses. **Nothing deployed to Fuji yet** |
| | Word (.docx) forms: content controls, legacy fields, table cells, dotted blanks, ☐ glyphs; Thai mapping with `[ต้องเพิ่ม: …]` placeholders | done | Generated Thai demo form (30 fields): parse → map → review gate → filled .docx |
| | `tools/portal-fill`: types reviewed answers into a funder's web portal in a visible browser, never submits | done | 3 headless Chromium tests (declarations, dates, passwords, files, hidden steps untouched) |
| | Corpus automation `python -m app.curate`: watch list → polite crawl (robots.txt, 5 s/host) → extract → **quote-verified** values → review-queue YAML → `apply` (comments preserved) | done | 8 offline tests (mock sites, TIS-620 page, fabricated quotes dropped). **Live funder sites unreachable from the sandbox** |
| | Evidence engine `/evidence`: real patents + papers (OpenAlex, Crossref, S2, arXiv, EPO OPS, PatentsView, Lens, BigQuery export) → claim chart with verified quotes, priority-date filter, FTO flags, battery TRL from evidence, bundle hash | done | 10 tests; EPO parser on **real OPS XML**; UI driven in Chromium. **No source reachable from the sandbox, so adapters other than EPO are untested live: run `python -m app.evidence.smoke`** |
| | Business model review + unit-economics model; research notes; MatDAO audit | done | `tools/models/receivables_model.py`; [docs/BUSINESS_MODEL.md](docs/BUSINESS_MODEL.md); [docs/RESEARCH.md](docs/RESEARCH.md) |

Test totals: contracts 29 · API 49 (Postgres and indexer suites run when `PG_TEST_URL` / `ANVIL_RPC` are set) ·
portal-fill 3 · web typecheck + lint + production build · browser smoke test of the full demo story.

## Quickstart (local, everything on your machine)

Prereqs: Node 20+, Python 3.11+, [Foundry](https://getfoundry.sh).

```bash
npm install                                         # web + shared workspaces
(cd contracts && bash script/setup.sh && forge test)
(cd apps/api && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt)

# terminal 1 - API (memory store, local IPFS, template explanations; add keys from apps/api/.env.example)
CHAIN_ID=31337 RPC_URL=http://127.0.0.1:8545 INDEXER_ENABLED=true npm run dev:api

# terminal 2 - anvil + deploy + export ABIs + seed the two demo projects
FAIL_DELAY=600 npm run dev:chain

# terminal 3 - web
printf 'NEXT_PUBLIC_API_URL=http://localhost:8000\nNEXT_PUBLIC_CHAIN_ID=31337\nNEXT_PUBLIC_RPC_URL=http://127.0.0.1:8545\n' > apps/web/.env.local
npm run dev:web     # http://localhost:3000
```

`dev:chain` prints three anvil dev keys (attestor, researcher, funder). Import them into MetaMask with network
`http://127.0.0.1:8545`, chain id 31337. **Local only - these keys are public.** If you restart anvil, use
MetaMask → Settings → Advanced → *Clear activity tab data* to reset nonces.

Run everything the brief's demo needs in a browser, automatically: `python scripts/e2e/smoke.py` (see its docstring).

## How matching works (brief §4)

1. **Intake is non-confidential by construction.** The API rejects any sub-domain outside the controlled vocabulary
   (free text would be a disclosure channel). There is no description field. Optional keywords stay in
   `localStorage` and re-rank results in the browser (`apps/web/lib/keywords.ts`, +0.05 weight).
2. **Hard filters decide eligibility** (`apps/api/app/match/filters.py`): country, applicant type, TRL band,
   award overlap, deadline, incorporation, equity, IP assignment. Each rule is pass / fail / *unknown*; unknown
   never excludes but is shown as "verify". On Postgres the same rules run as a SQL prefilter (`ELIGIBLE_SQL`);
   Python is authoritative and a test checks they agree.
3. **Hybrid ranking** (`match/ranker.py`) with the brief's weights. Cosine is min-max normalised across the eligible
   set so the 0.45 weight stays discriminative whatever the embedder's absolute range.
4. **Explanations** (`match/explain.py`): one batched Claude call for the top 10, structured JSON output, told
   explicitly that eligibility is already decided. Refusals, timeouts or no key → deterministic template.
5. **Unlocks** (`match/service.py`): re-runs the hard filters on single-change variants of the profile ("Register a
   company → +12 opportunities", "Reach TRL 6 → +n"). This is the demo's pivot into the on-chain path.

Claude settings: model `claude-opus-5-5` (override with `SCI_LLM_MODEL`), effort `low` for explanations and
`medium` for form mapping, structured outputs, and server-side refusal fallback (`fallbacks: "default"`, beta
`server-side-fallback-2026-07-01`) enabled by default.

## How form automation works (brief §5)

`fetch → classify → parse → FieldSpec[] → map → review → export`, in `apps/api/app/forms/`.

- **Templates are cached per form URL** (extraction is the expensive step).
- **Deterministic first** (`mapper.py`): profile and contact fields → green. Converted currency, months-to-milestone
  or values capped at the grant's maximum → amber.
- **Then Claude** for what's left, as amber only. Post-conditions hold whatever the model says. Declarations,
  consents, signatures, dates and bank/ID numbers are never filled. Choice values must be one of the form's options.
  Narrative drafts always carry `[YOU MUST ADD: …]`. Any figure the model introduces that isn't in the profile is
  flagged. Contact details are never sent to the LLM.
- **Without a key**: narrative fields get scaffolds built only from profile facts plus placeholders.
- **Review is enforced server-side.** Export returns 403 until every amber field is checked, every placeholder is
  replaced, every empty red field is filled or explicitly left blank, and the applicant attests. Any edit re-opens
  review. There is no submit endpoint.
- The demo persona gets **88% of the 33-field Thai demo form pre-filled** (20 green, 9 amber, 4 red).

## Contracts (brief §6)

| Contract | Role |
|---|---|
| `ProjectRegistry` | Researcher, IPFS metadata CID, optional vault hash, TRL (attestor-gated), lifecycle status (module-gated) |
| `MilestoneEscrow` | **No progress, no money.** Milestones (CID, amount, deadline) set before any raise. Sequential evidence → attestor approve/reject → permissionless release to the researcher. `refundRemaining` when the current milestone's deadline passes without accepted or under-review evidence. Funders pull pro-rata refunds of everything unreleased. Also accepts direct sponsor deposits |
| `FundingPool` | All-or-nothing crowd raise in a stablecoin for the part of the budget not already deposited. Auto-finalises into escrow on target. Full withdrawal if the target is missed. Contributors claim fractions |
| `SCIFraction` | ERC-1155, id = projectId, 1 unit per USDC base unit contributed. Built-in pro-rata revenue distribution with transfer-safe accounting (buyers don't get past revenue) |
| `AttestationRegistry` | `anchor(hash, cid)`: anyone, first-come timestamp (vault). `attest(projectId, claimHash, cid)`: role-gated verification claims |
| `MockUSDC` | 6-decimal test stablecoin with an open faucet. **Testnet only** |

Wiring (roles, pool↔escrow) lives in one place, `contracts/script/Wiring.sol`, used by both the deploy script and
the tests. Deployed addresses: `contracts/deployments/<chainId>.json` (committed), mirrored into
`packages/shared/src/deployments.ts` by `npm run export-abis`.

| Network | Addresses |
|---|---|
| Avalanche Fuji (43113) | `contracts/deployments/43113.json` (deployed 16 Oct 2026 from `/setup`, start block 59543464): [ProjectRegistry](https://testnet.snowtrace.io/address/0x366Dc6DaA48E279A5D1333a3324Ee4e30260Ef51) · [MilestoneEscrow](https://testnet.snowtrace.io/address/0xF0487Cc97079Fc65464151fD16e2c88912787b43) · [FundingPool](https://testnet.snowtrace.io/address/0x30fa1DF6abBEb7a684126C8eE2Fe80d7BD560C1a) · [SCIFraction](https://testnet.snowtrace.io/address/0x469244e785e6D69b298a64bb841B1Da18966bD0D) · [AttestationRegistry](https://testnet.snowtrace.io/address/0x7F61DE1E77Fdd786AB63795332f855A7Db483000) · [MockUSDC](https://testnet.snowtrace.io/address/0xd66313481E6cFD9bc459a0571c87e38928e2BED5) |
| Local anvil (31337) | `contracts/deployments/31337.json` (deterministic dev addresses) |

## What's real vs. mocked

| Piece | Real | Mocked / fallback |
|---|---|---|
| Grant data | Grants.gov + EU connectors (live when reachable) | Curated corpus is **drafted, unverified** - see below |
| Embeddings | Voyage `voyage-3.5` (1024-d) with `VOYAGE_API_KEY` | Local feature-hashing embedder (1024-d) |
| LLM | Claude with `ANTHROPIC_API_KEY` | Deterministic templates |
| IPFS | Pinata with `PINATA_JWT` | Local store minting real CIDv1 (raw, sha2-256), labelled `pinned: "local"` |
| Stablecoin | - | `MockUSDC` with open faucet |
| Attestor | - | Deployer key (centralized). Decentralizing it is future work |
| Application forms | Any fillable PDF / HTML form you point `form_url` at or upload | The three demo forms are **generic replicas, labelled as such on the page and in the PDF**. Not any funder's official document |
| TRL scoring | Evidence-vs-TRL consistency check; battery TRL from quoted evidence (`app/evidence/trl.py`, rubric `battery-trl-0.1`, a proposal pending practitioner review) | KALDERA logic wasn't available to port |
| Prior art / literature | Live adapters for OpenAlex (key required since Feb 2026), Crossref, Semantic Scholar, arXiv, EPO OPS, PatentsView, Lens; local corpus from your own BigQuery export | **No patent data is bundled.** Test fixtures carry `XX-TEST` ids and are refused outside test mode (MatDAO's corpus was fabricated; see docs/RESEARCH.md) |
| Corpus watching | Crawler + extraction + verification run for real against any reachable site | Review queue only. Nothing is ever marked `verified: true` automatically |

## Before demo day

1. **Verify the corpus.** Open each `url` in `data/seed/grants.yaml`, correct amounts, bands, eligibility and cycles,
   set `verified: true` and `last_reviewed`. Add real `deadline:` dates (none were guessed, so countdowns only show
   once you add them). Thai entries matter most; you know these programs better than any model.
2. **Verify the live connectors**: `python -m app.ingest.run grants_gov eu_sedia` and check row counts.
3. **Swap in a real form** for at least one funder (`form_url: https://…pdf`), or use the in-app upload.
4. Deploy, seed and rehearse per [docs/DEPLOY.md](docs/DEPLOY.md) and [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

Not included: a UKRI connector (Gateway to Research lists awarded projects, not open calls). Also "Protocol Camp",
which the brief lists but which couldn't be identified confidently enough to curate.

## Scope boundaries

- **Testnet only. No real value. No mainnet deployment.**
- Tokenization is a **mechanism demonstration**, not a securities offering. Fractional claims on future revenue
  are very likely securities in most jurisdictions; a real deployment needs counsel.
- The attestor is centralized (the deployer key / backend signer). Named as future work, not hidden.
- A vault proof is a **timestamped existence proof**. It is not prior art, not patent protection, and not legal IP
  registration.
- Applications are never auto-submitted. A mis-submitted application is the applicant's liability. `tools/portal-fill`
  types into portals but never clicks submit or presses Enter, and never touches declarations, signatures, dates,
  bank/ID numbers, passwords or file uploads.
- The evidence engine produces **signals for a patent attorney, not legal opinions**. Absence of a match is not
  proof of novelty; FTO flags are not clearance. Confidential submissions only send your own public keywords to
  external search APIs.
- `SCIFraction` revenue rights make it securities-like: testnet demonstration only. See
  [docs/BUSINESS_MODEL.md §5](docs/BUSINESS_MODEL.md) for the recommended token design (no platform token).

## Repository layout

```
apps/web/            Next.js app (pages under app/, chain + API clients under lib/)
apps/api/            FastAPI: app/{ingest,curate,match,forms,evidence,score,chain,db,models,routers}, tests/, demo_forms/
tools/portal-fill/   Playwright helper for web-portal forms (never submits)
tools/models/        receivables_model.py - unit economics of the financing arm
data/curate/         sites.yaml (watch list), review/ (queues), state.json
.claude/agents/      9 domain subagents for Claude Code (see below)
contracts/           Foundry: src/ (5 + MockUSDC), test/, script/{Deploy,SeedDemo,Wiring}, deployments/
packages/shared/     ABIs + deployments (generated) and API types shared with the web app
data/seed/grants.yaml  curated corpus · data/demo/  demo persona + on-chain project metadata
supabase/migrations/   schema (also auto-applied by the API)
scripts/             dev-chain.sh, export-abis.mjs, e2e/smoke.py
docs/DEPLOY.md · docs/BUSINESS_MODEL.md · docs/RESEARCH.md · DEMO_SCRIPT.md · render.yaml
```

## Claude Code subagents (`.claude/agents/`)

Loaded automatically by Claude Code in this repo; invoke by name or let Claude delegate.

| Agent | Use it for |
|---|---|
| `fact-checker` | Adversarially verify any claim, figure or citation before it goes into a pitch or a filing |
| `rwa-structurer` | Receivables-pool design: tranching, waterfalls, true sale vs loan, permissioning |
| `battery-materials-scientist` | Recycling/upcycling chemistry, TRL rubric review, test plans |
| `ip-literature-analyst` | Prior art, claim charts and FTO signals from real patents and papers |
| `thai-regulatory-researcher` | SEC digital-asset rules, factoring/assignment law, Bayh-Dole, PDPA (always ends with lawyer questions) |
| `funding-corpus-curator` | Add or verify funders in `data/seed/grants.yaml` and the crawler watch list |
| `form-automation-engineer` | New PDF/Word/HTML form layouts, portal-fill selectors |
| `solidity-auditor` | Review contract changes before any deployment |
| `commercialization-strategist` | Membership offers, validation sprints, licensing terms |
