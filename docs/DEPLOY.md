# Deploying SCI Protocol (Avalanche Fuji testnet)

Order matters: contracts first (the web app and API need the addresses), then the database, the API and the web app.
The whole path takes about an hour, most of it waiting on faucets and first builds. **Deploy on day one, not day three.**

## 0. Provision these first (brief §7)

Target: **Avalanche Fuji C-Chain (chain id 43113)** now, **Avalanche C-Chain mainnet (43114)** only after an external
audit and legal sign-off. Facts below were checked on 2026-10-15 from search results (the build sandbox could not
open the pages directly); re-check anything marked *verify* on the official page before relying on it.

| What | Where | Used by |
|---|---|---|
| 3 testnet wallets: deployer/attestor, researcher, funder | MetaMask or Core (fresh accounts, never your main one) | deploy, demo |
| Fuji AVAX in all three | Builder Hub faucet (build.avax.network → Console → Faucet; tops up a connected Builder Hub account). Fallback: core.app faucet with an Academy coupon code. Drip amounts differ by source: *verify* | gas. **Faucets are flaky, so do this first** |
| Fuji RPC URL | public `https://api.avax-test.network/ext/bc/C/rpc` (shared, no SLA) or a paid provider for the deployed API | deploy, web, API indexer |
| Test USDC *(optional)* | Circle faucet (faucet.circle.com): Fuji USDC `0x5425890298aed601595a70AB815c96711a31Bc65`, 10 USDC per 24 h per address (*verify*). Default deploy uses the repo's MockUSDC, which has an unlimited faucet - better for demos | funding demo |
| Contract verification | **no key needed**: Routescan (operator of snowtrace.io) is configured in `contracts/foundry.toml`. Etherscan's free tier reportedly stopped covering Avalanche in Nov 2025 | `--verify` |
| WalletConnect / Reown project id | cloud.reown.com | RainbowKit (without it, only browser wallets are offered) |
| Supabase project | supabase.com (free tier is enough) | Postgres + pgvector |
| Anthropic API key | console.anthropic.com | explanations, form mapping, corpus extraction, evidence judging |
| Evidence-engine keys *(optional, each source works alone)* | OpenAlex key (required since Feb 2026, metered), EPO OPS key+secret, Lens token, Semantic Scholar key, PatentsView key (issuance reported paused) | `/evidence` |
| Voyage API key *(optional)* | voyageai.com | better embeddings than the local fallback |
| Pinata JWT *(optional but recommended)* | pinata.cloud | public IPFS pinning (never pin plaintext research) |
| Render (or Fly.io) + Vercel accounts | | hosting |

**Helicon (C-Chain upgrade, mainnet 2026-09-22):** `latest` is now the last *executed* block and `finalized`/`safe`
the last *settled* block. The API indexer therefore follows `finalized` on chain ids 43113/43114 (override with
`INDEXER_HEAD_TAG`). The minimum gas price is now validator-governed: let Foundry/wallets estimate fees; never hardcode
a gas price.

## 1. Contracts: toolchain and tests

```bash
cd contracts
bash script/setup.sh        # npm i (OpenZeppelin) + forge install forge-std + forge build
forge test -vv              # 29 tests, including the refund-path fuzz test
```

`evm_version = "cancun"` is supported on the C-Chain since the Etna upgrade (Dec 2024). Blob transactions are not.

## 2. Deploy to Avalanche Fuji

```bash
cd contracts
export FUJI_RPC_URL="https://api.avax-test.network/ext/bc/C/rpc"
export PRIVATE_KEY=0x<deployer key>          # becomes admin AND attestor unless you set ATTESTOR=0x...
# optional: export USDC_ADDRESS=0x5425890298aed601595a70AB815c96711a31Bc65   # Circle test USDC instead of MockUSDC

forge script script/Deploy.s.sol --rpc-url fuji --broadcast --verify

node ../scripts/export-abis.mjs               # -> packages/shared/src/{abis,deployments}.ts + packages/shared/abis.json
git add deployments/43113.json ../packages/shared && git commit -m "Deploy to Avalanche Fuji"
```

Paste the addresses from `deployments/43113.json` into the README table and check them on
`https://testnet.snowtrace.io/address/<address>`. If `--verify` fails (explorer lag), re-run per contract:

```bash
forge verify-contract <address> src/ProjectRegistry.sol:ProjectRegistry --chain 43113 --verifier etherscan \
  --verifier-url https://api.routescan.io/v2/network/testnet/evm/43113/etherscan --etherscan-api-key verifyContract \
  --constructor-args $(cast abi-encode "constructor(address)" <deployer>) --watch
```

**Mainnet C-Chain (43114), later:** same commands with `--rpc-url avalanche` and `AVALANCHE_RPC_URL`, and set
`USDC_ADDRESS=0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` (Circle native USDC, *not* the bridged USDC.e). Do not do this
before: an external audit, a multisig + timelock on admin and attestor roles, and Thai legal advice on whatever the
pool shares are (see docs/RESEARCH.md). Circle can freeze USDC: terms and contracts must handle blocked repayments.

**Base Sepolia / BNB testnet instead:** `--rpc-url base_sepolia` / `bsc_testnet` with the matching RPC env var and an
Etherscan V2 key, then set chain id `84532` / `97` everywhere below.

## 3. Database (Supabase)

1. Create a project and note the database password.
2. Project Settings → Database → Connection string → **Session pooler** (IPv4, port 5432). That URL is `DATABASE_URL`.
3. Nothing else to run. On every boot the API applies `supabase/migrations/*.sql` in order (all idempotent:
   `0001_init.sql` enables `vector` and creates tables + the HNSW index, `0002_blobs.sql` the table that holds
   local-IPFS objects and uploaded forms) and loads the curated corpus if `grants` is empty. To refresh or add live sources:

```bash
cd apps/api && DATABASE_URL=... python -m app.ingest.run curated grants_gov eu_sedia
```

Re-running upserts on `(source, source_ref)`. It never duplicates. Schedule it with the Render cron in
`render.yaml` or `.github/workflows/ingest.yml`.

## 4. API (Render)

New → **Blueprint** → select the repo. `render.yaml` defines the web service (Docker, built from the repo root so
the corpus, migration, ABIs and deployments are included) and a daily ingest cron. Fill in:

| Env var | Value |
|---|---|
| `DATABASE_URL` | from step 3 |
| `ANTHROPIC_API_KEY` | your key (model defaults to `claude-opus-5-5`; override with `SCI_LLM_MODEL`) |
| `VOYAGE_API_KEY` | optional |
| `PINATA_JWT` | optional. Without it, IPFS objects are stored in Postgres and served by the API at `/ipfs/{cid}` (not public IPFS) |
| `CHAIN_ID` | `43113` (Avalanche Fuji; `84532` still works for Base Sepolia) |
| `RPC_URL` | Fuji RPC (the indexer uses it; public `https://api.avax-test.network/ext/bc/C/rpc` has no SLA) |
| `CORS_ORIGINS` | your Vercel URL (after step 5) |

`render.yaml` uses the **free** plan (no card needed). Free instances sleep after ~15 min idle and cold-start in
~50 s, which is a real risk mid-pitch: open the site a few minutes before you present, or switch `plan:` to
`starter`. Nothing is kept on the service's disk, so restarts lose no data (with `DATABASE_URL` set, drafts,
templates, IPFS objects and uploads all live in Postgres). Free has no cron jobs; the daily ingest runs from
`.github/workflows/ingest.yml` (add `DATABASE_URL` as a repo secret). Check `https://<api>/health`: you want `store: postgres`,
`llm.enabled: true`, `chain.deployment: true` and an `indexer` with events.

Fly.io alternative: `fly launch --dockerfile apps/api/Dockerfile` from the repo root, then `fly secrets set ...`.

## 5. Web (Vercel)

Import the repo. **Root Directory: `apps/web`**, framework Next.js (Vercel installs the npm workspaces from the repo
root). Environment variables:

```
NEXT_PUBLIC_API_URL=https://<your-render-api>
NEXT_PUBLIC_CHAIN_ID=43113
NEXT_PUBLIC_RPC_URL=https://api.avax-test.network/ext/bc/C/rpc
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=<reown id>
```

`NEXT_PUBLIC_*` values are inlined at build time, so redeploy after changing them or after re-exporting ABIs.

## 6. Seed the demo projects on testnet

The demo needs two on-chain projects: **A**, an open raise you fund live, and **B**, fully funded with a milestone
deadline that passes *during* your pitch (so you can show the refund).

```bash
API=https://<your-render-api>
CID_A=$(curl -s -X POST $API/ipfs/pin-json -H 'content-type: application/json' -d @data/demo/project-a.json | jq -r .cid)
CID_B=$(curl -s -X POST $API/ipfs/pin-json -H 'content-type: application/json' -d @data/demo/project-b.json | jq -r .cid)

cd contracts
RESEARCHER_KEY=0x<researcher> FUNDER_KEY=0x<funder> METADATA_CID_A=$CID_A METADATA_CID_B=$CID_B \
FAIL_DELAY=2400 forge script script/SeedDemo.s.sol --rpc-url fuji --broadcast
```

`FAIL_DELAY` is the number of seconds until project B's milestone is due. Run the script that long before the refund
moment in your pitch (2400 = 40 min). The script prints the exact deadline. Both wallets need a little Fuji
AVAX; the funder's mock USDC comes from the token's faucet.

## 7. Pre-flight checklist (morning of the demo)

- [ ] `/health`: postgres, LLM on, Pinata, deployment found, indexer has events
- [ ] `/raise` lists projects A and B; B's countdown matches your schedule
- [ ] All three wallets are on Avalanche Fuji with AVAX; the funder has mock USDC
- [ ] The attestor wallet sees *Approve / Reject* on a submitted milestone
- [ ] Run through [DEMO_SCRIPT.md](../DEMO_SCRIPT.md) twice on the **deployed** URL, on venue wifi
- [ ] Curated entries you'll show are `verified: true` (README "Before demo day")

## Local end-to-end (no accounts needed)

```bash
FAIL_DELAY=300 npm run dev:chain                                          # anvil + deploy + seed
CHAIN_ID=31337 RPC_URL=http://127.0.0.1:8545 INDEXER_ENABLED=true npm run dev:api
NEXT_PUBLIC_CHAIN_ID=31337 NEXT_PUBLIC_RPC_URL=http://127.0.0.1:8545 npm run build:web && npm start -w apps/web
pip install playwright && python scripts/e2e/smoke.py --shots /tmp/sci-shots   # drives the whole story in Chromium
```

Optional backend suites: `PG_TEST_URL=postgresql://…` (any Postgres with pgvector) and `ANVIL_RPC=http://127.0.0.1:8545`.
