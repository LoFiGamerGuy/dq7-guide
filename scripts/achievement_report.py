#!/usr/bin/env python3
"""Report the sourced achievement ledger against explicit player state."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from build_kb import DEFAULT_DB, ROOT

DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"


def load_achievement_report(
    db_path: Path = DEFAULT_DB,
    state_path: Path = DEFAULT_STATE,
    include_unlocked: bool = False,
) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    unlocked = state.get("completion", {}).get("achievements_unlocked", [])
    if not isinstance(unlocked, list) or not all(isinstance(row, str) for row in unlocked):
        raise ValueError("completion.achievements_unlocked must be a list of strings")

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT a.*, r.target_type, r.target_key, r.required_count,
                s.title AS source_title, s.url AS source_url
            FROM achievements a JOIN sources s USING(source_id)
            LEFT JOIN achievement_requirements r USING(achievement_id)
            ORDER BY CASE a.grade
                WHEN 'bronze' THEN 1 WHEN 'silver' THEN 2
                WHEN 'gold' THEN 3 ELSE 4 END,
                a.category, a.name"""
        ).fetchall()
        known = {row["achievement_id"] for row in rows}
        unknown = sorted(set(unlocked) - known)
        result_rows = []
        for row in rows:
            item = dict(row)
            item["unlocked"] = item["achievement_id"] in unlocked
            progress = None
            completion = state.get("completion", {})
            if item["target_type"] == "mini_medal_registry":
                progress = completion.get("mini_medal_count")
                if progress is None:
                    found = completion.get("mini_medals_found", [])
                    progress = len(found) if isinstance(found, list) else None
            elif item["target_type"] == "item_registry":
                found = completion.get("items_obtained", [])
                progress = len(found) if isinstance(found, list) else None
            elif item["target_type"] == "checkpoint_obligation":
                done = completion.get("obligations_completed", [])
                progress = int(item["target_key"] in done) if isinstance(done, list) else None
            elif item["target_type"] == "achievement_registry":
                progress = len(set(unlocked) & known)
            item["progress"] = progress
            if include_unlocked or not item["unlocked"]:
                result_rows.append(item)
    return {
        "total": len(rows),
        "unlocked_count": len(set(unlocked) & known),
        "achievements": result_rows,
        "unknown_state_ids": unknown,
    }


def print_achievement_report(report: dict, sources: bool = False) -> None:
    print(f"Achievements: {report['unlocked_count']}/{report['total']} explicitly recorded")
    if report["unknown_state_ids"]:
        print("Unknown saved IDs: " + ", ".join(report["unknown_state_ids"]))
    for row in report["achievements"]:
        mark = "DONE" if row["unlocked"] else "TODO"
        gate = row["completion_checkpoint_id"] or row["earliest_checkpoint_id"] or "unknown gate"
        progress = ""
        if row["required_count"] is not None:
            current = "?" if row["progress"] is None else row["progress"]
            progress = f" [{current}/{row['required_count']}]"
        print(f"- [{mark}] {row['name']}{progress} — {row['description']} ({gate})")
        if sources:
            print(f"  Source: {row['source_title']} — {row['source_url']} — {row['locator']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Include recorded achievements")
    parser.add_argument("--sources", action="store_true")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    print_achievement_report(
        load_achievement_report(args.db, args.state, args.all), args.sources
    )


if __name__ == "__main__":
    main()
