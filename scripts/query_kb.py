#!/usr/bin/env python3
"""Search the local FTS5 corpus and show provenance."""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"


def normalize_query(query: str) -> str | None:
    tokens = re.findall(r"[\w]+(?:['’][\w]+)?", query, flags=re.UNICODE)
    if not tokens:
        return None
    return " OR ".join(f'"{token}"' for token in tokens)


def _tokens(query: str) -> list[str]:
    return re.findall(r"[\w]+(?:['’][\w]+)?", query, flags=re.UNICODE)


def _fts_rows(connection: sqlite3.Connection, expression: str, limit: int) -> list[dict]:
    return [dict(row) for row in connection.execute(
        """SELECT
            d.document_id, d.title, d.body, d.domain, d.checkpoint_key,
            d.confidence, d.reconstruction_status,
            d.locator, d.source_id, s.title AS source_title,
            s.url AS source_url, s.updated_at AS source_updated_at,
            s.retrieved_at AS source_retrieved_at,
            bm25(document_fts, 3.0, 1.0, 0.5, 0.5) AS score
        FROM document_fts
        JOIN documents d ON d.rowid = document_fts.rowid
        LEFT JOIN sources s ON s.source_id = d.source_id
        WHERE document_fts MATCH ?
        ORDER BY score
        LIMIT ?""",
        (expression, limit),
    ).fetchall()]


def _structured_rows(connection: sqlite3.Connection, tokens: list[str], limit: int) -> list[dict]:
    clauses = " AND ".join(
        "lower(search_text) LIKE ?" for _ in tokens
    )
    parameters = [f"%{token.casefold()}%" for token in tokens]
    rows = connection.execute(
        f"""WITH searchable AS (
            SELECT 'claim:' || c.claim_id AS document_id,
                replace(c.subject_key, '_', ' ') || ' · ' ||
                    replace(c.predicate, '_', ' ') AS title,
                c.subject_key || ' ' || c.predicate || ' ' || c.value_json AS search_text,
                c.value_json AS body, 'claim' AS domain, NULL AS checkpoint_key,
                c.confidence, c.reconstruction_status, c.locator, c.source_id
            FROM claims c
            UNION ALL
            SELECT 'item-alias:' || a.alias_id, a.alias || ' → ' || i.name,
                a.alias || ' ' || i.name || ' ' || i.canonical_key,
                'Sourced item alias for ' || i.name, 'item identity', NULL,
                a.confidence, 'normalized', a.locator, a.source_id
            FROM item_aliases a JOIN items i ON i.item_id=a.item_id
            UNION ALL
            SELECT 'item:' || i.item_id, i.name,
                i.name || ' ' || i.canonical_key,
                'Canonical item identity', 'item identity', NULL,
                i.confidence, 'normalized', i.locator, i.source_id
            FROM items i
        )
        SELECT q.document_id, q.title, q.body, q.domain, q.checkpoint_key,
            q.confidence, q.reconstruction_status, q.locator, q.source_id,
            s.title AS source_title, s.url AS source_url,
            s.updated_at AS source_updated_at,
            s.retrieved_at AS source_retrieved_at, -100.0 AS score
        FROM searchable q LEFT JOIN sources s ON s.source_id=q.source_id
        WHERE {clauses}
        ORDER BY CASE WHEN lower(q.title)=? THEN 0 ELSE 1 END, q.title
        LIMIT ?""",
        (*parameters, " ".join(tokens).casefold(), limit),
    ).fetchall()
    return [dict(row) for row in rows]


def search(db_path: Path, query: str, limit: int = 8):
    tokens = _tokens(query)
    if not tokens:
        return []
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        exact = " AND ".join(f'"{token}"' for token in tokens)
        broad = " OR ".join(f'"{token}"' for token in tokens)
        results = _fts_rows(connection, exact, limit)
        results.extend(_structured_rows(connection, tokens, limit))
        if len({row["document_id"] for row in results}) < limit:
            results.extend(_fts_rows(connection, broad, limit))
        deduplicated = []
        seen = set()
        for row in results:
            if row["document_id"] in seen:
                continue
            seen.add(row["document_id"])
            deduplicated.append(row)
            if len(deduplicated) == limit:
                break
        return deduplicated
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
            print(f"Source ID: {row['source_id']}")
            if row["locator"]:
                print(f"Locator: {row['locator']}")
            print(
                "Freshness: "
                f"updated={row['source_updated_at'] or 'unknown'}, "
                f"retrieved={row['source_retrieved_at']}"
            )
        print(f"Record status: {row['reconstruction_status']}")
        print()


if __name__ == "__main__":
    main()
