#!/usr/bin/env python3
"""Show a monster's registry entry, known encounters, and verified drops."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from build_kb import DEFAULT_DB


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("monster", help="English name, stable ID, or Monster List number")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--sources", action="store_true")
    args = parser.parse_args()
    try:
        print_monster_report(load_monster_report(args.db, args.monster), args.sources)
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
