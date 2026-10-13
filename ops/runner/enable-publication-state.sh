#!/usr/bin/env bash
set -euo pipefail
[[ "$EUID" == 0 ]]
[[ ! -e /var/lib/xiyunews-runtime/paused ]]
state_source=$(dirname "$0")
[[ -s /home/xiyunews-runner/state/publication.sqlite3 ]]
for job_pid in $(cat /sys/fs/cgroup/system.slice/xiyunews-runner.service/cgroup.procs); do
  if [[ "$(cat "/proc/$job_pid/comm" 2>/dev/null || true)" == Runner.Worker ]]; then
    echo 'Runner busy; no runtime change.' >&2; exit 3
  fi
done
touch /var/lib/xiyunews-runtime/paused
trap 'systemctl start xiyunews-runner.service; rm -f /var/lib/xiyunews-runtime/paused' EXIT
systemctl stop xiyunews-runner.service
install -m 0644 "$state_source/30-publication-state.conf" /etc/systemd/system/xiyunews-runner.service.d/
systemctl daemon-reload
systemctl start xiyunews-runner.service
systemctl is-active --quiet xiyunews-runner.service
echo 'Independent publication SQLite enabled for trusted producers only.'
