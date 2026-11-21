#!/usr/bin/env bash
# Source and tar stream are supplied by the operator's reviewed main checkout.
set -euo pipefail
revision=${1:?full source revision required}
mode=${2:-activate}
[[ "$mode" == activate || "$mode" == check ]]
[[ "$EUID" == 0 && "$revision" =~ ^[a-f0-9]{40}$ ]]
base=/opt/fomobtc
releases="$base/releases"
unit=fomobtc.service
exec 9>/run/lock/xiyunews-realtime-release
flock -n 9
systemctl is-active --quiet "$unit"
test -L "$base/current"
previous=$(readlink -f "$base/current")
[[ "$previous" == "$releases/"* && -d "$previous" ]]

python3 - <<'PYSQL'
import sqlite3
with sqlite3.connect(
    "file:/var/lib/fomobtc/fomobtc.sqlite3?mode=ro", uri=True, timeout=3
) as database:
    if database.execute("PRAGMA quick_check").fetchone() != ("ok",):
        raise SystemExit("Realtime SQLite failed integrity check")
PYSQL

candidate=$(mktemp -d "$releases/$revision.XXXXXX")
next=$(mktemp -d "$base/.release.XXXXXX")
live=false
cleanup() {
    local result=$?
    if [[ "$live" == false && "$(readlink -f "$base/current")" != "$candidate" ]]; then
        rm -rf -- "$candidate"
    fi
    rm -rf -- "$next"
    exit "$result"
}
trap cleanup EXIT
chown fomobtc:fomobtc "$candidate"
runuser -u fomobtc -- tar --strip-components=1 --no-same-owner --no-same-permissions -xf - -C "$candidate"
test -f "$candidate/requirements.lock"
runuser -u fomobtc -- python3 -m venv "$candidate/venv"
runuser -u fomobtc -- "$candidate/venv/bin/python" -m pip install \
    --disable-pip-version-check --no-cache-dir --only-binary=:all: --no-deps --require-hashes \
    -r "$candidate/requirements.lock"
runuser -u fomobtc -- "$candidate/venv/bin/python" -m pip check
(
    cd "$candidate"
    runuser -u fomobtc -- "$candidate/venv/bin/python" -c 'from src.platform.app import Platform'
)
printf '%s\n' "$revision" > "$candidate/release.sha"
chown -hR root:fomobtc "$candidate"
chmod 0750 "$candidate"

if [[ "$mode" == check ]]; then
    printf 'xiyu.news realtime preflight passed for %s\n' "$revision"
    exit 0
fi

# Exactly one systemd unit owns the existing SQLite and Telegram session.
ln -s -- "$candidate" "$next/current"
mv -Tf -- "$next/current" "$base/current"
live=true
systemctl restart "$unit"

for ((attempt=0; attempt<20; attempt++)); do
    if health=$(curl -fsS --max-time 2 http://127.0.0.1:8080/api/health 2>/dev/null) &&
       python3 -c 'import json, sys; sys.exit(json.load(sys.stdin)["source_commit"] != sys.argv[1])' \
         "$revision" <<<"$health"; then
        printf 'xiyu.news realtime activated %s\n' "$revision"
        exit 0
    fi
    sleep 1
done
printf 'Realtime did not confirm revision %s. Previous release path: %s\n' "$revision" "$previous" >&2
exit 1
