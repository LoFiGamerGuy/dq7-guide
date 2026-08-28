#!/usr/bin/env python3
"""Show explicit party vocation mastery and remaining Master of All work."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from build_kb import DEFAULT_DB, ROOT

DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"


def load_vocation_details(db_path: Path, query: str) -> dict:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        vocation = connection.execute(
            """SELECT v.*, e.name FROM vocations v
            JOIN entities e ON e.entity_id = v.vocation_id
            WHERE v.vocation_id = ? OR lower(e.name) = lower(?)""",
            (query, query),
        ).fetchone()
        if vocation is None:
            raise ValueError(f"Unknown vocation: {query}")
        skills = connection.execute(
            """SELECT vs.*, s.title AS source_title, s.url AS source_url
            FROM vocation_rank_skills vs JOIN sources s USING(source_id)
            WHERE vs.vocation_id = ?
            ORDER BY vs.proficiency_rank, vs.vocation_skill_id""",
            (vocation["vocation_id"],),
        ).fetchall()
        perks = connection.execute(
            """SELECT vp.*, s.title AS source_title, s.url AS source_url
            FROM vocation_perks vp JOIN sources s USING(source_id)
            WHERE vp.vocation_id = ? ORDER BY vp.perk_type, vp.perk_name""",
            (vocation["vocation_id"],),
        ).fetchall()
        requirements = connection.execute(
            """SELECT vr.*, e.name AS prerequisite_name,
                s.title AS source_title, s.url AS source_url
            FROM vocation_requirements vr
            JOIN entities e ON e.entity_id = vr.prerequisite_vocation_id
            JOIN sources s USING(source_id)
            WHERE vr.vocation_id = ?
            ORDER BY vr.group_id, e.name""",
            (vocation["vocation_id"],),
        ).fetchall()
        return {
            "vocation": dict(vocation),
            "skills": [dict(row) for row in skills],
            "perks": [dict(row) for row in perks],
            "requirements": [dict(row) for row in requirements],
        }
    finally:
        connection.close()


def print_vocation_details(report: dict, include_sources: bool = False) -> None:
    vocation = report["vocation"]
    print(f"{vocation['name']} ({vocation['tier']})")
    if report["requirements"]:
        groups: dict[str, list[dict]] = {}
        for row in report["requirements"]:
            groups.setdefault(row["group_id"], []).append(row)
        for rows in groups.values():
            rule = rows[0]["rule"]
            names = ", ".join(row["prerequisite_name"] for row in rows)
            if rule == "all_of":
                print(f"Unlock: master all — {names}")
            else:
                print(f"Unlock: master any {rows[0]['required_count']} — {names}")
            if include_sources:
                print(f"  Source: {rows[0]['source_title']} — {rows[0]['source_url']}")
    if report["skills"]:
        for row in report["skills"]:
            print(f"{row['proficiency_rank']}★ {row['skill_name']} — {row['skill_description']}")
            if include_sources:
                print(f"  Source: {row['source_title']} — {row['source_url']} ({row['locator']})")
    else:
        print("Skills: not normalized yet")
    for row in report["perks"]:
        print(f"Let Loose: {row['perk_name']} — {row['perk_description']}")
        if include_sources:
            print(f"  Source: {row['source_title']} — {row['source_url']} ({row['locator']})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--vocation", help="Show skills for an exact vocation name or ID")
    parser.add_argument("--sources", action="store_true")
    args = parser.parse_args()
    if args.vocation:
        try:
            print_vocation_details(
                load_vocation_details(args.db, args.vocation), args.sources
            )
        except (FileNotFoundError, ValueError) as error:
            raise SystemExit(str(error)) from error
        return
    state = json.loads(args.state.read_text(encoding="utf-8"))
    members = state.get("party", {}).get("members", {})
    with sqlite3.connect(args.db) as connection:
        rows = connection.execute(
            """SELECT v.vocation_id, e.name, v.tier
            FROM vocations v JOIN entities e ON e.entity_id = v.vocation_id
            ORDER BY v.tier, e.name"""
        ).fetchall()
    mastered_by: dict[str, list[str]] = {}
    for character, member in members.items():
        for vocation_id, mastered in member.get("vocation_mastery", {}).items():
            if mastered is True:
                mastered_by.setdefault(vocation_id, []).append(character)
    mastered = [row for row in rows if row[0] in mastered_by]
    remaining = [row for row in rows if row[0] not in mastered_by]
    print(f"Master of All: {len(mastered)}/{len(rows)} vocations explicitly mastered")
    if mastered:
        print("Mastered: " + ", ".join(
            f"{name} ({'/'.join(mastered_by[vocation_id])})"
            for vocation_id, name, _tier in mastered
        ))
    print("Remaining: " + (", ".join(name for _id, name, _tier in remaining) or "none"))


if __name__ == "__main__":
    main()
