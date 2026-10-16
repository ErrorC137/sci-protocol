# UPLO hackathon infrastructure

Separate from MatDAO production. Nothing here touches `matdaoplatform-ops/MatDAO-Platform-V1`, its backend, or
the MatDAO Supabase project. **No secret values in this file, ever** - names and where they live only.

## Services

| What | Where | URL / id | Plan |
|---|---|---|---|
| Web (Next.js, `apps/web`) | Vercel, team **MatDAO** (`mat-dao`), project `sci-protocol` | production `https://sci-protocol.vercel.app` (live since 16 Oct 2026, deployed from `uplo-rebrand`) | Hobby |
| API (FastAPI, Docker) | Render, Blueprint `uplo-hackathon` → service `uplo-api` (region Singapore), deploys branch `uplo-rebrand` | `https://uplo-api.onrender.com` · health: `/health` | Free |
| Database (Postgres + pgvector) | Supabase org `MatDAO_V1`, project `uplo-hackathon` (Southeast Asia / Singapore), Data API **off** | ref `ldjsjtqvrlmeiwixrpfn` | Free |
| Contracts | Avalanche Fuji (43113); Base Sepolia (84532) still supported | **not deployed yet**: deploy from the browser at `/setup` ([GO_LIVE.md](GO_LIVE.md)) | testnet |
| Wallet connect | Reown (WalletConnect) team `matdao`, project `matdao` | project id is public (in `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID`) | Free |

GitHub: code is `ErrorC137/sci-protocol`, working branch `uplo-rebrand` (`matdaoplatform-ops` is a collaborator).
The Vercel project is also git-linked to a private copy `matdaoplatform-ops/sci-protocol` created by Vercel's
import flow; deploys go through the CLI from this repo instead, so that copy is unused.

## Environment variables (names only)

| Name | Lives in | Notes |
|---|---|---|
| `DATABASE_URL` | Render `uplo-api` · local `apps/api/.env.local` (gitignored) | Supabase **Session pooler**, port 5432 |
| `ANTHROPIC_API_KEY` | Render `uplo-api` | unset → template explanations, `/health` shows `llm.enabled: false` |
| `VOYAGE_API_KEY`, `PINATA_JWT` | Render `uplo-api` | optional, unset. Without Pinata, IPFS objects live in Postgres (`blobs`) |
| `RPC_URL` | `render.yaml` | `https://api.avax-test.network/ext/bc/C/rpc` (public Fuji node; the indexer refuses an RPC on another chain) |
| `DEPLOYMENT_JSON` | Render `uplo-api` | one line of JSON from `/setup`; overrides `contracts/deployments/<chainId>.json` |
| `CHAIN_ID`, `INDEXER_ENABLED`, `STARTUP_CONNECTORS` | `render.yaml` | `43113`, `true`, empty |
| `CORS_ORIGINS` | Render `uplo-api` | unset → `*`. Set to the Vercel production (+ preview) domain, comma-separated |
| `NEXT_PUBLIC_API_URL` | Vercel (Production + Preview) | `https://uplo-api.onrender.com` |
| `NEXT_PUBLIC_CHAIN_ID` | Vercel (Production + Preview) | `43113` |
| `NEXT_PUBLIC_RPC_URL` | Vercel (Production + Preview) | `https://api.avax-test.network/ext/bc/C/rpc` |
| `NEXT_PUBLIC_DEPLOYMENT_JSON` | Vercel (Production + Preview) | same JSON as `DEPLOYMENT_JSON`; rebuild after setting |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | Vercel (Production + Preview) | Reown project id |

`NEXT_PUBLIC_*` values are inlined at build time: redeploy the web app after changing them.

## Redeploying

- **API:** push to `uplo-rebrand` → Render auto-deploys (Blueprint-managed). Manual: Render → `uplo-api` → Manual Deploy.
  Every boot re-applies `supabase/migrations/*.sql` (idempotent) and upserts the curated corpus (stable ids), so edits to `data/seed/grants.yaml` show up after a deploy.
- **Web:** from the repo root, `npx vercel deploy` (preview) or `npx vercel deploy --prod` (production).
  Vercel settings: Root Directory `apps/web`, framework Next.js, Node 24.x. `.vercelignore` keeps the API, contracts and
  every `.env*` file out of the upload.
- **Contracts:** `docs/DEPLOY.md` §2, then `npm run export-abis`, commit `contracts/deployments/84532.json` +
  `packages/shared`, and redeploy both API and web.

## Free-plan caveats

- Render free sleeps after ~15 min idle; the first request then takes ~50 s. Open the site a few minutes before a
  pitch - the web app pings `/health` every 30 s while it's open, which keeps the API awake.
- Render free has no disk and no cron. Nothing is lost on restart (Postgres holds everything); the daily live-source
  ingest runs from `.github/workflows/ingest.yml` once a `DATABASE_URL` repo secret exists (needs repo admin).
- Supabase free pauses a project after ~7 days without activity; un-pause it from the dashboard.
