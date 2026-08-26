#!/usr/bin/env python3
"""Show every verified acquisition route for an item."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"


def load_item_routes(db_path: Path, item_query: str) -> tuple[dict, list[dict]]:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        item = connection.execute(
            """SELECT i.*, c.name AS category_name FROM items i
            JOIN item_categories c USING(category_id)
            WHERE i.item_id = ? OR lower(i.name) = lower(?)""",
            (item_query, item_query),
        ).fetchone()
        if item is None:
            raise ValueError(f"Unknown item: {item_query}")
        routes = connection.execute(
            """SELECT a.*, cp.name AS available_checkpoint,
                si.price, si.currency, sh.name AS shop_name,
                lp.venue AS panel_venue, lp.game_version AS panel_version,
                lp.panel_rank, s.title AS source_title, s.url AS source_url
            FROM item_acquisition_paths a
            LEFT JOIN checkpoints cp
              ON cp.checkpoint_id = a.available_from_checkpoint_id
            LEFT JOIN shop_inventory si USING(acquisition_id)
            LEFT JOIN shops sh ON sh.shop_id = si.shop_id
            LEFT JOIN lucky_panel_rewards lr USING(acquisition_id)
            LEFT JOIN lucky_panel_pools lp ON lp.pool_id = lr.pool_id
            JOIN sources s ON s.source_id = a.source_id
            WHERE a.item_id = ?
            ORDER BY cp.sequence_no, a.acquisition_id""",
            (item["item_id"],),
        ).fetchall()
        return dict(item), [dict(row) for row in routes]
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("item", help="Exact item name or stable item ID")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    try:
        item, routes = load_item_routes(args.db, args.item)
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error
    required = "required" if item["heroic_hoarder_required"] else "optional"
    print(f"{item['name']} ({item['category_name']}; Heroic Hoarder: {required})")
    for route in routes:
        detail = route["route_label"]
        if route["price"] is not None:
            detail += f" — {route['price']} {route['currency']}"
        print(
            f"- {route['method']}: {detail} "
            f"[from: {route['available_checkpoint'] or 'unknown'}; "
            f"supply: {route['supply_type']}]"
        )
        print(f"  Source: {route['source_title']} — {route['source_url']} ({route['locator']})")


if __name__ == "__main__":
    main()
