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
            WHERE i.item_id = ? OR lower(i.name) = lower(?)
               OR EXISTS (
                   SELECT 1 FROM item_aliases ia
                   WHERE ia.item_id = i.item_id AND lower(ia.alias) = lower(?)
               )""",
            (item_query, item_query, item_query),
        ).fetchone()
        if item is None:
            raise ValueError(f"Unknown item: {item_query}")
        routes = connection.execute(
            """SELECT a.*, cp.name AS available_checkpoint,
                si.price, si.currency, sh.name AS shop_name,
                lp.venue AS panel_venue, lp.game_version AS panel_version,
                lp.panel_rank, lp.entry_cost AS panel_entry_cost,
                lp.currency AS panel_currency,
                cp.sequence_no AS available_sequence,
                expiry.name AS unavailable_checkpoint,
                expiry.sequence_no AS unavailable_sequence,
                s.title AS source_title, s.url AS source_url
            FROM item_acquisition_paths a
            LEFT JOIN checkpoints cp
              ON cp.checkpoint_id = a.available_from_checkpoint_id
            LEFT JOIN checkpoints expiry
              ON expiry.checkpoint_id = a.unavailable_after_checkpoint_id
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


def load_purchase_advice(
    db_path: Path, item_query: str, checkpoint_id: str
) -> tuple[dict, list[dict], str]:
    item, routes = load_item_routes(db_path, item_query)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        checkpoint = connection.execute(
            "SELECT sequence_no FROM checkpoints WHERE checkpoint_id = ?",
            (checkpoint_id,),
        ).fetchone()
        route_conflicts = connection.execute(
            """SELECT DISTINCT a.predicate
            FROM conflicts c
            JOIN claims a ON a.claim_id = c.claim_a_id
            WHERE c.status = 'unresolved'
              AND a.subject_key = ?
              AND a.predicate IN (
                  'acquisition_exclusivity',
                  'precise_location_description',
                  'treasure_availability'
              )""",
            (item["canonical_key"],),
        ).fetchall()
    finally:
        connection.close()
    if checkpoint is None:
        raise ValueError(f"Unknown checkpoint: {checkpoint_id}")
    current_sequence = checkpoint["sequence_no"]
    for route in routes:
        available = route["available_sequence"]
        unavailable = route["unavailable_sequence"]
        if available is None:
            route["timing_status"] = "unknown_gate"
        elif unavailable is not None and unavailable < available:
            route["timing_status"] = "invalid_window"
        elif unavailable is not None and unavailable < current_sequence:
            route["timing_status"] = "expired"
        elif available <= current_sequence:
            route["timing_status"] = "available_now"
        else:
            route["timing_status"] = "available_later"

        if route["is_free"] == 1:
            route["cost_status"] = "free"
        elif route["is_free"] == 0:
            route["cost_status"] = "paid"
        elif route["method"] == "shop" and route["price"] is not None:
            route["cost_status"] = "free" if route["price"] == 0 else "paid"
        elif route["method"] == "lucky_panel" and route["panel_entry_cost"] is not None:
            route["cost_status"] = (
                "free" if route["panel_entry_cost"] == 0 else "paid"
            )
        else:
            route["cost_status"] = "unknown"

    if route_conflicts:
        predicates = ", ".join(row["predicate"] for row in route_conflicts)
        verdict = (
            "UNRESOLVED — acquisition evidence conflict requires review: "
            + predicates
        )
    elif any(
        row["cost_status"] == "free" and row["timing_status"] == "available_now"
        for row in routes
    ):
        verdict = "DON'T BUY FOR COMPLETION — verified free route available now"
    else:
        later_free = [
            row for row in routes
            if row["cost_status"] == "free"
            and row["timing_status"] == "available_later"
        ]
        if later_free:
            earliest = min(later_free, key=lambda row: row["available_sequence"])
            verdict = (
                "CAN WAIT — verified free route later at "
                f"{earliest['available_checkpoint']}"
            )
        elif any(
            row["cost_status"] == "unknown"
            or row["timing_status"] in ("unknown_gate", "invalid_window")
            for row in routes
        ):
            verdict = "UNRESOLVED — no verified free route; incomplete cost or timing data"
        else:
            verdict = "NO VERIFIED FREE ROUTE — buy if needed for completion or immediate power"
    return item, routes, verdict


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("item", help="Exact item name or stable item ID")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--at-checkpoint", help="Add buy-now versus free-later advice")
    args = parser.parse_args()
    try:
        if args.at_checkpoint:
            item, routes, verdict = load_purchase_advice(
                args.db, args.item, args.at_checkpoint
            )
        else:
            item, routes = load_item_routes(args.db, args.item)
            verdict = None
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error
    required = "required" if item["heroic_hoarder_required"] else "optional"
    print(f"{item['name']} ({item['category_name']}; Heroic Hoarder: {required})")
    if verdict:
        print("Advice: " + verdict)
        print("Tradeoff: waiting may save currency but can defer an immediate power increase.")
    for route in routes:
        detail = route["route_label"]
        if route["price"] is not None:
            detail += f" — {route['price']} {route['currency']}"
        print(
            f"- {route['method']}: {detail} "
            f"[from: {route['available_checkpoint'] or 'unknown'}; "
            f"supply: {route['supply_type']}]"
        )
        if args.at_checkpoint:
            print(
                f"  Timing: {route['timing_status']}; cost: {route['cost_status']}; "
                f"prerequisites: {route['prerequisite_json']}"
            )
        print(f"  Source: {route['source_title']} — {route['source_url']} ({route['locator']})")


if __name__ == "__main__":
    main()
