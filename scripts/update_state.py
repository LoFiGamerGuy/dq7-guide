#!/usr/bin/env python3
"""Update a value in the canonical player state JSON file."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"


def parse_value(value: str):
    """Parse common JSON scalar values while preserving ordinary text."""
    lowered = value.lower()
    if lowered == "null":
        return None
    if lowered in ("true", "false"):
        return lowered == "true"
    if value.startswith(("[", "{")):
        return json.loads(value)
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def set_path(obj: dict, dotted: str, value: str) -> None:
    parts = dotted.split(".")
    if not all(parts):
        raise ValueError("State path must contain non-empty dot-separated keys")
    cur = obj
    for p in parts[:-1]:
        if p not in cur:
            raise KeyError(f"Unknown state path component: {p}")
        if not isinstance(cur[p], dict):
            raise TypeError(f"State path component is not an object: {p}")
        cur = cur[p]
    leaf = parts[-1]
    if leaf not in cur:
        raise KeyError(f"Unknown state field: {dotted}")
    parsed = parse_value(value)
    current = cur[leaf]
    if current is not None:
        compatible = (
            isinstance(current, (int, float)) and not isinstance(current, bool)
            and isinstance(parsed, (int, float)) and not isinstance(parsed, bool)
        ) or type(current) is type(parsed)
        if not compatible:
            raise TypeError(
                f"Refusing to change type of {dotted} from "
                f"{type(current).__name__} to {type(parsed).__name__}"
            )
    cur[leaf] = parsed


def update_state(state_path: Path, dotted: str, value: str) -> None:
    data = json.loads(state_path.read_text(encoding="utf-8"))
    set_path(data, dotted, value)
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    state_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Dot-separated path, e.g. party.members.Hero.level")
    parser.add_argument("value", nargs="+", help="New scalar value")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help="Player-state JSON path")
    args = parser.parse_args()

    update_state(args.state, args.path, " ".join(args.value))
    print(f"Updated {args.path} in {args.state}")


if __name__ == "__main__":
    main()
