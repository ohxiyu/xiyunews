#!/bin/bash
# ============================================================================
# SSOT Guard: Check for unauthorized external API access
# ============================================================================
#
# This script enforces the Single Source of Truth (SSOT) architecture
# by detecting any direct access to third-party prediction market APIs.
#
# ALL data MUST flow through Polyrouter API.
#
# Usage:
#   ./scripts/check_no_external_fetch.sh
#
# Exit codes:
#   0 - No violations found
#   1 - Violations detected
# ============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🔍 SSOT Guard: Checking for unauthorized external API access..."
echo "   Project: $PROJECT_ROOT"
echo ""

# Forbidden domains (direct API access not allowed)
FORBIDDEN_DOMAINS=(
    "gamma-api.polymarket.com"
    "data-api.polymarket.com"
    "clob.polymarket.com"
    "api.kalshi.com"
    "manifold.markets"
    "api.metaculus.com"
    "metaculus.com/api"
    "proxy.opinion.trade"
    "api.opinion.trade"
    "sx.bet"
)

# Files/directories to check (frontend and web API layer)
CHECK_PATHS=(
    "web/app"           # Frontend React components
    "web/lib"           # Frontend utilities
    "src/api"           # Backend API layer
)

# Files/directories that ARE allowed to have external access
ALLOWED_PATHS=(
    "src/services/api.py:PolyrouterAPI"    # Polyrouter is the ONLY allowed external
    "src/platforms"                          # Legacy adapters (to be deprecated)
    "src/services/opinion_api.py"           # Legacy (to be deprecated)
)

VIOLATIONS=0
VIOLATION_DETAILS=""

for domain in "${FORBIDDEN_DOMAINS[@]}"; do
    for check_path in "${CHECK_PATHS[@]}"; do
        if [ -d "$check_path" ] || [ -f "$check_path" ]; then
            # Search for the domain
            matches=$(grep -rn "$domain" "$check_path" 2>/dev/null || true)
            if [ -n "$matches" ]; then
                VIOLATIONS=$((VIOLATIONS + 1))
                VIOLATION_DETAILS="$VIOLATION_DETAILS\n❌ Found '$domain' in $check_path:\n$matches\n"
            fi
        fi
    done
done

echo "============================================"
if [ $VIOLATIONS -gt 0 ]; then
    echo "❌ SSOT VIOLATION DETECTED!"
    echo ""
    echo "The following files contain unauthorized direct API access:"
    echo -e "$VIOLATION_DETAILS"
    echo ""
    echo "FIX: All data MUST flow through PolyrouterAPI."
    echo "     Do NOT directly access third-party prediction market APIs."
    echo "============================================"
    exit 1
else
    echo "✅ SSOT Check Passed"
    echo ""
    echo "No unauthorized external API access detected in:"
    for path in "${CHECK_PATHS[@]}"; do
        echo "   - $path"
    done
    echo ""
    echo "All data flows through Polyrouter as expected."
    echo "============================================"
    exit 0
fi
