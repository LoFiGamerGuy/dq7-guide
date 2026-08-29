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
            f"""SELECT cf.*, ca.subject_key, ca.predicate,
                ca.scope_json AS scope_a, cb.scope_json AS scope_b,
                ca.value_json AS value_a, ca.locator AS locator_a,
                ca.confidence AS confidence_a,
                ca.verification_status AS verification_status_a,
                sa.source_id AS source_id_a,
                sa.title AS source_title_a, sa.url AS source_url_a,
                sa.updated_at AS source_updated_at_a,
                sa.retrieved_at AS source_retrieved_at_a,
                cb.value_json AS value_b, cb.locator AS locator_b,
                cb.confidence AS confidence_b,
                cb.verification_status AS verification_status_b,
                sb.source_id AS source_id_b,
                sb.title AS source_title_b, sb.url AS source_url_b,
                sb.updated_at AS source_updated_at_b,
                sb.retrieved_at AS source_retrieved_at_b,
                cr.value_json AS resolution_value,
                cr.scope_json AS resolution_scope,
                cr.confidence AS resolution_confidence,
                cr.verification_status AS resolution_verification_status,
                cr.locator AS resolution_locator,
                sr.source_id AS resolution_source_id,
                sr.title AS resolution_source_title,
                sr.url AS resolution_source_url,
                sr.updated_at AS resolution_source_updated_at,
                sr.retrieved_at AS resolution_source_retrieved_at
            FROM conflicts cf
            JOIN claims ca ON ca.claim_id = cf.claim_a_id
            JOIN claims cb ON cb.claim_id = cf.claim_b_id
            JOIN sources sa ON sa.source_id = ca.source_id
            JOIN sources sb ON sb.source_id = cb.source_id
            LEFT JOIN claims cr ON cr.claim_id = cf.resolution_claim_id
            LEFT JOIN sources sr ON sr.source_id = cr.source_id
            {where}
            ORDER BY ca.subject_key, ca.predicate, cf.conflict_id"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def load_resolution_evidence(db_path: Path, resolution_claim_id: str) -> list[dict]:
    """Return every claim matching a resolution value, with publisher provenance."""
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT c.claim_id, c.value_json, c.scope_json, c.confidence,
                c.verification_status, c.locator, s.source_id, s.title,
                s.publisher, s.url, s.updated_at, s.retrieved_at
            FROM claims resolution
            JOIN claims c ON c.subject_key=resolution.subject_key
                AND c.predicate=resolution.predicate
                AND c.value_json=resolution.value_json
            JOIN sources s ON s.source_id=c.source_id
            WHERE resolution.claim_id=?
            ORDER BY s.publisher, c.claim_id""",
            (resolution_claim_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def print_conflicts(rows: list[dict], db_path: Path = DEFAULT_DB) -> None:
    if not rows:
        print("No matching conflicts.")
        return
    for row in rows:
        print(f"{row['conflict_id']}: {row['subject_key']} / {row['predicate']}")
        print(f"Status: {row['status']} ({row['detection_method']})")
        print("Scope A: " + json.dumps(json.loads(row["scope_a"]), sort_keys=True))
        print("Scope B: " + json.dumps(json.loads(row["scope_b"]), sort_keys=True))
        print(f"A [{row['claim_a_id']}]: {row['value_a']}")
        print(f"  {row['source_title_a']} — {row['source_url_a']} ({row['locator_a'] or 'no locator'})")
        print(f"B [{row['claim_b_id']}]: {row['value_b']}")
        print(f"  {row['source_title_b']} — {row['source_url_b']} ({row['locator_b'] or 'no locator'})")
        if (row["resolution_claim_id"] and
                row["resolution_claim_id"] not in (row["claim_a_id"], row["claim_b_id"])):
            print(f"Resolution [{row['resolution_claim_id']}]: {row['resolution_value']}")
            for evidence in load_resolution_evidence(
                    db_path, row["resolution_claim_id"]):
                print(f"  {evidence['title']} ({evidence['publisher']}) — "
                      f"{evidence['url']} ({evidence['locator'] or 'no locator'})")
        if row["rationale"]:
            print(f"Rationale: {row['rationale']}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--all", action="store_true", help="Include resolved conflicts")
    args = parser.parse_args()
    try:
        print_conflicts(load_conflicts(args.db, args.all), args.db)
    except FileNotFoundError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
