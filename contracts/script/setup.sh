#!/usr/bin/env bash
# One-time contract toolchain setup: OpenZeppelin via npm, forge-std via forge install.
set -euo pipefail
cd "$(dirname "$0")/.."

npm install --no-audit --no-fund

if [ ! -f lib/forge-std/src/Test.sol ]; then
  mkdir -p lib
  forge install foundry-rs/forge-std --no-git 2>/dev/null \
    || forge install foundry-rs/forge-std --no-commit \
    || git clone --depth 1 https://github.com/foundry-rs/forge-std lib/forge-std
fi

forge build
echo "Contracts ready. Run: forge test -vv"
