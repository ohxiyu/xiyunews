#!/usr/bin/env bash
set -euo pipefail
[[ "$EUID" == 0 ]]
[[ -s /etc/xiyunews-backup-recipient.pub ]]
command -v age >/dev/null
backup_source=$(dirname "$0")
install -d -m 0700 /var/backups/xiyunews
install -d -m 0755 /opt/xiyunews-backup
install -d -m 0700 -o xiyunews-runner -g xiyunews-runner /home/xiyunews-runner/backup-export
install -m 0644 "$backup_source/backup.py" /opt/xiyunews-backup/backup.py
install -m 0644 "$backup_source/xiyunews-backup.service" "$backup_source/xiyunews-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now xiyunews-backup.timer
systemctl start xiyunews-backup.service
