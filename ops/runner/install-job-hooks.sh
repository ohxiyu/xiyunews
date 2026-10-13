#!/usr/bin/env bash
set -euo pipefail
[[ "$EUID" == 0 ]]
[[ ! -e /var/lib/xiyunews-runtime/paused ]] || { echo 'Already paused; preserve operator control.' >&2; exit 1; }
hook_source=$(dirname "$0")
install -d -m 0755 /opt/xiyunews-job-hooks
install -m 0644 "$hook_source/job_hooks.py" /opt/xiyunews-job-hooks/job_hooks.py
install -m 0755 "$hook_source/job-start.sh" "$hook_source/job-complete.sh" /opt/xiyunews-job-hooks/
install -d -m 0700 -o xiyunews-runner -g xiyunews-runner /home/xiyunews-runner/state
# Never restart a live job. The integrator first waits for the known queue.
for job_pid in $(cat /sys/fs/cgroup/system.slice/xiyunews-runner.service/cgroup.procs); do
  if [[ "$(cat "/proc/$job_pid/comm" 2>/dev/null || true)" == Runner.Worker ]]; then
    echo 'Runner busy; hooks staged but not activated.' >&2; exit 3
  fi
done
touch /var/lib/xiyunews-runtime/paused
trap 'systemctl start xiyunews-runner.service; rm -f /var/lib/xiyunews-runtime/paused' EXIT
systemctl stop xiyunews-runner.service
install -d -m 0755 /etc/systemd/system/xiyunews-runner.service.d
install -m 0644 "$hook_source/20-job-hooks.conf" /etc/systemd/system/xiyunews-runner.service.d/
systemctl daemon-reload
systemctl start xiyunews-runner.service
systemctl is-active --quiet xiyunews-runner.service
echo 'Job hooks activated; business service was not restarted.'
