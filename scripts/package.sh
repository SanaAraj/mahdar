#!/bin/sh
# Package the tracked tree into mahdar.zip, refusing to leak secrets.
# Guard one: no tracked .env. Guard two: no gsk_ material anywhere tracked.
# Only after both pass does git archive run, so the zip is the exact tree.
set -eu

cd "$(dirname "$0")/.."

if [ -n "$(git ls-files -- .env)" ]; then
  echo "abort: a .env file is tracked; remove it from git before packaging" >&2
  exit 1
fi

if git grep -l -I -n "gsk_" -- . >/dev/null 2>&1; then
  echo "abort: gsk_ material found in the tracked tree; scrub it before packaging" >&2
  exit 1
fi

git archive -o mahdar.zip HEAD
echo "wrote mahdar.zip ($(wc -c < mahdar.zip | tr -d ' ') bytes)"
