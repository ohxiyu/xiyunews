#!/usr/bin/env bash
# Apply from a reviewed, transferred source directory. No application restarts.
set -euo pipefail
[[ "$(id -u)" == 0 ]] || { echo 'root required'; exit 1; }
source_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
python3 -m py_compile "$source_dir/disk_maintenance.py"
install -d -m 0755 /opt/xiyunews-disk-maintenance /etc/systemd/journald.conf.d
install -o root -g root -m 0755 "$source_dir/disk_maintenance.py" /opt/xiyunews-disk-maintenance/disk_maintenance.py
install -o root -g root -m 0644 "$source_dir/60-xiyunews-journal-cap.conf" /etc/systemd/journald.conf.d/60-xiyunews-journal-cap.conf
install -o root -g root -m 0644 "$source_dir/xiyunews-disk-maintenance.service" /etc/systemd/system/xiyunews-disk-maintenance.service
install -o root -g root -m 0644 "$source_dir/xiyunews-disk-maintenance.timer" /etc/systemd/system/xiyunews-disk-maintenance.timer
systemd-analyze verify /etc/systemd/system/xiyunews-disk-maintenance.service /etc/systemd/system/xiyunews-disk-maintenance.timer
systemctl daemon-reload
# Journald preserves service stream fds across its own restart. Do not restart
# Docker, containers, the Actions runner, realtime or any application.
systemctl restart systemd-journald.service
systemctl enable --now xiyunews-disk-maintenance.timer
echo 'Retention policy installed; explicit dry-run/apply remains separate.'
