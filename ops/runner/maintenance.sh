#!/usr/bin/env bash
# Only runner diagnostics and the package manager's dedicated cache are eligible.
# Publication state, AI result caches, credentials and realtime data are excluded.
set -euo pipefail
mode="${1:---dry-run}"
[[ "$mode" == --dry-run || "$mode" == --apply ]] || exit 64
[[ "$(id -un)" == xiyunews-runner ]] || { echo "Use the dedicated runner user." >&2; exit 1; }
deployment_cleanup=/opt/xiyunews-job-hooks/deploy_temp_cleanup.py
if [[ -f "$deployment_cleanup" ]]; then
  python3 "$deployment_cleanup" --min-age-hours 24 "$mode"
fi
runner_diag=/opt/xiyunews-runner/_diag
if [[ -d "$runner_diag" ]]; then
  [[ ! -L "$runner_diag" && "$(stat -c %U "$runner_diag")" == xiyunews-runner ]]
  candidates=$(find -P "$runner_diag" -xdev -type f -user xiyunews-runner \
    \( -name 'Runner_*.log' -o -name 'Worker_*.log' \) -mtime +14 -printf '.' | wc -c)
  echo "Runner diagnostics older than 14 days: $candidates ($mode)"
  if [[ "$mode" == --apply ]]; then
    find -P "$runner_diag" -xdev -type f -user xiyunews-runner \
      \( -name 'Runner_*.log' -o -name 'Worker_*.log' \) -mtime +14 -delete
  fi
fi
runner_uv=/opt/hostedtoolcache/uv/0.11.32/x86_64/uv
runner_cache=/home/xiyunews-runner/.cache/uv
if [[ "$mode" == --apply && -x "$runner_uv" && -d "$runner_cache" ]]; then
  [[ ! -L "$runner_cache" && "$(stat -c %U "$runner_cache")" == xiyunews-runner ]]
  "$runner_uv" cache prune --cache-dir "$runner_cache"
fi
