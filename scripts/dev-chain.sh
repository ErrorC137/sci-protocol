#!/usr/bin/env bash
# Local end-to-end chain: starts anvil, deploys all contracts, exports ABIs, seeds the demo projects.
# Uses anvil's well-known dev mnemonic: account 0 = deployer/attestor, 1 = researcher, 2 = funder.
# NEVER use these keys anywhere but a local chain.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RPC=http://127.0.0.1:8545
M="test test test test test test test test test test test junk"
key() { cast wallet private-key --mnemonic "$M" --mnemonic-index "$1"; }

if ! cast chain-id --rpc-url $RPC >/dev/null 2>&1; then
  echo "Starting anvil on :8545"
  anvil --silent --port 8545 --block-time 1 &  # real-time blocks so deadlines pass like on a testnet
  for _ in $(seq 1 30); do cast chain-id --rpc-url $RPC >/dev/null 2>&1 && break; sleep 0.5; done
fi

cd "$ROOT/contracts"
PRIVATE_KEY=$(key 0) forge script script/Deploy.s.sol --rpc-url $RPC --broadcast ${FORGE_FLAGS:-}
node "$ROOT/scripts/export-abis.mjs"

PIN_A=${METADATA_CID_A:-} PIN_B=${METADATA_CID_B:-}
API=${API_URL:-http://127.0.0.1:8000}
if [ -z "$PIN_A" ] && curl -sf "$API/health" >/dev/null 2>&1; then
  PIN_A=$(curl -sf -X POST "$API/ipfs/pin-json" -H 'content-type: application/json' \
    -d @"$ROOT/data/demo/project-a.json" | python3 -c 'import sys,json;print(json.load(sys.stdin)["cid"])')
  PIN_B=$(curl -sf -X POST "$API/ipfs/pin-json" -H 'content-type: application/json' \
    -d @"$ROOT/data/demo/project-b.json" | python3 -c 'import sys,json;print(json.load(sys.stdin)["cid"])')
fi

RESEARCHER_KEY=$(key 1) FUNDER_KEY=$(key 2) METADATA_CID_A=${PIN_A:-demo-metadata-a} METADATA_CID_B=${PIN_B:-demo-metadata-b} \
  FAIL_DELAY=${FAIL_DELAY:-600} forge script script/SeedDemo.s.sol --rpc-url $RPC --broadcast ${FORGE_FLAGS:-}

cat <<EOF

Local chain ready (chainId 31337). Import these into MetaMask (local only!):
  attestor   $(key 0)
  researcher $(key 1)
  funder     $(key 2)
EOF
