#!/usr/bin/env python3
"""Print a conservative, ordered early-game completion checklist."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"
DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"
DEFAULT_FROM = "cp_001_prologue"
DEFAULT_THROUGH = "cp_009_alltrades"


def _checkpoint(connection: sqlite3.Connection, checkpoint_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown checkpoint: {checkpoint_id}")
    return row


def load_walkthrough(
    db_path: Path,
    state_path: Path,
    from_checkpoint: str = DEFAULT_FROM,
    through_checkpoint: str = DEFAULT_THROUGH,
) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    found = state.get("completion", {}).get("mini_medals_found", [])
    if not isinstance(found, list) or any(
        not isinstance(number, int) or isinstance(number, bool) for number in found
    ):
        raise ValueError("completion.mini_medals_found must be a list of integers")
    found_numbers = set(found)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        start = _checkpoint(connection, from_checkpoint)
        end = _checkpoint(connection, through_checkpoint)
        if start["sequence_no"] > end["sequence_no"]:
            raise ValueError("The starting checkpoint must not follow the ending checkpoint")
        checkpoints = connection.execute(
            """SELECT * FROM checkpoints
            WHERE sequence_no BETWEEN ? AND ? ORDER BY sequence_no""",
            (start["sequence_no"], end["sequence_no"]),
        ).fetchall()
        blocks = []
        for checkpoint in checkpoints:
            sequence_no = checkpoint["sequence_no"]
            obligations = connection.execute(
                """SELECT o.*, s.title AS source_title, s.url AS source_url
                FROM checkpoint_obligations o JOIN sources s USING(source_id)
                WHERE o.checkpoint_id = ?
                ORDER BY o.stop_before_advancing DESC,
                         o.rowid""",
                (checkpoint["checkpoint_id"],),
            ).fetchall()
            medals = connection.execute(
                """SELECT m.*, loc.sequence_no AS location_sequence,
                    avail.sequence_no AS available_sequence,
                    avail.name AS available_checkpoint,
                    s.title AS source_title, s.url AS source_url
                FROM mini_medal_locations m
                JOIN checkpoints loc ON loc.checkpoint_id = m.checkpoint_id
                JOIN checkpoints avail
                  ON avail.checkpoint_id = m.available_checkpoint_id
                JOIN sources s USING(source_id)
                WHERE (loc.sequence_no = ? OR
                       (loc.sequence_no < ? AND avail.sequence_no = ?))
                  AND m.medal_number NOT IN (
                      SELECT value FROM json_each(?)
                  )
                ORDER BY m.medal_number""",
                (sequence_no, sequence_no, sequence_no, json.dumps(sorted(found_numbers))),
            ).fetchall()
            guidance = connection.execute(
                """SELECT d.*, s.title AS source_title, s.url AS source_url
                FROM documents d LEFT JOIN sources s USING(source_id)
                WHERE d.checkpoint_key = ?
                  AND d.domain IN ('equipment', 'vocations')
                ORDER BY d.domain, d.document_id""",
                (checkpoint["checkpoint_id"],),
            ).fetchall()
            advice = connection.execute(
                """SELECT a.*, s.title AS source_title, s.url AS source_url
                FROM checkpoint_advice a JOIN sources s USING(source_id)
                WHERE a.checkpoint_id = ? AND a.ready_for_play = 1
                ORDER BY CASE a.advice_type
                    WHEN 'gear' THEN 1 WHEN 'boss' THEN 2
                    WHEN 'grind' THEN 3 WHEN 'vocation' THEN 4 END,
                    a.display_order""",
                (checkpoint["checkpoint_id"],),
            ).fetchall()
            blocks.append(
                {
                    "checkpoint": dict(checkpoint),
                    "stops": [dict(row) for row in obligations if row["stop_before_advancing"]],
                    "now": [dict(row) for row in obligations if not row["stop_before_advancing"]],
                    "medals_now": [
                        dict(row) for row in medals
                        if row["location_sequence"] == sequence_no
                        and row["available_sequence"] <= sequence_no
                    ],
                    "medals_backtrack": [
                        dict(row) for row in medals
                        if row["location_sequence"] < sequence_no
                    ],
                    "medals_later": [
                        dict(row) for row in medals
                        if row["location_sequence"] == sequence_no
                        and row["available_sequence"] > sequence_no
                    ],
                    "guidance": [dict(row) for row in guidance],
                    "advice": [dict(row) for row in advice],
                }
            )
        return {
            "blocks": blocks,
            "collected_medal_count": len(found_numbers),
            "player_checkpoint": state.get("story", {}).get("checkpoint_id"),
        }
    finally:
        connection.close()


def _source(row: dict) -> str:
    return f"{row['source_title']} — {row['source_url']} ({row['locator']})"


def _print_medals(label: str, rows: list[dict], include_sources: bool) -> None:
    if not rows:
        return
    print(f"Medals {label}:")
    for row in rows:
        suffix = ""
        if label == "LATER":
            suffix = f" [return: {row['available_checkpoint']}; gate: {row['available_from']}]"
        print(f"- #{row['medal_number']} {row['location']}: {row['detail']}{suffix}")
        if include_sources:
            print(f"  Source: {_source(row)}")


def print_walkthrough(report: dict, include_sources: bool = False) -> None:
    print(f"Early checklist (already collected medals hidden: {report['collected_medal_count']})")
    if report["player_checkpoint"]:
        print(f"Player-state checkpoint: {report['player_checkpoint']}")
    for block in report["blocks"]:
        checkpoint = block["checkpoint"]
        complete = checkpoint["coverage_status"] == "complete"
        print(f"\n{checkpoint['checkpoint_id']} — {checkpoint['name']} [{checkpoint['coverage_status']}]")
        print("STOP:")
        if not block["stops"]:
            print("- No verified STOP recorded; incomplete coverage is not proof that none exists.")
        for row in block["stops"]:
            print(f"- {row['action']}")
            if row["unavailable_after"]:
                print(f"  Deadline: {row['unavailable_after']}")
            if include_sources:
                print(f"  Source: {_source(row)}")

        print("NOW:")
        if not block["now"]:
            print("- No normalized actions; this is a coverage gap.")
        for number, row in enumerate(block["now"], 1):
            marker = "required" if row["required_for_100_percent"] else "optional"
            print(f"{number}. [{marker}] {row['action']}")
            if include_sources:
                print(f"   Source: {_source(row)}")

        medal_buckets = (
            ("NOW", block["medals_now"]),
            ("BACKTRACK", block["medals_backtrack"]),
            ("LATER", block["medals_later"]),
        )
        if any(rows for _, rows in medal_buckets):
            for label, rows in medal_buckets:
                _print_medals(label, rows, include_sources)
        else:
            print("Medals: none recorded for this checkpoint.")

        advice_by_type = {
            advice_type: [
                row for row in block["advice"] if row["advice_type"] == advice_type
            ]
            for advice_type in ("gear", "boss", "grind", "vocation")
        }
        labels = {
            "gear": "Gear", "boss": "Boss", "grind": "Grind (optional)",
            "vocation": "Vocations",
        }
        goal_markers = {"completion_safe": " (safe)", "immediate_power": " (power)", "both": ""}
        for advice_type in ("gear", "boss", "grind", "vocation"):
            rows = advice_by_type[advice_type]
            if not rows:
                continue
            summaries = "; ".join(
                f"{row['subject']} — {row['advice_text']}"
                f"{goal_markers[row['recommendation_goal']]}" for row in rows
            )
            print(f"{labels[advice_type]}: {summaries}")
            if include_sources:
                for row in rows:
                    print(f"  Source: {_source(row)}")
        core_missing = [name for name in ("gear", "boss", "grind") if not advice_by_type[name]]
        if len(core_missing) == 3:
            print("Advice: gear, boss, and grind guidance not normalized.")
        elif core_missing:
            print(f"Advice gap: {' and '.join(core_missing)} not normalized.")
        qualifier = "" if complete else " (partial audit; not a guarantee)"
        print(f"Recorded safe condition{qualifier}: {checkpoint['safe_exit_condition']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="from_checkpoint", default=DEFAULT_FROM)
    parser.add_argument("--through", dest="through_checkpoint", default=DEFAULT_THROUGH)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument(
        "--sources", action="store_true", help="Show a source citation for each sourced line"
    )
    args = parser.parse_args()
    try:
        print_walkthrough(
            load_walkthrough(
                args.db, args.state, args.from_checkpoint, args.through_checkpoint
            ),
            include_sources=args.sources,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
