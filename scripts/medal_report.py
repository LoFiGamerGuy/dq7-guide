#!/usr/bin/env python3
"""List Mini Medals obtainable by a selected checkpoint."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"


def medals_available_through(db_path: Path, checkpoint_id: str) -> list[dict]:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        checkpoint = connection.execute(
            "SELECT sequence_no FROM checkpoints WHERE checkpoint_id = ?",
            (checkpoint_id,),
        ).fetchone()
        if checkpoint is None:
            raise ValueError(f"Unknown checkpoint: {checkpoint_id}")
        rows = connection.execute(
            """SELECT m.*, location_cp.name AS location_checkpoint,
                available_cp.name AS available_checkpoint,
                s.title AS source_title, s.url AS source_url
            FROM mini_medal_locations m
            JOIN checkpoints location_cp ON location_cp.checkpoint_id = m.checkpoint_id
            JOIN checkpoints available_cp
              ON available_cp.checkpoint_id = m.available_checkpoint_id
            JOIN sources s ON s.source_id = m.source_id
            WHERE available_cp.sequence_no <= ?
            ORDER BY m.medal_number""",
            (checkpoint["sequence_no"],),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--through", required=True, help="Checkpoint ID")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    try:
        rows = medals_available_through(args.db, args.through)
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Mini Medals obtainable through {args.through}: {len(rows)}")
    for row in rows:
        print(
            f"- #{row['medal_number']} {row['location']} ({row['time_period']}): "
            f"{row['detail']} [available: {row['available_checkpoint']}; "
            f"gate: {row['available_from'] or 'normal access'}]"
        )
        print(f"  Source: {row['source_title']} — {row['source_url']} ({row['locator']})")


if __name__ == "__main__":
    main()
