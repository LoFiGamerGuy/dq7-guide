#!/usr/bin/env python3
"""Search the local FTS5 corpus and show provenance."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"


def normalize_query(query: str) -> str:
    tokens = [token.strip("\"'()[]{}.,:;!?+-*/\\") for token in query.split()]
    tokens = [token for token in tokens if token]
    return " OR ".join(f'"{token}"' for token in tokens)


def search(db_path: Path, query: str, limit: int = 8):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            """SELECT
                d.document_id, d.title, d.body, d.domain, d.checkpoint_key,
                d.confidence, d.reconstruction_status,
                s.title AS source_title, s.url AS source_url,
                bm25(document_fts, 3.0, 1.0, 0.5, 0.5) AS score
            FROM document_fts
            JOIN documents d ON d.rowid = document_fts.rowid
            LEFT JOIN sources s ON s.source_id = d.source_id
            WHERE document_fts MATCH ?
            ORDER BY score
            LIMIT ?""",
            (normalize_query(query), limit),
        ).fetchall()
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Plain-language search terms")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    if not args.db.exists():
        raise SystemExit(f"Database not found: {args.db}. Run scripts/build_kb.py first.")

    rows = search(args.db, args.query, args.limit)
    if not rows:
        print("No results.")
        return

    for index, row in enumerate(rows, 1):
        print(f"[{index}] {row['title']} ({row['domain']}, {row['confidence']})")
        print(row["body"])
        if row["checkpoint_key"]:
            print(f"Checkpoint: {row['checkpoint_key']}")
        if row["source_title"]:
            print(f"Source: {row['source_title']} — {row['source_url']}")
        print(f"Record status: {row['reconstruction_status']}")
        print()


if __name__ == "__main__":
    main()

