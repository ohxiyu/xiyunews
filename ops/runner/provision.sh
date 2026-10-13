#!/usr/bin/env bash
# Installs only the isolated runner; never reads business credentials or starts
# fomobtc, a publication workflow, or the runner before repository enrollment.
set -euo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Run this reviewed installer as root." >&2; exit 1; }
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 && "$(uname -m)" == x86_64 ]]
systemctl is-active --quiet fomobtc
[[ "$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)" -ge 614400 ]]
[[ ! -e /opt/xiyunews-runner/.runner ]] || { echo "Already enrolled; refusing to replace runner credentials." >&2; exit 1; }
for runner_path in /opt/xiyunews-runner /opt/hostedtoolcache /home/runner; do
  if [[ -e "$runner_path" && "$(stat -c %U "$runner_path")" != xiyunews-runner ]]; then
    echo "Existing directory has a different owner: $runner_path" >&2; exit 1
  fi
done
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=l
apt-get update -qq
apt-get install -y --no-upgrade --no-install-recommends ca-certificates curl git jq unzip rsync \
  libicu74 libssl3t64 libyaml-0-2 libgmp10 libffi8 libreadline8t64 \
  zlib1g libbz2-1.0 libsqlite3-0 build-essential pkg-config libyaml-dev
if ! id xiyunews-runner >/dev/null 2>&1; then
  useradd --system --user-group --create-home --home-dir /home/xiyunews-runner \
    --shell /bin/bash xiyunews-runner
fi
[[ "$(id -Gn xiyunews-runner)" == xiyunews-runner ]]
install -d -m 0700 -o xiyunews-runner -g xiyunews-runner /home/xiyunews-runner /home/runner
install -d -m 0755 -o xiyunews-runner -g xiyunews-runner /opt/xiyunews-runner /opt/hostedtoolcache
runner_download=$(mktemp -d /var/tmp/xiyunews-runner-package.XXXXXX)
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  https://github.com/actions/runner/releases/download/v2.337.0/actions-runner-linux-x64-2.337.0.tar.gz \
  --output "$runner_download/runner.tar.gz"
printf '%s  %s\n' 70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613 \
  "$runner_download/runner.tar.gz" | sha256sum --check --status
tar -xzf "$runner_download/runner.tar.gz" -C /opt/xiyunews-runner --no-same-owner
chown -R xiyunews-runner:xiyunews-runner /opt/xiyunews-runner
install -m 0644 "$(dirname "$0")/xiyunews-runner.service" /etc/systemd/system/xiyunews-runner.service
systemctl daemon-reload
systemctl is-active --quiet fomobtc
echo "Isolated runner installed, not enrolled or started. Verified package retained at $runner_download."
