#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$script_dir"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10 or newer is required." >&2
  exit 1
fi

exec python3 scripts/guide_server.py --open-browser
