#!/usr/bin/env bash
# Tool dependencies only. CI and main publication never share a cache path.
set -euo pipefail
role="${1:?ci or producer required}"
[[ "$role" == ci || "$role" == producer ]] || exit 64
[[ -f Gemfile.lock && ! -L Gemfile.lock ]]
cache_root="${XIYUNEWS_BUNDLE_CACHE_ROOT:-/home/xiyunews-runner/.cache/xiyunews-bundle}"
lock_hash=$(ruby -rdigest -e 'print Digest::SHA256.file("Gemfile.lock").hexdigest')
[[ "$lock_hash" =~ ^[a-f0-9]{64}$ ]]
cache="$cache_root/$role/ruby-3.3/$lock_hash"
umask 077
mkdir -p "$cache/cache" "$cache/installed"
bundle config set --local path "$cache/installed"
bundle config set --local cache_path "$cache/cache"
bundle config set --local deployment true
# A prewarmed, lock-verified archive can install without the network. Otherwise
# retain normal frozen installation; never update or rewrite dependency locks.
bundle check || bundle install --local || bundle install --jobs 1
