#!/usr/bin/env python3
"""Report Heroic Hoarder identity, route, and explicit player progress coverage."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from build_kb import DEFAULT_DB, ROOT

DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"


def load_hoarder_report(
    db_path: Path = DEFAULT_DB,
    state_path: Path = DEFAULT_STATE,
    gaps_only: bool = False,
) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    obtained = state.get("completion", {}).get("items_obtained", [])
    if not isinstance(obtained, list) or any(not isinstance(value, str) for value in obtained):
        raise ValueError("completion.items_obtained must be a list of item IDs")
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT i.item_id, i.name, i.heroic_hoarder_ordinal,
                i.verification_status, c.name AS category,
                COUNT(a.acquisition_id) AS route_count
            FROM items i JOIN item_categories c USING(category_id)
            LEFT JOIN item_acquisition_paths a USING(item_id)
            WHERE i.heroic_hoarder_required = 1
            GROUP BY i.item_id
            ORDER BY c.heroic_hoarder_order, i.heroic_hoarder_ordinal"""
        ).fetchall()
    known = {row["item_id"] for row in rows}
    result = []
    for row in rows:
        item = dict(row)
        item["obtained"] = item["item_id"] in obtained
        if not item["obtained"] and (not gaps_only or item["route_count"] == 0):
            result.append(item)
    return {
        "total": len(rows),
        "obtained_count": len(set(obtained) & known),
        "routed_count": sum(row["route_count"] > 0 for row in rows),
        "items": result,
        "unknown_state_ids": sorted(set(obtained) - known),
    }


def print_hoarder_report(report: dict, gaps_only: bool = False) -> None:
    print(
        f"Heroic Hoarder: {report['obtained_count']}/{report['total']} explicitly obtained; "
        f"{report['routed_count']}/{report['total']} have sourced routes"
    )
    if report["unknown_state_ids"]:
        print("Unknown saved item IDs: " + ", ".join(report["unknown_state_ids"]))
    if gaps_only:
        print(f"Unresolved route gaps: {len(report['items'])}")
    for row in report["items"]:
        route = f"{row['route_count']} route(s)" if row["route_count"] else "ROUTE UNKNOWN"
        print(f"- {row['category']} #{row['heroic_hoarder_ordinal']}: {row['name']} — {route}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gaps", action="store_true", help="Show only unresolved routes")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    report = load_hoarder_report(args.db, args.state, args.gaps)
    print_hoarder_report(report, args.gaps)


if __name__ == "__main__":
    main()
