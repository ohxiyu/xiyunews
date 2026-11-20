#!/usr/bin/env bash
set -euo pipefail
[[ "$EUID" == 0 ]]
mode="${1:---install}"
[[ "$mode" == --install || "$mode" == --refresh-scripts ]] || exit 64
[[ ! -e /var/lib/xiyunews-runtime/paused ]] || { echo 'Already paused; preserve operator control.' >&2; exit 1; }
hook_source=$(cd "$(dirname "$0")" && pwd)
# Refresh reviewed scripts without restarting a busy runner or changing its
# installed environment. Replace each script atomically, helper before caller.
refresh_scripts() {
  install -d -m 0755 /opt/xiyunews-job-hooks
  local file permissions temporary
  for file in deploy_temp_cleanup.py job_hooks.py job-start.sh job-complete.sh maintenance.sh; do
    permissions=0755
    [[ "$file" != *.py ]] || permissions=0644
    temporary=$(mktemp /opt/xiyunews-job-hooks/.refresh.XXXXXXXX)
    install -m "$permissions" "$hook_source/$file" "$temporary"
    mv -f "$temporary" "/opt/xiyunews-job-hooks/$file"
  done
  temporary=$(mktemp /opt/.xiyunews-maintenance.XXXXXXXX)
  install -m 0755 "$hook_source/maintenance.sh" "$temporary"
  mv -f "$temporary" /opt/xiyunews-runner-maintenance.sh
}
if [[ "$mode" == --refresh-scripts ]]; then
  cmp -s "$hook_source/20-job-hooks.conf" /etc/systemd/system/xiyunews-runner.service.d/20-job-hooks.conf
  refresh_scripts
  echo 'Reviewed scripts refreshed; runner environment and active job unchanged.'
  exit 0
fi
install -d -m 0755 /opt/xiyunews-job-hooks
install -d -m 0700 -o xiyunews-runner -g xiyunews-runner /home/xiyunews-runner/state
# Never restart a live job. The integrator first waits for the known queue.
for job_pid in $(cat /sys/fs/cgroup/system.slice/xiyunews-runner.service/cgroup.procs); do
  if [[ "$(cat "/proc/$job_pid/comm" 2>/dev/null || true)" == Runner.Worker ]]; then
    echo 'Runner busy; nothing activated.' >&2; exit 3
  fi
done
touch /var/lib/xiyunews-runtime/paused
trap 'systemctl start xiyunews-runner.service; rm -f /var/lib/xiyunews-runtime/paused' EXIT
systemctl stop xiyunews-runner.service
refresh_scripts
install -d -m 0755 /etc/systemd/system/xiyunews-runner.service.d
install -m 0644 "$hook_source/20-job-hooks.conf" /etc/systemd/system/xiyunews-runner.service.d/
systemctl daemon-reload
systemctl start xiyunews-runner.service
systemctl is-active --quiet xiyunews-runner.service
echo 'Job hooks activated; business service was not restarted.'
