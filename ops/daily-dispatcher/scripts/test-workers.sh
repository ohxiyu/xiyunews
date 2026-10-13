#!/usr/bin/env bash
set -euo pipefail
if [[ "${XIYUNEWS_SERIAL_TESTS:-0}" != 1 ]]; then
  exec ./node_modules/.bin/vitest run
fi
# A fresh process per file releases Vite/Workerd heaps between suites on the
# bounded runner. Run every file and preserve a failing exit status.
worker_tests=(tests/*.spec.ts)
[[ -f "${worker_tests[0]}" ]] || exit 1
for worker_test in "${worker_tests[@]}"; do
  ./node_modules/.bin/vitest run "$worker_test"
done
