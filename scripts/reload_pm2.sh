#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "${ROOT_DIR}/logs"

pm2 startOrReload "${ROOT_DIR}/ecosystem.config.js"
pm2 list
