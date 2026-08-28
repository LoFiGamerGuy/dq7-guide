#!/usr/bin/env python3
"""Show a monster's registry entry, known encounters, and verified drops."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from build_kb import DEFAULT_DB

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"


def load_monster_report(db_path: Path, query: str) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        number = query.removeprefix("#")
        ordinal = int(number) if number.isdigit() else None
        monster = connection.execute(
            """SELECT * FROM monsters
            WHERE monster_id = ? OR lower(english_name) = lower(?)
               OR source_ordinal = ?""",
            (query, query, ordinal),
        ).fetchone()
        if monster is None:
            raise ValueError(f"Unknown monster: {query}")
        encounters = connection.execute(
            """SELECT me.*, cp.name AS available_checkpoint,
                expiry.name AS unavailable_checkpoint,
                s.title AS source_title, s.url AS source_url
            FROM monster_encounters me
            LEFT JOIN checkpoints cp ON cp.checkpoint_id = me.available_from_checkpoint_id
            LEFT JOIN checkpoints expiry ON expiry.checkpoint_id = me.unavailable_after_checkpoint_id
            JOIN sources s USING(source_id)
            WHERE me.monster_id = ?
            ORDER BY cp.sequence_no, me.location_text""",
            (monster["monster_id"],),
        ).fetchall()
        drops = connection.execute(
            """SELECT md.*, s.title AS source_title, s.url AS source_url
            FROM monster_drops md JOIN sources s USING(source_id)
            WHERE md.monster_id = ? ORDER BY md.drop_id""",
            (monster["monster_id"],),
        ).fetchall()
        return {
            "monster": dict(monster),
            "encounters": [dict(row) for row in encounters],
            "drops": [dict(row) for row in drops],
        }
    finally:
        connection.close()


def print_monster_report(report: dict, include_sources: bool = False) -> None:
    monster = report["monster"]
    print(
        f"#{monster['source_ordinal']} {monster['english_name'] or monster['source_display_name']}"
        f" — HP {monster['hp']}; EXP {monster['experience']}; gold {monster['gold']}"
    )
    if report["encounters"]:
        print("Find:")
        for row in report["encounters"]:
            gate = row["available_checkpoint"] or "gate unknown"
            print(f"- {row['location_text']} ({row['time_period']}) — from {gate}")
            if include_sources:
                print(f"  Source: {row['source_title']} — {row['source_url']} ({row['locator']})")
    else:
        print("Find: not normalized yet")
    if report["drops"]:
        print("Drops: " + ", ".join(
            row["item_name"] + (f" ({row['drop_rate_text']})" if row["drop_rate_text"] else "")
            for row in report["drops"]
        ))
        if include_sources:
            for row in report["drops"]:
                print(f"  Source: {row['source_title']} — {row['source_url']} ({row['locator']})")
    else:
        print("Drops: not normalized yet")


def load_checkpoint_monsters(
    db_path: Path, state_path: Path, checkpoint_id: str | None, include_completed: bool = False
) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    selected = checkpoint_id or state.get("story", {}).get("checkpoint_id")
    if not selected:
        raise ValueError("Checkpoint is unknown; pass --checkpoint or record player progress")
    completed = state.get("completion", {}).get("monster_entries", [])
    if not isinstance(completed, list) or any(not isinstance(value, str) for value in completed):
        raise ValueError("completion.monster_entries must be a list of strings")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        checkpoint = connection.execute(
            "SELECT name FROM checkpoints WHERE checkpoint_id = ?", (selected,)
        ).fetchone()
        if checkpoint is None:
            raise ValueError(f"Unknown checkpoint: {selected}")
        rows = connection.execute(
            """SELECT m.monster_id, m.source_ordinal, m.english_name,
                group_concat(me.location_text || ' (' || me.time_period || ')', '; ') AS locations
            FROM monster_encounters me JOIN monsters m USING(monster_id)
            WHERE me.available_from_checkpoint_id = ?
            GROUP BY m.monster_id ORDER BY m.source_ordinal""",
            (selected,),
        ).fetchall()
        monsters = [dict(row) | {"completed": row["monster_id"] in completed} for row in rows]
        if not include_completed:
            monsters = [row for row in monsters if not row["completed"]]
        return {"checkpoint_id": selected, "checkpoint_name": checkpoint["name"], "monsters": monsters}
    finally:
        connection.close()


def print_checkpoint_monsters(report: dict) -> None:
    print(f"Monsters introduced at {report['checkpoint_name']}:")
    if not report["monsters"]:
        print("- None remaining in normalized coverage")
        return
    for row in report["monsters"]:
        marker = "DONE" if row["completed"] else "TODO"
        print(f"- [{marker}] #{row['source_ordinal']} {row['english_name']} — {row['locations']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("monster", nargs="?", help="English name, stable ID, or Monster List number")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--checkpoint", help="List monsters introduced at this checkpoint")
    parser.add_argument("--all", action="store_true", help="Include completed monster entries")
    parser.add_argument("--sources", action="store_true")
    args = parser.parse_args()
    try:
        if args.checkpoint:
            if args.monster:
                raise ValueError("monster cannot be combined with --checkpoint")
            print_checkpoint_monsters(
                load_checkpoint_monsters(args.db, args.state, args.checkpoint, args.all)
            )
        elif args.monster:
            print_monster_report(load_monster_report(args.db, args.monster), args.sources)
        else:
            print_checkpoint_monsters(
                load_checkpoint_monsters(args.db, args.state, None, args.all)
            )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
