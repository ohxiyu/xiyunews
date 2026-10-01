#!/usr/bin/env bash
# Run from the combined repository; stdout is the tar stream, never credentials.
set -euo pipefail
SOURCE_SHA=${1:?Usage: bash realtime/scripts/deploy/package_release.sh FULL_MAIN_SHA}
[[ $SOURCE_SHA =~ ^[0-9a-f]{40}$ ]] || { echo 'Require full SHA' >&2; exit 1; }
REPOSITORY_ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
git -C "$REPOSITORY_ROOT" merge-base --is-ancestor "$SOURCE_SHA" origin/main
git -C "$REPOSITORY_ROOT" cat-file -e "$SOURCE_SHA:realtime/requirements.lock"
git -C "$REPOSITORY_ROOT" archive "$SOURCE_SHA" realtime
