#!/usr/bin/env python3
"""List sourced Monster Hearts and their checkpoint-aware availability."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from build_kb import DEFAULT_DB


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"


def load_heart_report(db_path: Path, query: str | None = None,
                      checkpoint_id: str | None = None,
                      state_path: Path | None = None) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    entitlements = {}
    if state_path is not None:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        entitlements = state.get("dlc_entitlements", {})
        if not isinstance(entitlements, dict) or any(
            not isinstance(scope, str) or not isinstance(owned, bool)
            for scope, owned in entitlements.items()
        ):
            raise ValueError("dlc_entitlements must map DLC scope names to booleans")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        checkpoint_sequence = None
        if checkpoint_id:
            checkpoint = connection.execute(
                "SELECT sequence_no, name FROM checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            ).fetchone()
            if checkpoint is None:
                raise ValueError(f"Unknown checkpoint: {checkpoint_id}")
            checkpoint_sequence = checkpoint["sequence_no"]
            checkpoint_name = checkpoint["name"]
        else:
            checkpoint_name = None
        rows = [dict(row) for row in connection.execute(
            """SELECT h.*, cp.name AS available_checkpoint,
                cp.sequence_no AS available_sequence,
                s.title AS source_title, s.url AS source_url,
                avs.title AS availability_source_title,
                avs.url AS availability_source_url
            FROM monster_hearts h
            LEFT JOIN checkpoints cp ON cp.checkpoint_id=h.available_from_checkpoint_id
            JOIN sources s USING(source_id)
            LEFT JOIN sources avs ON avs.source_id=h.availability_source_id
            ORDER BY h.name"""
        )]
        route_rows = connection.execute(
            """SELECT lower(i.name) AS heart_name,
                a.available_from_checkpoint_id, cp.name AS available_checkpoint,
                cp.sequence_no AS available_sequence, a.route_label,
                a.locator AS availability_locator,
                s.title AS availability_source_title,
                s.url AS availability_source_url
            FROM item_acquisition_paths a
            JOIN items i USING(item_id)
            JOIN sources s USING(source_id)
            LEFT JOIN checkpoints cp
              ON cp.checkpoint_id=a.available_from_checkpoint_id
            WHERE lower(i.name) LIKE '% heart'
            ORDER BY lower(i.name), COALESCE(cp.sequence_no, 999999),
                a.acquisition_id"""
        ).fetchall()
        earliest_routes = {}
        for route in route_rows:
            earliest_routes.setdefault(route["heart_name"], dict(route))
        for row in rows:
            route = earliest_routes.get(row["name"].casefold())
            if row["available_from_checkpoint_id"]:
                row["availability_status"] = "heart_gate"
            elif route and route["available_from_checkpoint_id"]:
                row["available_from_checkpoint_id"] = route["available_from_checkpoint_id"]
                row["available_checkpoint"] = route["available_checkpoint"]
                row["available_sequence"] = route["available_sequence"]
                row["availability_source_title"] = route["availability_source_title"]
                row["availability_source_url"] = route["availability_source_url"]
                row["availability_locator"] = route["availability_locator"]
                row["availability_notes"] = (
                    row["availability_notes"]
                    or f"Earliest normalized item route: {route['route_label']}."
                )
                row["availability_status"] = "route_normalized"
            else:
                row["availability_status"] = "unknown"
        if query:
            needle = query.casefold()
            rows = [row for row in rows if needle in row["name"].casefold()
                    or needle == row["heart_id"].casefold()]
            if not rows:
                raise ValueError(f"Unknown Monster Heart: {query}")
        for row in rows:
            entitlement = entitlements.get(row["dlc_scope"]) if row["dlc_scope"] else None
            row["dlc_ownership_status"] = (
                "owned" if entitlement is True else
                "not_owned" if entitlement is False else
                "unknown" if row["dlc_scope"] else "not_applicable"
            )
            if checkpoint_sequence is None or row["available_sequence"] is None:
                row["available_now"] = None
            else:
                row["available_now"] = row["available_sequence"] <= checkpoint_sequence
            if row["dlc_scope"] and row["dlc_ownership_status"] != "owned":
                row["available_now"] = (
                    False if row["dlc_ownership_status"] == "not_owned" else None
                )
                row["availability_status"] = "requires_dlc_ownership_confirmation"
        return {
            "checkpoint_id": checkpoint_id,
            "checkpoint_name": checkpoint_name,
            "hearts": rows,
            "verified_available": sum(row["available_now"] is True for row in rows),
            "unknown_availability": sum(row["available_now"] is None for row in rows),
        }
    finally:
        connection.close()


def print_heart_report(report: dict, include_sources: bool = False) -> None:
    if report["checkpoint_name"]:
        print(f"Monster Hearts at {report['checkpoint_name']}:")
    else:
        print("Monster Hearts:")
    for row in report["hearts"]:
        if row["dlc_ownership_status"] == "unknown":
            gate = f"requires {row['dlc_scope']} ownership confirmation"
        elif row["dlc_ownership_status"] == "not_owned":
            gate = f"{row['dlc_scope']} reported not owned"
        elif row["available_now"] is True:
            gate = f"available from {row['available_checkpoint']}"
        elif row["available_now"] is False:
            gate = f"later: {row['available_checkpoint']}"
        else:
            gate = "availability not yet established"
        print(f"- {row['name']} — {row['effect_text']} ({gate})")
        if row["availability_notes"]:
            print(f"  Note: {row['availability_notes']}")
        if include_sources:
            print(f"  Effect: {row['source_title']} — {row['source_url']} ({row['locator']})")
            if row["availability_source_url"]:
                print("  Availability: "
                      f"{row['availability_source_title']} — "
                      f"{row['availability_source_url']} "
                      f"({row['availability_locator']})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("heart", nargs="?", help="Heart name or stable ID")
    parser.add_argument("--checkpoint", help="Compare verified availability with this checkpoint")
    parser.add_argument("--sources", action="store_true")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    try:
        print_heart_report(
            load_heart_report(args.db, args.heart, args.checkpoint, args.state), args.sources
        )
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
