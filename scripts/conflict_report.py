#!/usr/bin/env python3
"""List unresolved or resolved knowledge-base conflicts with full provenance."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"


def load_conflicts(db_path: Path, include_resolved: bool = False) -> list[dict]:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        where = "" if include_resolved else "WHERE cf.status != 'resolved'"
        rows = connection.execute(
            f"""SELECT cf.*, ca.subject_key, ca.predicate, ca.scope_json,
                ca.value_json AS value_a, ca.locator AS locator_a,
                sa.title AS source_title_a, sa.url AS source_url_a,
                cb.value_json AS value_b, cb.locator AS locator_b,
                sb.title AS source_title_b, sb.url AS source_url_b
            FROM conflicts cf
            JOIN claims ca ON ca.claim_id = cf.claim_a_id
            JOIN claims cb ON cb.claim_id = cf.claim_b_id
            JOIN sources sa ON sa.source_id = ca.source_id
            JOIN sources sb ON sb.source_id = cb.source_id
            {where}
            ORDER BY ca.subject_key, ca.predicate, cf.conflict_id"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def print_conflicts(rows: list[dict]) -> None:
    if not rows:
        print("No matching conflicts.")
        return
    for row in rows:
        print(f"{row['conflict_id']}: {row['subject_key']} / {row['predicate']}")
        print(f"Status: {row['status']} ({row['detection_method']})")
        print("Scope: " + json.dumps(json.loads(row["scope_json"]), sort_keys=True))
        print(f"A [{row['claim_a_id']}]: {row['value_a']}")
        print(f"  {row['source_title_a']} — {row['source_url_a']} ({row['locator_a'] or 'no locator'})")
        print(f"B [{row['claim_b_id']}]: {row['value_b']}")
        print(f"  {row['source_title_b']} — {row['source_url_b']} ({row['locator_b'] or 'no locator'})")
        if row["rationale"]:
            print(f"Rationale: {row['rationale']}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--all", action="store_true", help="Include resolved conflicts")
    args = parser.parse_args()
    try:
        print_conflicts(load_conflicts(args.db, args.all))
    except FileNotFoundError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
