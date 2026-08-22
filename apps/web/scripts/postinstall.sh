#!/usr/bin/env bash
set -euo pipefail

web_dir="$(cd "$(dirname "$0")/.." && pwd)"
root="$(cd "$web_dir/../.." && pwd)"
nm="$root/node_modules/.bun"

[ -d "$nm" ] || exit 0

for dir in "$nm"/nitro-nightly@*/node_modules; do
  [ -d "$dir" ] || continue
  if [ -d "$dir/nitro-nightly" ] || [ -e "$dir/nitro-nightly" ]; then
    if [ ! -e "$dir/nitro" ]; then
      ln -s "nitro-nightly" "$dir/nitro"
    fi
  fi
done
exit 0
