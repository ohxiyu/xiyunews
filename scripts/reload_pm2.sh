#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "${ROOT_DIR}/logs"

pm2 delete qsh-openmolt >/dev/null 2>&1 || true
pm2 startOrReload "${ROOT_DIR}/ecosystem.config.js"
pm2 list
