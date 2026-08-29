#!/usr/bin/env python3
"""Search the local FTS5 corpus and show provenance."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"
DEFAULT_EVIDENCE_GAPS = ROOT / "data" / "evidence_gaps.json"
EVIDENCE_GAP_SEARCH_TERMS = {
    "gap_blue_button_cutoff":
        "Blue Button before Cataclysm cutoff missable Emberdale child disaster",
    "gap_ruby_of_protection_drawer":
        "Ruby of Protection Faraday Castle throne bedroom drawer container chest location",
    "gap_lucky_panel_probabilities":
        "Lucky Panel probability probabilities odds chance draw rate weights denominator",
    "gap_reproducible_farm_rates":
        "farming farm EXP experience gold drop encounter rate efficiency benchmark hour",
    "gap_repeatable_monster_hearts":
        "repeatable renewable farm farming Monster Heart respawn rematch drop vicious",
    "gap_duplicate_equipment_stacking":
        "duplicate same item accessory accessories Monster Heart stacking stack legality "
        "Rabbit Tail formula cap equip two same work reserve",
    "gap_achievement_counter_semantics":
        "achievement trophy counter persistence save reset New Game demo import overlap "
        "quick win Field Day Monster Masher Metal Mangler carry over count",
}

EVIDENCE_GAP_STOPWORDS = {
    "a", "an", "are", "can", "do", "does", "for", "get", "has", "how", "i",
    "in", "is", "it", "much", "of", "per", "still", "the", "what", "which",
}

EVIDENCE_GAP_TOKEN_NORMALIZATIONS = {
    "accessories": "accessory", "counters": "counter", "drawers": "drawer",
    "hearts": "heart", "monsters": "monster", "odds": "probability",
    "rates": "rate", "repeatedly": "repeatable", "wins": "win",
}


def normalize_query(query: str) -> str | None:
    tokens = re.findall(r"[\w]+(?:['’][\w]+)?", query, flags=re.UNICODE)
    if not tokens:
        return None
    return " OR ".join(f'"{token}"' for token in tokens)


def _tokens(query: str) -> list[str]:
    return re.findall(r"[\w]+(?:['’][\w]+)?", query, flags=re.UNICODE)


def _gap_tokens(value: str) -> list[str]:
    """Normalize natural question phrasing without weakening ordinary FTS search."""
    normalized = []
    for token in _tokens(value):
        token = token.casefold()
        if token in EVIDENCE_GAP_STOPWORDS:
            continue
        normalized.append(EVIDENCE_GAP_TOKEN_NORMALIZATIONS.get(token, token))
    return normalized


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


def _evidence_gap_rows(connection: sqlite3.Connection, tokens: list[str]) -> list[dict]:
    """Return curated unknowns before generic matches when every query token matches."""
    gaps = json.loads(DEFAULT_EVIDENCE_GAPS.read_text(encoding="utf-8"))
    gap_ids = {gap["gap_id"] for gap in gaps}
    if gap_ids != set(EVIDENCE_GAP_SEARCH_TERMS):
        raise ValueError(
            "Evidence-gap search vocabulary is out of sync: "
            f"missing={sorted(gap_ids - set(EVIDENCE_GAP_SEARCH_TERMS))}, "
            f"extra={sorted(set(EVIDENCE_GAP_SEARCH_TERMS) - gap_ids)}"
        )
    rows = []
    for gap in gaps:
        search_text = " ".join((gap["gap_id"], gap["subject"], gap["summary"],
                                gap["acceptance_condition"],
                                EVIDENCE_GAP_SEARCH_TERMS.get(gap["gap_id"], "")))
        search_tokens = set(_gap_tokens(search_text))
        query_tokens = _gap_tokens(" ".join(tokens))
        if not query_tokens or not all(token in search_tokens for token in query_tokens):
            continue
        claim_ids = gap.get("claim_ids", [])
        evidence = []
        if claim_ids:
            placeholders = ",".join("?" for _ in claim_ids)
            evidence = [dict(row) for row in connection.execute(
                f"""SELECT c.claim_id, c.locator, c.source_id, s.title AS source_title,
                    s.url AS source_url, s.updated_at AS source_updated_at,
                    s.retrieved_at AS source_retrieved_at
                FROM claims c JOIN sources s USING(source_id)
                WHERE c.claim_id IN ({placeholders}) ORDER BY c.claim_id""",
                claim_ids,
            ).fetchall()]
            found_claim_ids = {row["claim_id"] for row in evidence}
            missing_claim_ids = set(claim_ids) - found_claim_ids
            if missing_claim_ids:
                raise ValueError(f"Unknown evidence-gap claim ID(s): {sorted(missing_claim_ids)}")
        rows.append({
            "document_id": f"evidence-gap:{gap['gap_id']}",
            "title": f"Open evidence gap · {gap['subject']}",
            "body": f"{gap['summary']} Needed: {gap['acceptance_condition']}",
            "domain": "evidence gap",
            "checkpoint_key": None,
            "confidence": "unknown preserved",
            "reconstruction_status": gap["status"],
            "locator": None,
            "source_id": None,
            "source_title": None,
            "source_url": None,
            "source_updated_at": None,
            "source_retrieved_at": None,
            "score": -200.0,
            "evidence": evidence,
        })
    return rows


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
        results = _evidence_gap_rows(connection, tokens)
        results.extend(_fts_rows(connection, exact, limit))
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
        for evidence in row.get("evidence", []):
            print(f"Supporting claim: {evidence['source_title']} — {evidence['source_url']}")
            print(f"Source ID: {evidence['source_id']}")
            print(f"Locator: {evidence['locator']}")
        print(f"Record status: {row['reconstruction_status']}")
        print()


if __name__ == "__main__":
    main()
