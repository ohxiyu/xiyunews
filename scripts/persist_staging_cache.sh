#!/usr/bin/env bash
# Update only cache blobs, preserving the remote branch tree and ancestry.
set -euo pipefail

if [ ! -f data/staging-items.json ]; then
  echo "No staging file to persist"
  exit 0
fi

cache_merge_helper="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/merge_pipeline_cache.py"
base=""
if git ls-remote --exit-code origin refs/heads/staging-cache >/dev/null; then
  git fetch --depth=1 origin refs/heads/staging-cache
  base=$(git rev-parse FETCH_HEAD)
  python3 "$cache_merge_helper" "$base"
else
  status=$?
  if [ "$status" -ne 2 ]; then
    echo "Cannot inspect staging-cache remote" >&2
    exit "$status"
  fi
fi

cache_index_dir=$(mktemp -d)
trap 'rm -f "$cache_index_dir/index"; rmdir "$cache_index_dir"' EXIT
export GIT_INDEX_FILE="$cache_index_dir/index"
if [ -n "$base" ]; then
  git read-tree "$base"
else
  git read-tree --empty
fi
for cache_path in data/staging-items.json data/analysis-cache.json data/qualified-cache.json; do
  if [ -f "$cache_path" ]; then
    blob=$(git hash-object -w -- "$cache_path")
    git update-index --add --cacheinfo "100644,$blob,$cache_path"
  fi
done
tree=$(git write-tree)
if [ -n "$base" ] && [ "$tree" = "$(git rev-parse "$base^{tree}")" ]; then
  echo "Staging cache unchanged"
  exit 0
fi

export GIT_AUTHOR_NAME="github-actions[bot]"
export GIT_AUTHOR_EMAIL="41898282+github-actions[bot]@users.noreply.github.com"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
if [ -n "$base" ]; then
  commit=$(git commit-tree "$tree" -p "$base" -m "chore: update staging cache")
else
  commit=$(git commit-tree "$tree" -m "chore: update staging cache")
fi
# A concurrent update must fail safely, never overwrite remote history.
git push origin "$commit:refs/heads/staging-cache"
