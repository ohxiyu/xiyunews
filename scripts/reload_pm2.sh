#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "${ROOT_DIR}/logs"

# Remove services retired by the CoinSignal migration.
for retired_app in qsh-polymarket qsh-crypto-monitor; do
  pm2 delete "${retired_app}" >/dev/null 2>&1 || true
done

pm2 startOrReload "${ROOT_DIR}/ecosystem.config.js" --only coinsignal
pm2 save
pm2 show coinsignal
