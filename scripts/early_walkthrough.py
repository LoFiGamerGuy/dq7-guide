#!/usr/bin/env python3
"""Print a conservative chronological completion walkthrough."""

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


def resolve_checkpoint_range(
    state_path: Path,
    checkpoint: str | None,
    from_checkpoint: str | None,
    through_checkpoint: str | None,
) -> tuple[str, str]:
    if checkpoint and (from_checkpoint or through_checkpoint):
        raise ValueError("--checkpoint cannot be combined with --from or --through")
    if bool(from_checkpoint) != bool(through_checkpoint):
        raise ValueError("--from and --through must be supplied together")
    if checkpoint:
        return checkpoint, checkpoint
    if from_checkpoint:
        return from_checkpoint, through_checkpoint  # type: ignore[return-value]
    state = json.loads(state_path.read_text(encoding="utf-8"))
    saved = state.get("story", {}).get("checkpoint_id")
    selected = saved or DEFAULT_FROM
    return selected, selected


def classify_medal_tracking(
    medal_count: int | None, found_numbers: set[int]
) -> tuple[str, str | None]:
    if medal_count is None and not found_numbers:
        return "unknown", None
    if medal_count is None:
        return (
            "partial",
            "Medal count is unknown; listed medal IDs are treated only as confirmed finds.",
        )
    if medal_count != len(found_numbers):
        return (
            "inconsistent",
            f"Medal count ({medal_count}) disagrees with recorded medal IDs ({len(found_numbers)}).",
        )
    return "known", None


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
    medal_count = state.get("completion", {}).get("mini_medal_count")
    if not isinstance(found, list) or any(
        not isinstance(number, int) or isinstance(number, bool) for number in found
    ):
        raise ValueError("completion.mini_medals_found must be a list of integers")
    found_numbers = set(found)
    completed = state.get("completion", {}).get("obligations_completed", [])
    if not isinstance(completed, list) or any(not isinstance(value, str) for value in completed):
        raise ValueError("completion.obligations_completed must be a list of strings")
    completed_ids = set(completed)
    if medal_count is not None and (
        not isinstance(medal_count, int) or isinstance(medal_count, bool) or medal_count < 0
    ):
        raise ValueError("completion.mini_medal_count must be a non-negative integer or null")
    medal_tracking_status, medal_tracking_warning = classify_medal_tracking(
        medal_count, found_numbers
    )

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
        unordered = connection.execute(
            """SELECT DISTINCT o.checkpoint_id
            FROM checkpoint_obligations o JOIN checkpoints c USING(checkpoint_id)
            WHERE c.sequence_no BETWEEN ? AND ? AND o.display_order IS NULL
            ORDER BY c.sequence_no LIMIT 1""",
            (start["sequence_no"], end["sequence_no"]),
        ).fetchone()
        if unordered is not None:
            raise ValueError(
                f"Checkpoint checklist is not ordered yet: {unordered['checkpoint_id']}"
            )
        known_completed_ids = {
            row[0] for row in connection.execute(
                """SELECT obligation_id FROM checkpoint_obligations
                WHERE obligation_id IN (SELECT value FROM json_each(?))""",
                (json.dumps(sorted(completed_ids)),),
            )
        }
        unknown_completed_ids = sorted(completed_ids - known_completed_ids)
        blocks = []
        for checkpoint in checkpoints:
            sequence_no = checkpoint["sequence_no"]
            obligations = connection.execute(
                """SELECT o.*, s.title AS source_title, s.url AS source_url
                FROM checkpoint_obligations o JOIN sources s USING(source_id)
                WHERE o.checkpoint_id = ?
                ORDER BY o.stop_before_advancing DESC,
                         o.display_order, o.obligation_id""",
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
            conflicts = connection.execute(
                """SELECT f.conflict_id, ca.subject_key, ca.predicate,
                    ca.locator AS claim_a_locator,
                    sa.title AS claim_a_source_title, sa.url AS claim_a_source_url,
                    cb.locator AS claim_b_locator,
                    sb.title AS claim_b_source_title, sb.url AS claim_b_source_url
                FROM conflicts f
                JOIN claims ca ON ca.claim_id = f.claim_a_id
                JOIN claims cb ON cb.claim_id = f.claim_b_id
                JOIN sources sa ON sa.source_id = ca.source_id
                JOIN sources sb ON sb.source_id = cb.source_id
                WHERE f.status = 'unresolved'
                  AND (
                    json_extract(ca.scope_json, '$.checkpoint_from') = ?
                    OR json_extract(ca.scope_json, '$.checkpoint_to') = ?
                  )
                ORDER BY ca.subject_key, ca.predicate, f.conflict_id""",
                (checkpoint["checkpoint_id"], checkpoint["checkpoint_id"]),
            ).fetchall()
            stop_rows = [dict(row) for row in obligations if row["stop_before_advancing"]]
            now_rows = [dict(row) for row in obligations if not row["stop_before_advancing"]]
            blocks.append(
                {
                    "checkpoint": dict(checkpoint),
                    "recorded_stop_count": len(stop_rows),
                    "recorded_now_count": len(now_rows),
                    "stops": [row for row in stop_rows if row["obligation_id"] not in completed_ids],
                    "now": [row for row in now_rows if row["obligation_id"] not in completed_ids],
                    "completed_hidden_count": sum(
                        row["obligation_id"] in completed_ids for row in stop_rows + now_rows
                    ),
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
                    "conflicts": [dict(row) for row in conflicts],
                }
            )
        return {
            "blocks": blocks,
            "collected_medal_count": len(found_numbers),
            "mini_medal_count": medal_count,
            "medal_tracking_status": medal_tracking_status,
            "medal_tracking_warning": medal_tracking_warning,
            "player_checkpoint": state.get("story", {}).get("checkpoint_id"),
            "unknown_completed_ids": unknown_completed_ids,
            "completed_hidden_count": sum(
                block["completed_hidden_count"] for block in blocks
            ),
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


def _print_advice(block: dict, include_sources: bool, show_gaps: bool = True) -> None:
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
        summaries = []
        for row in rows:
            applicability = json.loads(row["applicability_json"])
            required_medals = applicability.get("requires", {}).get("mini_medals")
            condition = f"If you have {required_medals} medals, " if required_medals else ""
            summaries.append(
                f"{row['subject']} — {condition}{row['advice_text']}"
                f"{goal_markers[row['recommendation_goal']]}"
            )
        print(f"{labels[advice_type]}: {'; '.join(summaries)}")
        if include_sources:
            for row in rows:
                print(f"  Source: {_source(row)}")
    core_missing = [name for name in ("gear", "boss", "grind") if not advice_by_type[name]]
    if not show_gaps:
        return
    if len(core_missing) == 3:
        print("Advice: gear, boss, and grind guidance not normalized.")
    elif core_missing:
        print(f"Advice gap: {' and '.join(core_missing)} not normalized.")


def _print_conflicts(block: dict, include_sources: bool) -> None:
    for row in block["conflicts"]:
        subject = row["subject_key"].split(":", 1)[-1].replace("_", " ").title()
        predicate = row["predicate"].replace("_", " ")
        print(f"CONFLICT: {subject} — {predicate} disputed")
        if include_sources:
            print(
                f"  Source A: {row['claim_a_source_title']} — "
                f"{row['claim_a_source_url']} ({row['claim_a_locator'] or 'locator unavailable'})"
            )
            print(
                f"  Source B: {row['claim_b_source_title']} — "
                f"{row['claim_b_source_url']} ({row['claim_b_locator'] or 'locator unavailable'})"
            )


def print_walkthrough(
    report: dict, include_sources: bool = False, compact: bool = False
) -> None:
    if report["medal_tracking_status"] == "known":
        medal_note = f"medals tracked: {report['mini_medal_count']}"
    elif report["medal_tracking_status"] == "unknown":
        medal_note = "medal tracking unknown"
    else:
        medal_note = f"confirmed medal IDs hidden: {report['collected_medal_count']}"
    if not compact:
        print(
            f"Chronological walkthrough (completed checks hidden: {report['completed_hidden_count']}; "
            f"{medal_note})"
        )
    if report["medal_tracking_warning"]:
        print(f"Medal tracking warning: {report['medal_tracking_warning']}")
    if report["unknown_completed_ids"]:
        print(
            "Progress warning: unknown completed obligation ID(s): "
            + ", ".join(report["unknown_completed_ids"])
        )
    if report["player_checkpoint"]:
        print(f"Player-state checkpoint: {report['player_checkpoint']}")
    for block in report["blocks"]:
        checkpoint = block["checkpoint"]
        complete = checkpoint["coverage_status"] == "complete"
        status = "" if compact else f" [{checkpoint['coverage_status']}]"
        print(f"\n{checkpoint['checkpoint_id']} — {checkpoint['name']}{status}")
        if block["stops"] or not compact:
            print("STOP:")
        if not compact and not block["stops"] and block["recorded_stop_count"]:
            print("- All recorded warnings cleared.")
        elif not compact and not block["stops"]:
            print("- No verified STOP recorded; incomplete coverage is not proof that none exists.")
        for row in block["stops"]:
            print(f"- [step {row['display_order']}] {row['action']}")
            if row["unavailable_after"]:
                print(f"  Deadline: {row['unavailable_after']}")
            if include_sources:
                print(f"  Source: {_source(row)}")

        _print_conflicts(block, include_sources)
        _print_advice(block, include_sources, show_gaps=not compact)

        if block["now"] or not compact:
            print("NOW:")
        if not compact and not block["now"] and block["recorded_now_count"]:
            print("- All recorded actions complete.")
        elif not compact and not block["now"]:
            print("- No normalized actions; this is a coverage gap.")
        for row in block["now"]:
            marker = "required" if row["required_for_100_percent"] else "optional"
            print(f"{row['display_order']}. [{marker}] {row['action']}")
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
        elif not compact:
            print("Medals: none recorded for this checkpoint.")

        qualifier = "" if complete else " (partial audit; not a guarantee)"
        if compact:
            print(f"SAFE: {checkpoint['safe_exit_condition']}")
        else:
            print(f"Recorded safe condition{qualifier}: {checkpoint['safe_exit_condition']}")
        if not compact and (block["stops"] or block["now"]):
            print(
                "Mark complete: python scripts/player_progress.py done "
                f"{checkpoint['checkpoint_id']} <step>"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", help="Show one checkpoint")
    parser.add_argument("--from", dest="from_checkpoint")
    parser.add_argument("--through", dest="through_checkpoint")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument(
        "--sources", action="store_true", help="Show a source citation for each sourced line"
    )
    parser.add_argument(
        "--compact", action="store_true", help="Hide progress and coverage boilerplate"
    )
    args = parser.parse_args()
    try:
        start, end = resolve_checkpoint_range(
            args.state, args.checkpoint, args.from_checkpoint, args.through_checkpoint
        )
        print_walkthrough(
            load_walkthrough(
                args.db, args.state, start, end
            ),
            include_sources=args.sources,
            compact=args.compact,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
