# UPLO pitch readiness (Phase 5)

Status as of 16 Oct 2026. Infrastructure details: [INFRA.md](INFRA.md) · Fuji go-live clicks: [GO_LIVE.md](GO_LIVE.md) ·
pitch flow: [../../DEMO_SCRIPT.md](../../DEMO_SCRIPT.md).

## What's live

| Piece | URL | State |
|---|---|---|
| API (Render free, Singapore) | `https://uplo-api.onrender.com/health` | up: `store: postgres`, 150 programmes, chain 43113, `deployment: false`, LLM off (templates) |
| Web (Vercel `mat-dao/sci-protocol`) | `https://sci-protocol.vercel.app` | needs a fresh `npx vercel deploy` from `uplo-rebrand` to include Phases 4-5, then promote |
| Database | Supabase `uplo-hackathon` | up (free plan pauses after ~7 idle days) |
| Contracts | Avalanche Fuji | deployed 16 Oct 2026 (`contracts/deployments/43113.json`); attestor = the admin wallet `0xd5eC…a6a0` |

## Verified

- Web: `npm run build`, `typecheck` and `lint` pass.
- API: 63 tests pass (9 skipped: Postgres/anvil suites without their env vars).
- Contracts: 29 forge tests pass.
- **Full browser smoke test passes on a local chain** (`scripts/e2e/smoke.py`, anvil + API with indexer + production
  web build): profile → matches with explanations and unlocks → pre-filled application with export locked →
  funder contributes → evidence → approve → release → missed milestone → refund → new raise from the UI → vault
  seal/anchor/verify/decrypt. It was **not** run against the deployed URLs: that needs deployed Fuji contracts and
  funded wallets.
- The new pages render with real data on the local chain: `/validation` groups evidence → approval → release and
  the missed-deadline refund; `/overview` live tiles show raises, escrowed mUSDC, approvals and corpus size.

## What's demo or simulated (and labelled on screen)

- Overview top-row KPIs ($2.4M verified assets, $950K active financing, $38K innovation capital, 12 projects).
- The whole Commercial Finance page: invoice book (anonymised recyclers/buyers) and the waterfall calculator.
- The $100k waterfall on the landing page and in the calculator: "Illustrative example, not market rates".
- Membership prices: "Pricing under market test".
- Demo rows in Active Opportunities and the landing pipeline (Lithium Recovery Enhancement, Direct Cathode
  Regeneration, LFP Upcycling Process).

All of these live in `apps/web/lib/uplo-demo-data.ts`.

## Demo data changes

- `data/demo/project-a.json` → "Direct Cathode Regeneration pilot" (materials + energy; Battery materials,
  Recycling & circular materials, Energy storage; TRL 5).
- `data/demo/project-b.json` → "LFP Upcycling Process (failure-path demo)" (TRL 4).
- `data/demo/persona.json` ("Load demo researcher") → the same cathode-regeneration project, keywords
  "NMC cathode, relithiation, black mass". With the 150-programme corpus: 42 eligible, 108 excluded by hard rules;
  TED Fund, PMU-C and NRCT are among the matches.
- `contracts/script/SeedDemo.s.sol`: on-chain TRL and milestone titles match the battery projects (amounts and
  timing unchanged). Schema ids unchanged.

## Known issues

- Contracts aren't on Fuji yet, so every on-chain beat (raise, escrow, release, refund, validation records, live
  tiles) is empty on the deployed site until `/setup` runs.
- `/health` shows `indexer: null` on Render until a deployment exists; `/validation` then falls back to a notice.
- LLM explanations are off on Render (`ANTHROPIC_API_KEY` unset), so match explanations use templates.
- No official UPLO logo files yet: a plain-text placeholder is used (`components/Logo.tsx`, `TODO(logo)`).
- Render free sleeps after 15 idle minutes (~50 s cold start). Open the site a few minutes before presenting.

## Before the pitch (by hand)

1. **Fuji test AVAX** for 3 wallets (admin/attestor, researcher, funder): core.app → Tools → Testnet Faucet.
2. **Deploy contracts** at `https://<web>/setup` with the admin wallet (13 confirmations), then paste the JSON into
   Vercel `NEXT_PUBLIC_DEPLOYMENT_JSON` (rebuild) and Render `DEPLOYMENT_JSON` ([GO_LIVE.md](GO_LIVE.md) §3).
3. **Deploy the web app** from `uplo-rebrand`: `npx vercel deploy` (preview) → check → `npx vercel deploy --prod`.
4. **Three browser profiles** with one wallet each, all on Fuji.
5. **Seed ~25 minutes before** presenting via `/raise/new`, per DEMO_SCRIPT.md setup. The failure-path project needs a raise
   closing in ~5 minutes and milestone 1 due in ~20 minutes (the UI equivalent of `FAIL_DELAY`), funded in full
   before the raise closes.
6. Optional: set `ANTHROPIC_API_KEY` on Render for model-written match explanations; set `CORS_ORIGINS` to the
   Vercel domain(s).
7. Drop the logo PNGs into `apps/web/public/brand/` and flip `LOGO_FILES_PRESENT`.
8. Security housekeeping from GO_LIVE.md §5: rotate the API keys that were pasted into chat, and remove
   `PRIVATE_KEY` from the Vercel project's env.
