#!/usr/bin/env bash
set -euo pipefail

pm2 show coinsignal | sed -n '1,35p'
echo
echo "=== Recent CoinSignal logs ==="
pm2 logs coinsignal --lines 30 --nostream
