#!/usr/bin/env python3
"""Report completion obligations and medal access for a checkpoint."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"
DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"


def load_report(db_path: Path, state_path: Path, checkpoint_id: str | None = None) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    completion = state.get("completion", {})
    completed = completion.get("obligations_completed", [])
    found_medals = completion.get("mini_medals_found", [])
    if not isinstance(completed, list) or any(not isinstance(value, str) for value in completed):
        raise ValueError("completion.obligations_completed must be a list of strings")
    if not isinstance(found_medals, list) or any(
        not isinstance(value, int) or isinstance(value, bool) for value in found_medals
    ):
        raise ValueError("completion.mini_medals_found must be a list of integers")
    completed_ids = set(completed)
    found_numbers = set(found_medals)
    selected = checkpoint_id or state["story"]["checkpoint_id"]
    if not selected:
        raise ValueError(
            "Checkpoint is unknown. Pass --checkpoint or update story.checkpoint_id "
            "from Ryan's report."
        )

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        checkpoint = connection.execute(
            "SELECT * FROM checkpoints WHERE checkpoint_id = ?", (selected,)
        ).fetchone()
        if checkpoint is None:
            raise ValueError(f"Unknown checkpoint: {selected}")

        obligations = connection.execute(
            """SELECT o.*, s.title AS source_title, s.url AS source_url
            FROM checkpoint_obligations o
            JOIN sources s ON s.source_id = o.source_id
            WHERE o.checkpoint_id = ?
            ORDER BY o.stop_before_advancing DESC, o.required_for_100_percent DESC,
                     o.obligation_id""",
            (selected,),
        ).fetchall()
        medals = connection.execute(
            """SELECT m.*, s.title AS source_title, s.url AS source_url
            FROM mini_medal_locations m
            JOIN sources s ON s.source_id = m.source_id
            WHERE m.checkpoint_id = ?
            ORDER BY m.medal_number""",
            (selected,),
        ).fetchall()
        return {
            "player_checkpoint_matches": state["story"]["checkpoint_id"] == selected,
            "checkpoint": dict(checkpoint),
            "obligations": [dict(row) for row in obligations
                            if row["obligation_id"] not in completed_ids],
            "medals": [dict(row) for row in medals
                       if row["medal_number"] not in found_numbers],
            "completed_hidden_count": sum(
                row["obligation_id"] in completed_ids for row in obligations
            ),
            "found_medals_hidden_count": sum(
                row["medal_number"] in found_numbers for row in medals
            ),
        }
    finally:
        connection.close()


def print_report(report: dict) -> None:
    checkpoint = report["checkpoint"]
    stops = [row for row in report["obligations"] if row["stop_before_advancing"]]
    print(f"Checkpoint: {checkpoint['name']} ({checkpoint['checkpoint_id']})")
    if not report["player_checkpoint_matches"]:
        print("Player-state note: report checkpoint was supplied explicitly; Ryan's saved checkpoint differs or is unknown.")
    if stops:
        print("STOP WARNING:")
        for row in stops:
            print(f"- {row['action']}")
            if row["unavailable_after"]:
                print(f"  Unavailable after: {row['unavailable_after']}")
            print(f"  Source: {row['source_title']} — {row['source_url']} ({row['locator']})")
    else:
        print("Stop warning: no verified stop-before-advancing obligation is recorded for this checkpoint.")

    print("Immediate completion actions:")
    actions = [row for row in report["obligations"] if not row["stop_before_advancing"]]
    if not actions:
        print("- No normalized obligations yet; this is a coverage gap, not a safe-to-advance guarantee.")
    for row in actions:
        marker = "required" if row["required_for_100_percent"] else "optional"
        print(f"- [{marker}] {row['action']}")
        print(f"  Source: {row['source_title']} — {row['source_url']} ({row['locator']})")

    print("Mini Medals assigned to this checkpoint/region:")
    if not report["medals"]:
        print("- None normalized yet.")
    for row in report["medals"]:
        gate = row["available_from"] or "normal access"
        print(f"- #{row['medal_number']}: {row['location']} ({row['time_period']}) — {row['detail']} [from: {gate}]")
        print(f"  Source: {row['source_title']} — {row['source_url']} ({row['locator']})")

    print(f"Safe advancement condition: {checkpoint['safe_exit_condition']}")
    print("Coverage status: " + checkpoint["coverage_status"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", help="Checkpoint ID; defaults to Ryan's saved checkpoint")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    try:
        print_report(load_report(args.db, args.state, args.checkpoint))
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
