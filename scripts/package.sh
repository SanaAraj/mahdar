#!/bin/sh
# Package the tracked tree into mahdar.zip, refusing to leak secrets.
# Guard one: no tracked .env. Guard two: no gsk_ or generic sk- key material
# anywhere tracked; sk- is word-boundaried so ordinary words such as "task-"
# never trip it. This script is excluded from that search because it has to
# name the patterns it refuses. Only after both guards pass does git archive
# run, so the zip is the exact tracked tree.
set -eu

cd "$(dirname "$0")/.."

if [ -n "$(git ls-files -- .env)" ]; then
  echo "abort: a .env file is tracked; remove it from git before packaging" >&2
  exit 1
fi

if git grep -l -I -E 'gsk_|(^|[^A-Za-z0-9_])sk-' -- . ':!scripts/package.sh' >/dev/null 2>&1; then
  echo "abort: key material (gsk_ or sk-) found in the tracked tree; scrub it before packaging" >&2
  exit 1
fi

git archive -o mahdar.zip HEAD
echo "wrote mahdar.zip ($(wc -c < mahdar.zip | tr -d ' ') bytes)"
