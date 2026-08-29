#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)

# Steam owns this foreground process, so stopping the shortcut stops LAN sharing.
exec "$repo_dir/manage-steam-deck-guide.sh" foreground
