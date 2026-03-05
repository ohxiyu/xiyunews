#!/usr/bin/env bash
set -euo pipefail

for app in qsh-openmolt qsh-crypto-monitor qsh-polymarket; do
  echo "=== ${app} ==="
  pm2 show "${app}" | sed -n '1,30p'
done

echo
echo "=== Recent Logs ==="
pm2 logs qsh-openmolt --lines 10 --nostream
pm2 logs qsh-crypto-monitor --lines 10 --nostream
pm2 logs qsh-polymarket --lines 10 --nostream
