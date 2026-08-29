#!/usr/bin/env python3
"""Report the sourced achievement ledger against explicit player state."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from build_kb import DEFAULT_DB, ROOT

DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"


def load_achievement_report(
    db_path: Path = DEFAULT_DB,
    state_path: Path = DEFAULT_STATE,
    include_unlocked: bool = False,
) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    unlocked = state.get("completion", {}).get("achievements_unlocked", [])
    if not isinstance(unlocked, list) or not all(isinstance(row, str) for row in unlocked):
        raise ValueError("completion.achievements_unlocked must be a list of strings")

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT a.*, r.target_type, r.target_key, r.required_count,
                r.source_id AS requirement_source_id,
                r.locator AS requirement_locator,
                r.confidence AS requirement_confidence,
                r.verification_status AS requirement_verification_status,
                s.title AS source_title, s.url AS source_url,
                rs.title AS requirement_source_title,
                rs.url AS requirement_source_url
            FROM achievements a JOIN sources s ON s.source_id=a.source_id
            LEFT JOIN achievement_requirements r USING(achievement_id)
            LEFT JOIN sources rs ON rs.source_id=r.source_id
            ORDER BY CASE a.grade
                WHEN 'bronze' THEN 1 WHEN 'silver' THEN 2
                WHEN 'gold' THEN 3 ELSE 4 END,
                a.category, a.name"""
        ).fetchall()
        semantic_rows = connection.execute(
            """SELECT c.claim_id, c.subject_key, c.predicate, c.value_json,
                c.scope_json, c.confidence, c.verification_status,
                c.locator, c.source_id, s.title AS source_title,
                s.url AS source_url
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key LIKE 'achievement:%'
              AND c.predicate LIKE 'achievement_counter_%'
            ORDER BY c.subject_key, c.predicate, c.claim_id"""
        ).fetchall()
        counter_conflict_rows = connection.execute(
            """SELECT c.conflict_key, c.status, c.rationale,
                c.resolution_claim_id, a.subject_key,
                c.claim_a_id, c.claim_b_id
            FROM conflicts c JOIN claims a ON a.claim_id=c.claim_a_id
            WHERE a.subject_key LIKE 'achievement:%'
            ORDER BY c.conflict_key"""
        ).fetchall()
        tablet_rows = connection.execute(
            "SELECT tablet_id, fragment_id FROM tablet_fragments ORDER BY tablet_id"
        ).fetchall()
        found_fragments = set(state.get("completion", {}).get("tablet_fragments", []))
        tablet_fragments: dict[str, set[str]] = {}
        for tablet_id, fragment_id in tablet_rows:
            tablet_fragments.setdefault(tablet_id, set()).add(fragment_id)
        assembled_tablets = sum(
            fragments.issubset(found_fragments)
            for fragments in tablet_fragments.values()
        )
        vicious_rows = connection.execute(
            "SELECT obligation_id, encounter_size FROM vicious_encounters"
        ).fetchall()
        completed_obligations = set(
            state.get("completion", {}).get("obligations_completed", [])
        )
        vicious_defeats = sum(
            encounter_size
            for obligation_id, encounter_size in vicious_rows
            if obligation_id in completed_obligations
        )
        known = {row["achievement_id"] for row in rows}
        vocation_rows = connection.execute(
            "SELECT vocation_id, tier FROM vocations"
        ).fetchall()
        vocation_tiers = {row["vocation_id"]: row["tier"] for row in vocation_rows}
        mastered_vocations = {
            vocation_id
            for member in state.get("party", {}).get("members", {}).values()
            if isinstance(member, dict)
            for vocation_id, mastered in member.get("vocation_mastery", {}).items()
            if mastered is True and vocation_id in vocation_tiers
        }
        unknown = sorted(set(unlocked) - known)
        result_rows = []
        semantics_by_achievement: dict[str, list[dict]] = {}
        semantic_claims: dict[str, dict] = {}
        for semantic_row in semantic_rows:
            semantic = dict(semantic_row)
            semantic["value"] = json.loads(semantic.pop("value_json"))
            semantic["scope"] = json.loads(semantic.pop("scope_json"))
            subject_id = semantic["subject_key"].removeprefix("achievement:")
            achievement_id = subject_id if subject_id.startswith("ach_") else f"ach_{subject_id}"
            semantics_by_achievement.setdefault(achievement_id, []).append(semantic)
            semantic_claims[semantic["claim_id"]] = semantic
        conflicts_by_achievement: dict[str, list[dict]] = {}
        for conflict_row in counter_conflict_rows:
            conflict = dict(conflict_row)
            subject_id = conflict["subject_key"].removeprefix("achievement:")
            achievement_id = subject_id if subject_id.startswith("ach_") else f"ach_{subject_id}"
            conflict["claims"] = [
                semantic_claims[claim_id]
                for claim_id in (conflict["claim_a_id"], conflict["claim_b_id"])
                if claim_id in semantic_claims
            ]
            conflict["resolution"] = semantic_claims.get(
                conflict["resolution_claim_id"]
            )
            conflicts_by_achievement.setdefault(achievement_id, []).append(conflict)
        for row in rows:
            item = dict(row)
            item["counter_semantics"] = semantics_by_achievement.get(
                item["achievement_id"], []
            )
            item["counter_conflicts"] = conflicts_by_achievement.get(
                item["achievement_id"], []
            )
            item["unlocked"] = item["achievement_id"] in unlocked
            progress = None
            basis = "No supported player-state counter has been recorded."
            completion = state.get("completion", {})
            if item["target_type"] == "mini_medal_registry":
                progress = completion.get("mini_medal_count")
                basis = "Explicit Mini Medal total."
                if progress is None:
                    found = completion.get("mini_medals_found", [])
                    progress = len(found) if isinstance(found, list) and found else None
                    basis = "Explicitly checked medal identities." if progress is not None else basis
            elif item["target_type"] == "item_registry":
                found = completion.get("items_obtained", [])
                progress = len(set(found)) if isinstance(found, list) and found else None
                basis = "Explicitly recorded Heroic Hoarder item identities."
            elif item["target_type"] == "checkpoint_obligation":
                done = completion.get("obligations_completed", [])
                progress = 1 if isinstance(done, list) and item["target_key"] in done else None
                basis = "Explicitly completed checkpoint obligation."
            elif item["target_type"] == "achievement_registry":
                recorded = len(set(unlocked) & known)
                progress = recorded if recorded else None
                basis = "Explicitly recorded achievement unlocks."
            elif item["target_type"] == "stone_tablet_registry":
                progress = assembled_tablets if found_fragments else None
                basis = "Whole tablets assembled from explicitly recorded fragment identities."
            elif item["target_type"] == "monster_registry":
                entries = completion.get("monster_entries", [])
                progress = len(set(entries)) if isinstance(entries, list) and entries else None
                basis = "Explicitly recorded Monster List identities."
            elif item["target_type"] == "vicious_registry":
                progress = vicious_defeats if vicious_defeats else None
                basis = "Vicious encounter sizes linked to explicitly completed obligations."
            elif item["target_type"] == "vocation_registry":
                progress = len(mastered_vocations) if mastered_vocations else None
                basis = "Distinct vocations explicitly mastered by at least one party member."
            elif item["target_type"] == "vocation_tier":
                tier = item["target_key"].removesuffix("_masteries")
                tier_count = sum(
                    vocation_tiers[vocation_id] == tier
                    for vocation_id in mastered_vocations
                )
                progress = tier_count if tier_count else None
                basis = f"Distinct explicitly mastered {tier} vocations."
            item["progress"] = progress
            if item["unlocked"]:
                progress_status = "complete"
                status_reason = "Achievement unlock is explicitly recorded."
            elif progress is None:
                progress_status = "unknown"
                status_reason = "No positive or exact counter is recorded; an empty tracker is not treated as zero."
            elif progress >= item["required_count"]:
                progress_status = "target_met"
                status_reason = "The explicit dependency count meets the published requirement; unlock is not recorded."
            else:
                progress_status = "partial"
                status_reason = "Some dependency progress is explicitly recorded."
            item["dependency_progress"] = {
                "status": progress_status,
                "known_count": progress,
                "required_count": item["required_count"],
                "basis": basis,
                "reason": status_reason,
                "target_type": item["target_type"],
                "target_key": item["target_key"],
            }
            if include_unlocked or not item["unlocked"]:
                result_rows.append(item)
    return {
        "total": len(rows),
        "unlocked_count": len(set(unlocked) & known),
        "achievements": result_rows,
        "unknown_state_ids": unknown,
    }


def print_achievement_report(report: dict, sources: bool = False) -> None:
    print(f"Achievements: {report['unlocked_count']}/{report['total']} explicitly recorded")
    if report["unknown_state_ids"]:
        print("Unknown saved IDs: " + ", ".join(report["unknown_state_ids"]))
    for row in report["achievements"]:
        mark = "DONE" if row["unlocked"] else "TODO"
        gate = row["completion_checkpoint_id"] or row["earliest_checkpoint_id"] or "unknown gate"
        progress = ""
        if row["required_count"] is not None:
            current = "?" if row["progress"] is None else row["progress"]
            progress = f" [{current}/{row['required_count']}]"
        print(f"- [{mark}] {row['name']}{progress} — {row['description']} ({gate})")
        if sources:
            print(f"  Source: {row['source_title']} — {row['source_url']} — {row['locator']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Include recorded achievements")
    parser.add_argument("--sources", action="store_true")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    print_achievement_report(
        load_achievement_report(args.db, args.state, args.all), args.sources
    )


if __name__ == "__main__":
    main()
