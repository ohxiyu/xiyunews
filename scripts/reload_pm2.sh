#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# Refuse a double sender. Migration must explicitly stop the old service first.
if pm2 describe coinsignal >/dev/null 2>&1; then
  echo "Old coinsignal entry exists. Follow docs/deployment.md migration first." >&2
  exit 1
fi
mkdir -p "${ROOT_DIR}/logs"
pm2 startOrReload "${ROOT_DIR}/ecosystem.config.js" --only fomobtc
pm2 save
