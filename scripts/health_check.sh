#!/usr/bin/env bash
set -euo pipefail
API_URL="${FOMOBTC_API_URL:-http://127.0.0.1:8080}"
curl --fail --silent --show-error "${API_URL}/api/health"
# Fails on missing credentials, degraded sources, startup or unavailable collectors.
curl --fail --silent --show-error "${API_URL}/api/ready"
