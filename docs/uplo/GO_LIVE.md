# Go live on Avalanche Fuji: checklist

The UPLO web app (Vercel), API (Render) and database (Supabase) exist already (see [INFRA.md](INFRA.md)).
This page lists what changes when moving from Base Sepolia to **Avalanche Fuji (43113)** and what someone with dashboard
access has to click. No secret values belong in this file.

Total time: about 30-45 minutes, most of it waiting for builds.

## 0. Code

Branch `uplo-rebrand` (Render deploys it) includes the Fuji switch, the `/setup` deploy page, Word/Thai forms,
the evidence engine (`/evidence`), the corpus crawler and the 75 programmes from the team spreadsheet
([SHEET_IMPORT.md](../SHEET_IMPORT.md)). Base Sepolia still works: set the chain ids back to `84532`.

## 1. Render (API, service `uplo-api`)

A push to `uplo-rebrand` redeploys automatically. `render.yaml` now sets these values itself:

| Variable | Value | Notes |
|---|---|---|
| `CHAIN_ID` | `43113` | from render.yaml |
| `RPC_URL` | `https://api.avax-test.network/ext/bc/C/rpc` | from render.yaml (public node, no SLA). The indexer refuses to run if `RPC_URL` serves a different chain than `CHAIN_ID`, and `/health` says so. |

If the Blueprint does not sync these values automatically, set them by hand in Render → `uplo-api` → Environment.
Check that the following are set in the dashboard (`sync: false`, so they stay there):

| Variable | Needed? | Value |
|---|---|---|
| `DATABASE_URL` | yes, for anything to survive a restart | Supabase → Connect → **Session pooler** URI (port 5432). The publishable/anon key is NOT this. |
| `CORS_ORIGINS` | recommended | `https://sci-protocol.vercel.app` plus any preview domain, comma-separated |
| `ANTHROPIC_API_KEY` | optional | Without it, explanations and form drafts use templates and the evidence engine uses lexical matching. It is a paid API. |
| `DEPLOYMENT_JSON` | after step 3 | the one line of JSON from `/setup` |
| `OPENALEX_API_KEY`, `S2_API_KEY`, `EPO_OPS_KEY`/`EPO_OPS_SECRET` | optional | free registrations that add sources to `/evidence`. Crossref, arXiv and Semantic Scholar (shared rate limit) work without keys. |

Check: `https://uplo-api.onrender.com/health` should show `"chain": {"chain_id": 43113, ...}` and `corpus_size` 150.
On the free plan the first request after 15 idle minutes takes about 50 s.

## 2. Vercel (web)

Settings → Environment Variables (Production and Preview):

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://uplo-api.onrender.com` |
| `NEXT_PUBLIC_CHAIN_ID` | `43113` |
| `NEXT_PUBLIC_RPC_URL` | `https://api.avax-test.network/ext/bc/C/rpc` |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | unchanged (public id) |
| `NEXT_PUBLIC_DEPLOYMENT_JSON` | after step 3 |

`NEXT_PUBLIC_*` values are baked in at build time, so **build again after changing them**. Per INFRA.md the project is
deployed with the CLI, so a dashboard "Redeploy" rebuilds the *last uploaded source*. To ship new code, run this from an
up-to-date checkout of `uplo-rebrand`:

    npx vercel deploy --prod

Alternatively, connect the project to `ErrorC137/sci-protocol` under Settings → Git so pushes build automatically.

Never put a private key, or any secret, in a `NEXT_PUBLIC_*` variable. They are shipped to every visitor's browser.
The web app needs no private key at all.

## 3. Contracts (once per testnet)

1. Put Fuji test AVAX in the wallet that will be admin. The Avalanche faucet is at core.app → Tools → Testnet Faucet.
   It may ask for a mainnet balance or a coupon code; we could not check the current rules from here. The 13
   transactions need well under 1 AVAX.
2. Open `https://<web>/setup`, connect that wallet and press **Deploy contracts**. Confirm 13 times. If anything
   fails, press **Continue**: progress is saved in the browser.
3. Copy the JSON line and paste it as `NEXT_PUBLIC_DEPLOYMENT_JSON` (Vercel, then build again) and `DEPLOYMENT_JSON`
   (Render restarts by itself).
4. Optional: commit it as `contracts/deployments/43113.json` and run `npm run export-abis`.

The deploying wallet becomes admin and, unless you enter another address, the attestor (it approves milestones).
Backers get test USDC from the mUSDC faucet button on a raise page; it is a mock token with an open faucet, testnet only.

## 4. Smoke test (5 minutes)

- `/discover` lists programmes. "Unverified" chips are expected, because nothing has been checked against funders' sites yet.
- `/profile` → `/matches` for a Thai battery-recycling startup at TRL 5 shows eligible programmes and the reasons.
- `/apply/<id>` → upload `apps/api/demo_forms/thai-research-proposal-demo.docx` → review → export `.docx`.
- `/evidence` opens with an example (NMC811 relithiation) → **Run evidence search**. Without keys only the keyless
  sources (Crossref, arXiv, Semantic Scholar) are searched, and the page shows which ones were and were not. These
  live sources were not reachable from the build sandbox, so only the offline fixtures have been tested end to end.
- `/raise/new` → create a raise → open it in a second browser profile → faucet → fund → submit evidence → approve as attestor.
- `/health`: `chain.deployment: true`, and the `indexer` shows no `error`.

## 5. Security housekeeping

- API keys were pasted into a chat while setting this up. **Rotate** every key in that paste: Anthropic, OpenAI, Gemini,
  DeepSeek, Cohere, OpenRouter and SerpAPI. Use the new values only in the Render dashboard.
- The MatDAO Vercel project has a `PRIVATE_KEY` variable. A deployer key does not belong in a frontend project's env;
  remove it there and keep deployer keys in a wallet.
