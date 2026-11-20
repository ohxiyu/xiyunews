#!/usr/bin/env bash
set -euo pipefail
exec timeout 90s /usr/bin/python3 /opt/xiyunews-job-hooks/job_hooks.py start
