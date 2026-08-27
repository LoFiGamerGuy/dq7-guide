#!/usr/bin/env python3
"""Show explicit party vocation mastery and remaining Master of All work."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from build_kb import DEFAULT_DB, ROOT

DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    members = state.get("party", {}).get("members", {})
    with sqlite3.connect(args.db) as connection:
        rows = connection.execute(
            """SELECT v.vocation_id, e.name, v.tier
            FROM vocations v JOIN entities e ON e.entity_id = v.vocation_id
            ORDER BY v.tier, e.name"""
        ).fetchall()
    mastered_by: dict[str, list[str]] = {}
    for character, member in members.items():
        for vocation_id, mastered in member.get("vocation_mastery", {}).items():
            if mastered is True:
                mastered_by.setdefault(vocation_id, []).append(character)
    mastered = [row for row in rows if row[0] in mastered_by]
    remaining = [row for row in rows if row[0] not in mastered_by]
    print(f"Master of All: {len(mastered)}/{len(rows)} vocations explicitly mastered")
    if mastered:
        print("Mastered: " + ", ".join(
            f"{name} ({'/'.join(mastered_by[vocation_id])})"
            for vocation_id, name, _tier in mastered
        ))
    print("Remaining: " + (", ".join(name for _id, name, _tier in remaining) or "none"))


if __name__ == "__main__":
    main()
