#!/usr/bin/env python3
"""Dependency-free local JSON API and static server for the DQ7 guide."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import secrets
import signal
import socket
import sqlite3
import threading
import tempfile
from urllib.parse import parse_qs, unquote, urlparse
import webbrowser

from achievement_report import load_achievement_report
from checkpoint_report import load_report
from conflict_report import load_conflicts
from early_walkthrough import DEFAULT_FROM, DEFAULT_THROUGH, load_walkthrough
from hoarder_report import load_hoarder_report
from item_report import load_item_routes
from monster_report import load_monster_coverage, load_monster_report
from player_progress import _load_state, _save_state, update_progress
from vocation_report import load_vocation_details


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"
DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"
DEFAULT_STATIC = ROOT / "web"
DEFAULT_EVIDENCE_GAPS = ROOT / "data" / "evidence_gaps.json"
MAX_BODY_BYTES = 64 * 1024
ALLOWED_PROGRESS_COMMANDS = {
    "checkpoint", "medal-found", "medal-undo", "medal-count", "done", "undo",
    "achievement-unlocked", "achievement-undo", "item-obtained", "item-undo",
    "tablet-found", "tablet-undo", "monster-defeated", "monster-undo",
    "heart-obtained", "heart-undo",
    "vocation-mastered", "vocation-undo",
    "party-level", "party-vocations", "party-setup",
    "missable-completed", "missable-undo",
    "accessory-set",
}


def _default_pairing_file() -> Path:
    config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_root / "dq7-guide" / "phone-pairing-token"


def _load_or_create_pairing_token(path: Path, rotate: bool = False) -> str:
    """Load a private durable LAN credential, creating or rotating atomically."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    if path.is_symlink():
        raise ValueError(f"Pairing token path must not be a symlink: {path}")
    if path.exists() and not rotate:
        token = path.read_text(encoding="ascii").strip()
        if len(token) < 24 or any(not (char.isalnum() or char in "-_") for char in token):
            raise ValueError("Stored phone pairing token is invalid; restart with --rotate-pairing")
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return token
    token = secrets.token_urlsafe(24)
    temporary = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".phone-pairing-", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            handle.write(token + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        temporary.replace(path)
        path.chmod(0o600)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return token


def _lan_addresses() -> list[str]:
    """Return usable local IPv4 addresses without sending network traffic."""
    addresses: set[str] = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 80))
            addresses.add(probe.getsockname()[0])
    except OSError:
        pass
    try:
        for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addresses.add(result[4][0])
    except OSError:
        pass
    return sorted(address for address in addresses
                  if address and not address.startswith("127."))


def _access_urls(host: str, port: int, pairing_token: str | None = None) -> tuple[str, list[str]]:
    """Return the same-device URL and any practical phone URLs."""
    local_url = f"http://127.0.0.1:{port}"
    suffix = f"/?pair={pairing_token}#walkthrough" if pairing_token else ""
    phone_urls = ([f"http://{address}:{port}{suffix}" for address in _lan_addresses()]
                  if host in {"0.0.0.0", "::"} else [])
    return local_url, phone_urls


def _client_error_status(error: Exception) -> HTTPStatus:
    return (HTTPStatus.NOT_FOUND if str(error).startswith("Unknown ")
            else HTTPStatus.BAD_REQUEST)


def _checkpoints(db_path: Path) -> list[dict]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(
            """SELECT checkpoint_id, sequence_no, name, time_period, region,
                safe_exit_condition, coverage_status
            FROM checkpoints ORDER BY sequence_no"""
        )]


def _rows(db_path: Path, sql: str, parameters: tuple = ()) -> list[dict]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(sql, parameters)]


def _state(state_path: Path) -> dict:
    return json.loads(state_path.read_text(encoding="utf-8"))


def _advice_applicability(db_path: Path, state: dict, applicability: dict) -> dict:
    checks = []
    requires = applicability.get("requires") if isinstance(applicability.get("requires"), dict) else {}
    required_medals = requires.get("mini_medals")
    if isinstance(required_medals, int) and not isinstance(required_medals, bool):
        explicit_count = state.get("completion", {}).get("mini_medal_count")
        numbered = len(state.get("completion", {}).get("mini_medals_found", []))
        if isinstance(explicit_count, int) and not isinstance(explicit_count, bool):
            if max(explicit_count, numbered) >= required_medals:
                checks.append(("satisfied", f"Mini Medals: {max(explicit_count, numbered)}/{required_medals} explicitly recorded"))
            elif numbered > explicit_count:
                checks.append(("unknown", f"Mini Medal records disagree ({explicit_count} total; {numbered} numbered; {required_medals} needed)"))
            else:
                checks.append(("unmet", f"Mini Medals: {explicit_count}/{required_medals} explicitly recorded"))
        elif numbered >= required_medals:
            checks.append(("satisfied", f"Mini Medals: {numbered}/{required_medals} numbered medals recorded"))
        else:
            checks.append(("unknown", f"Mini Medal count unknown ({numbered} numbered recorded; {required_medals} needed)"))
    unsupported_requires = sorted(key for key in requires if key != "mini_medals")
    if unsupported_requires:
        checks.append(("unknown", "Saved state does not track " + ", ".join(key.replace("_", " ") for key in unsupported_requires)))
    vocation_name = applicability.get("vocation")
    if isinstance(vocation_name, str):
        with sqlite3.connect(db_path) as connection:
            row = connection.execute(
                """SELECT v.vocation_id FROM vocations v JOIN entities e
                ON e.entity_id=v.vocation_id WHERE lower(e.name)=lower(?)""",
                (vocation_name,),
            ).fetchone()
        if row:
            vocation_id = row[0]
            matches = []
            for name, member in state.get("party", {}).get("members", {}).items():
                if vocation_id in (member.get("primary_vocation"), member.get("secondary_vocation")):
                    matches.append(f"{name} current")
                elif member.get("vocation_mastery", {}).get(vocation_id) is True:
                    matches.append(f"{name} mastered")
            checks.append(("satisfied", f"{vocation_name}: {', '.join(matches)}") if matches
                          else ("unknown", f"No explicit current/mastered {vocation_name} recorded"))
        else:
            checks.append(("unknown", f"Vocation gate is not normalized: {vocation_name}"))
    if not checks:
        return {"status": "unknown", "reason": "No supported saved-state gate"}
    statuses = {status for status, _ in checks}
    status = "unmet" if "unmet" in statuses else "unknown" if "unknown" in statuses else "satisfied"
    return {"status": status, "reason": "; ".join(reason for _, reason in checks)}


def _page(rows: list[dict], query: dict, searchable: tuple[str, ...]) -> dict:
    term = query.get("q", [""])[0].strip().casefold()
    if term:
        rows = [row for row in rows if any(term in str(row.get(key, "")).casefold()
                                          for key in searchable)]
    try:
        limit = min(max(int(query.get("limit", [50])[0]), 1), 200)
        offset = max(int(query.get("offset", [0])[0]), 0)
    except ValueError as error:
        raise ValueError("limit and offset must be integers") from error
    return {"total": len(rows), "limit": limit, "offset": offset,
            "results": rows[offset:offset + limit]}


def _items(db_path: Path, state_path: Path, query: dict) -> dict:
    obtained = set(_state(state_path).get("completion", {}).get("items_obtained", []))
    rows = _rows(db_path, """SELECT i.item_id, i.name, i.category_id,
        c.name AS category, i.heroic_hoarder_required, i.heroic_hoarder_ordinal
        FROM items i JOIN item_categories c USING(category_id) ORDER BY i.name""")
    for row in rows:
        row["obtained"] = row["item_id"] in obtained
    page = _page(rows, query, ("item_id", "name", "category"))
    page["items"] = page.pop("results")
    return page


def _vocations(db_path: Path, state_path: Path, query: dict) -> dict:
    members = _state(state_path).get("party", {}).get("members", {})
    rows = _rows(db_path, """SELECT v.vocation_id, e.name, v.tier, v.exclusive_character
        FROM vocations v JOIN entities e ON e.entity_id=v.vocation_id
        ORDER BY v.tier, e.name""")
    for row in rows:
        row["mastered_by"] = sorted(name for name, member in members.items()
            if member.get("vocation_mastery", {}).get(row["vocation_id"]) is True)
    page = _page(rows, query, ("vocation_id", "name", "tier", "exclusive_character"))
    page["vocations"] = page.pop("results")
    return page


def _vocation_unlock_progress(db_path: Path, state_path: Path,
                              vocation_id: str) -> dict:
    """Describe direct sourced prerequisites without treating absent state as false."""
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        requirements = [dict(row) for row in connection.execute(
            """SELECT r.group_id, r.rule, r.required_count,
            r.prerequisite_vocation_id, e.name AS prerequisite_name,
            r.source_id, s.title AS source_title, s.url AS source_url, r.locator
            FROM vocation_requirements r
            JOIN entities e ON e.entity_id=r.prerequisite_vocation_id
            JOIN sources s USING(source_id)
            WHERE r.vocation_id=? ORDER BY r.group_id, e.name""", (vocation_id,))]
        progression = connection.execute(
            """SELECT progression_mode, normalized_total_points,
                first_numeric_rank, last_numeric_rank, notes
            FROM vocation_progression_profiles WHERE vocation_id=?""",
            (vocation_id,),
        ).fetchone()
    cost_summary = ({"cost_status": "verified", "cost_profile": dict(progression),
                     "cost_note": progression["notes"]}
                    if progression else
                    {"cost_status": "unknown", "cost_profile": None,
                     "cost_note": "No verified progression profile."})
    recursive_plans = _vocation_recursive_plans(db_path, state_path, vocation_id)
    if not requirements:
        return {"status": "no_prerequisites", "groups": [], "party_progress": [],
                "recursive_plans": recursive_plans, **cost_summary}
    groups = []
    for group_id in dict.fromkeys(row["group_id"] for row in requirements):
        rows = [row for row in requirements if row["group_id"] == group_id]
        groups.append({"group_id": group_id, "rule": rows[0]["rule"],
            "required_count": rows[0]["required_count"],
            "candidates": [{"vocation_id": row["prerequisite_vocation_id"],
                "name": row["prerequisite_name"]} for row in rows],
            "source_id": rows[0]["source_id"],
            "source_title": rows[0]["source_title"],
            "source_url": rows[0]["source_url"], "locator": rows[0]["locator"]})
    progress = []
    members = _state(state_path).get("party", {}).get("members", {})
    direct_ids = {candidate["vocation_id"] for group in groups
                  for candidate in group["candidates"]}
    for name, member in members.items():
        mastered = {key for key, value in member.get("vocation_mastery", {}).items()
                    if value is True}
        group_progress = []
        for group in groups:
            candidate_ids = {row["vocation_id"] for row in group["candidates"]}
            known = sorted(candidate_ids & mastered)
            required = group["required_count"]
            group_progress.append({"group_id": group["group_id"],
                "status": "satisfied" if len(known) >= required else "unknown",
                "known_mastered": known,
                "unknown_mastery": sorted(candidate_ids - mastered),
                "required_count": required,
                "needed_if_unknowns_are_unmastered": max(required - len(known), 0)})
        progress.append({"party_member": name,
            "status": "satisfied" if all(row["status"] == "satisfied"
                                           for row in group_progress) else "unknown",
            "groups": group_progress})
    return {"status": "sourced_direct_prerequisites", "groups": groups,
        "party_progress": progress,
        "recursive_plans": recursive_plans,
        **cost_summary,
        "direct_prerequisite_ids": sorted(direct_ids)}


def _vocation_recursive_plans(db_path: Path, state_path: Path,
                              target_id: str) -> list[dict]:
    """Expand the sourced prerequisite DAG without selecting among alternatives."""
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        vocation_rows = connection.execute(
            """SELECT v.vocation_id, e.name, v.tier, v.exclusive_character
            FROM vocations v JOIN entities e ON e.entity_id=v.vocation_id"""
        ).fetchall()
        requirement_rows = connection.execute(
            """SELECT r.vocation_id, r.group_id, r.rule, r.required_count,
                r.prerequisite_vocation_id, r.source_id, s.title AS source_title,
                s.url AS source_url, r.locator
            FROM vocation_requirements r JOIN sources s USING(source_id)
            ORDER BY r.group_id, r.prerequisite_vocation_id"""
        ).fetchall()
        progression_rows = connection.execute(
            """SELECT vocation_id, progression_mode, normalized_total_points,
                first_numeric_rank, last_numeric_rank
            FROM vocation_progression_profiles"""
        ).fetchall()
    vocations = {row["vocation_id"]: dict(row) for row in vocation_rows}
    if target_id not in vocations:
        raise ValueError(f"Unknown vocation: {target_id}")
    grouped: dict[str, list[dict]] = {}
    for row in requirement_rows:
        grouped.setdefault(row["vocation_id"], []).append(dict(row))
    progression = {row["vocation_id"]: dict(row) for row in progression_rows}
    members = _state(state_path).get("party", {}).get("members", {})
    plans = []
    for character, member in members.items():
        mastered = {key for key, value in member.get("vocation_mastery", {}).items()
                    if value is True}
        next_options: dict[str, dict] = {}

        def expand(vocation_id: str, ancestry: set[str]) -> dict:
            vocation = vocations[vocation_id]
            if vocation_id in ancestry:
                raise ValueError(f"Vocation prerequisite cycle at {vocation_id}")
            eligible = vocation["exclusive_character"] in (None, character)
            rows = grouped.get(vocation_id, [])
            groups = []
            all_direct_satisfied = True
            for group_id in dict.fromkeys(row["group_id"] for row in rows):
                members_of_group = [row for row in rows if row["group_id"] == group_id]
                candidates = [expand(row["prerequisite_vocation_id"], ancestry | {vocation_id})
                              for row in members_of_group]
                known = sum(candidate["mastery_status"] == "mastered"
                            for candidate in candidates)
                required = members_of_group[0]["required_count"]
                satisfied = known >= required
                all_direct_satisfied = all_direct_satisfied and satisfied
                groups.append({"group_id": group_id,
                    "rule": members_of_group[0]["rule"],
                    "required_count": required, "explicitly_mastered_count": known,
                    "status": "satisfied" if satisfied else "unknown",
                    "candidates": candidates,
                    "source": {"id": members_of_group[0]["source_id"],
                        "title": members_of_group[0]["source_title"],
                        "url": members_of_group[0]["source_url"],
                        "locator": members_of_group[0]["locator"]}})
            mastery_status = "mastered" if vocation_id in mastered else "unknown"
            direct_status = ("ineligible" if not eligible else "no_prerequisites"
                             if not rows else "satisfied" if all_direct_satisfied else "unknown")
            if eligible and mastery_status != "mastered" and direct_status in (
                    "no_prerequisites", "satisfied"):
                next_options[vocation_id] = {"vocation_id": vocation_id,
                    "name": vocation["name"], "tier": vocation["tier"],
                    "readiness": ("base_candidate" if not rows else
                                  "direct_prerequisites_explicitly_mastered"),
                    "progression": progression.get(vocation_id),
                    "caveat": "Unrecorded game progress remains unknown."}
            return {"vocation_id": vocation_id, "name": vocation["name"],
                "tier": vocation["tier"], "eligible_for_character": eligible,
                "mastery_status": mastery_status,
                "direct_prerequisite_status": direct_status, "groups": groups}

        tree = expand(target_id, set())
        plans.append({"character": character,
            "status": "target_mastered" if target_id in mastered else
                      "ineligible" if not tree["eligible_for_character"] else "planning",
            "target": tree,
            "next_options": sorted(next_options.values(), key=lambda row: (row["tier"], row["name"])),
            "choice_policy": "All legal next options are shown; any_n_of branches are not ranked or silently selected.",
            "cost_status": "verified" if target_id in progression else "unknown",
            "cost_profile": progression.get(target_id)})
    return plans


def _monsters(db_path: Path, state_path: Path, query: dict) -> dict:
    defeated = set(_state(state_path).get("completion", {}).get("monster_entries", []))
    rows = _rows(db_path, """SELECT m.monster_id, m.source_ordinal, m.english_name,
        m.family, COUNT(DISTINCT e.encounter_id) AS route_count,
        COUNT(DISTINCT d.drop_id) AS drop_count
        FROM monsters m LEFT JOIN monster_encounters e USING(monster_id)
        LEFT JOIN monster_drops d USING(monster_id)
        GROUP BY m.monster_id ORDER BY m.source_ordinal""")
    for row in rows:
        row["defeated"] = row["monster_id"] in defeated
    page = _page(rows, query, ("monster_id", "source_ordinal", "english_name", "family"))
    page["monsters"] = page.pop("results")
    return page


def _equipment_readiness(db_path: Path, state_path: Path) -> dict:
    """Compare explicit gear state with sourced checkpoint advice without validating it."""
    state = _state(state_path)
    checkpoint_id = state.get("story", {}).get("checkpoint_id")
    members = state.get("party", {}).get("members", {})
    result = {
        "editor_supported": False,
        "accessory_editor_supported": True,
        "comparison_scope": "current_checkpoint_attributed_recommendations",
        "checkpoint_id": checkpoint_id,
        "gaps": [
            "Only two-source-agreeing compatibility rows are normalized; disputed and single-source rows remain read-only.",
            "Duplicate accessory/Heart equip and effect-stacking behavior has only one current-version source and is not normalized.",
            "One-each weapon, shield, head, and torso slot counts lack direct two-source evidence.",
            "Three compatibility rows conflict and two armour rows remain single-source.",
        ],
        "mechanics": [],
        "compatibility_coverage": {
            "verified_item_character_pairs": 0,
            "conflicted_item_rows": 0,
            "status": "partial_two_source_matrix",
        },
        "compatibility_audits": [],
        "members": [],
        "recommendations": [],
    }
    for name, member in members.items():
        equipment = member.get("equipment", {})
        result["members"].append({
            "name": name,
            "status": "unknown" if not equipment else "unvalidated_record",
            "recorded_equipment": equipment if isinstance(equipment, dict) else {},
            "note": ("No equipment explicitly recorded." if not equipment else
                     "Recorded values are displayed only; compatibility has not been validated."),
        })
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        result["mechanics"] = [dict(row) for row in connection.execute(
            """SELECT r.rule_id, r.rule_type, r.slot_name, r.numeric_value,
                r.applies_to, r.confidence, r.verification_status,
                r.locator, r.corroborating_locator,
                s.source_id, s.title AS source_title, s.url AS source_url,
                cs.source_id AS corroborating_source_id,
                cs.title AS corroborating_source_title,
                cs.url AS corroborating_source_url
            FROM equipment_rules r
            JOIN sources s ON s.source_id=r.source_id
            JOIN sources cs ON cs.source_id=r.corroborating_source_id
            ORDER BY r.rule_id"""
        )]
        audit_rows = [dict(row) for row in connection.execute(
            """SELECT a.audit_id, a.item_id, i.name AS item_name,
                c.name AS category, a.source_display_name, a.mapping_status,
                a.agreement_status, a.allowed_characters_json,
                a.source_a_characters_json, a.source_b_characters_json,
                a.source_c_characters_json,
                a.confidence, a.verification_status, a.notes,
                a.source_a_locator, a.source_b_locator, a.source_c_locator,
                a.mapping_locator,
                sa.title AS source_a_title, sa.url AS source_a_url,
                sb.title AS source_b_title, sb.url AS source_b_url,
                sc.title AS source_c_title, sc.url AS source_c_url,
                sm.title AS mapping_source_title, sm.url AS mapping_source_url
            FROM equipment_compatibility_audits a
            LEFT JOIN items i ON i.item_id=a.item_id
            LEFT JOIN item_categories c ON c.category_id=i.category_id
            JOIN sources sa ON sa.source_id=a.source_a_id
            LEFT JOIN sources sb ON sb.source_id=a.source_b_id
            LEFT JOIN sources sc ON sc.source_id=a.source_c_id
            LEFT JOIN sources sm ON sm.source_id=a.mapping_source_id
            ORDER BY c.heroic_hoarder_order, i.heroic_hoarder_ordinal, i.name"""
        )]
        for row in audit_rows:
            for field in ("allowed_characters_json", "source_a_characters_json",
                          "source_b_characters_json", "source_c_characters_json"):
                row[field.removesuffix("_json")] = (
                    json.loads(row.pop(field)) if row[field] is not None else None
                )
        result["compatibility_audits"] = audit_rows
        states = {status: sum(row["agreement_status"] == status for row in audit_rows)
                  for status in ("two_source_agreement", "source_disagreement", "single_source")}
        catalog_rows = [dict(row) for row in connection.execute(
            """SELECT c.name AS category, COUNT(*) AS catalog_item_rows,
                SUM(CASE WHEN a.item_id IS NOT NULL THEN 1 ELSE 0 END) AS audited_item_rows,
                SUM(CASE WHEN a.agreement_status='two_source_agreement' THEN 1 ELSE 0 END) AS verified_item_rows,
                SUM(CASE WHEN a.agreement_status='source_disagreement' THEN 1 ELSE 0 END) AS conflicted_item_rows,
                SUM(CASE WHEN a.agreement_status='single_source' THEN 1 ELSE 0 END) AS single_source_item_rows,
                SUM(CASE WHEN a.item_id IS NULL THEN 1 ELSE 0 END) AS unaudited_item_rows
            FROM item_categories c JOIN items i USING(category_id)
            LEFT JOIN equipment_compatibility_audits a USING(item_id)
            LEFT JOIN item_identity_redirects redirect ON redirect.legacy_item_id=i.item_id
            WHERE c.name IN ('Weapons','Shields','Head','Armour','Accessories')
              AND redirect.legacy_item_id IS NULL
            GROUP BY c.category_id ORDER BY c.heroic_hoarder_order"""
        )]
        result["compatibility_coverage"] = {
            "catalog_item_rows": sum(row["catalog_item_rows"] for row in catalog_rows),
            "audited_item_rows": len(audit_rows),
            "verified_item_rows": states["two_source_agreement"],
            "verified_item_character_pairs": states["two_source_agreement"] * 6,
            "verified_can_equip_pairs": connection.execute(
                "SELECT COUNT(*) FROM equipment_compatibility WHERE can_equip=1"
            ).fetchone()[0],
            "conflicted_item_rows": states["source_disagreement"],
            "single_source_item_rows": states["single_source"],
            "unaudited_item_rows": sum(row["unaudited_item_rows"] for row in catalog_rows),
            "by_category": catalog_rows,
            "status": "partial_two_source_matrix",
        }
        obtained_items = set(state.get("completion", {}).get("items_obtained", []))
        owned_hearts = set(state.get("completion", {}).get("monster_hearts_owned", []))
        owned_accessories = [dict(row) for row in connection.execute(
            """SELECT i.item_id, i.name, mh.heart_id
            FROM items i JOIN item_categories c USING(category_id)
            LEFT JOIN monster_hearts mh ON mh.name=i.name
            LEFT JOIN item_identity_redirects redirect ON redirect.legacy_item_id=i.item_id
            WHERE c.name='Accessories' AND redirect.legacy_item_id IS NULL
            ORDER BY i.name"""
        ) if row["item_id"] in obtained_items or row["heart_id"] in owned_hearts]
        compatible = {(row["item_id"], row["character_name"])
                      for row in connection.execute(
                          "SELECT item_id, character_name FROM equipment_compatibility WHERE can_equip=1")}
        for member_row in result["members"]:
            equipment = member_row["recorded_equipment"]
            member_row["accessory_slots"] = {
                slot: equipment.get(slot) for slot in ("accessory_1", "accessory_2")
            }
            member_row["accessory_options"] = [row for row in owned_accessories
                                               if (row["item_id"], member_row["name"]) in compatible]
            member_row["accessory_editor_status"] = "supported_owned_verified_distinct_only"
    if not checkpoint_id:
        result["status"] = "unknown_checkpoint"
        return result
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        checkpoint = connection.execute(
            "SELECT sequence_no FROM checkpoints WHERE checkpoint_id=?", (checkpoint_id,)
        ).fetchone()
        if checkpoint is None:
            result["status"] = "unknown_checkpoint"
            return result
        advice_rows = connection.execute(
            """SELECT a.advice_id, a.subject, a.advice_text, a.applicability_json,
                a.recommendation_goal, a.confidence, a.verification_status,
                s.source_id, s.title AS source_title, s.url AS source_url, a.locator
            FROM checkpoint_advice a JOIN sources s USING(source_id)
            WHERE a.checkpoint_id=? AND a.advice_type='gear' AND a.ready_for_play=1
            ORDER BY a.display_order, a.advice_id""", (checkpoint_id,)
        ).fetchall()
        item_rows = connection.execute(
            """SELECT i.item_id, i.name, c.name AS category FROM items i
            JOIN item_categories c USING(category_id)"""
        ).fetchall()
        aliases = connection.execute("SELECT alias, item_id FROM item_aliases").fetchall()
        available = {row[0] for row in connection.execute(
            """SELECT DISTINCT a.item_id FROM item_acquisition_paths a
            JOIN checkpoints c ON c.checkpoint_id=a.available_from_checkpoint_id
            WHERE c.sequence_no <= ?""", (checkpoint["sequence_no"],)
        )}
        compatibility_by_pair = {
            (row["item_id"], row["character_name"]): bool(row["can_equip"])
            for row in connection.execute(
                "SELECT item_id, character_name, can_equip FROM equipment_compatibility"
            )
        }
        compatibility_status_by_item = {
            row["item_id"]: row["agreement_status"]
            for row in connection.execute(
                "SELECT item_id, agreement_status FROM equipment_compatibility_audits"
            )
        }
    by_name = {row["name"].casefold(): dict(row) for row in item_rows}
    by_id = {row["item_id"]: dict(row) for row in item_rows}
    for alias, item_id in aliases:
        by_name[alias.casefold()] = by_id[item_id]
    obtained = set(state.get("completion", {}).get("items_obtained", []))
    slot_for_category = {"weapons": "weapon", "armour": "armour",
                         "shields": "shield", "head": "helmet",
                         "accessories": "accessory"}
    for advice in advice_rows:
        applicability = json.loads(advice["applicability_json"])
        character = applicability.get("party_member")
        candidates = []
        if isinstance(applicability.get("item"), str):
            candidates.append((None, applicability["item"]))
        if isinstance(applicability.get("items"), dict):
            candidates.extend(applicability["items"].items())
        for stated_slot, stated_name in candidates:
            if not isinstance(stated_name, str):
                continue
            item = by_name.get(stated_name.casefold())
            if item is None:
                continue
            slot = stated_slot or slot_for_category.get(item["category"].casefold())
            recorded = members.get(character, {}).get("equipment", {}) if character else {}
            recorded_value = recorded.get(slot) if isinstance(recorded, dict) and slot else None
            matches = recorded_value in (item["item_id"], item["name"])
            compatibility = compatibility_by_pair.get((item["item_id"], character))
            audit_status = compatibility_status_by_item.get(item["item_id"], "not_audited")
            result["recommendations"].append({
                "advice_id": advice["advice_id"], "character": character,
                "slot": slot, "item_id": item["item_id"], "item_name": item["name"],
                "category": item["category"],
                "availability_status": "route_available" if item["item_id"] in available else "route_not_proven_by_checkpoint",
                "ownership_status": "recorded" if item["item_id"] in obtained else "unknown",
                "comparison_status": "matches_recommendation" if matches else "current_equipment_unknown" if recorded_value is None else "different_recorded_value",
                "recorded_value": recorded_value,
                "recommendation": advice["advice_text"],
                "goal": advice["recommendation_goal"],
                "source": {"id": advice["source_id"], "title": advice["source_title"],
                           "url": advice["source_url"], "locator": advice["locator"]},
                "confidence": advice["confidence"],
                "verification_status": advice["verification_status"],
                "compatibility_status": (
                    "verified_can_equip" if compatibility is True else
                    "verified_cannot_equip" if compatibility is False else audit_status
                ),
                "compatibility_basis": (
                    "Two independent current-version equipment rows agree for this character and item."
                    if compatibility is not None else
                    "Compatibility remains disputed or single-source; the attributed recommendation is not universal proof."
                ),
            })
    result["status"] = "recommendations_available" if result["recommendations"] else "no_checkpoint_gear_recommendations"
    return result


def _monster_hearts(db_path: Path, query: dict, state_path: Path | None = None) -> dict:
    rows = _rows(db_path, """SELECT h.heart_id, h.name, h.effect_text,
        h.available_from_checkpoint_id, c.name AS available_checkpoint,
        h.availability_notes, h.confidence, h.verification_status,
        h.source_id, s.title AS source_title, s.url AS source_url, h.locator
        FROM monster_hearts h
        LEFT JOIN checkpoints c ON c.checkpoint_id=h.available_from_checkpoint_id
        JOIN sources s USING(source_id)
        ORDER BY COALESCE(c.sequence_no, 999), h.name""")
    player_state = _state(state_path) if state_path else {}
    completion = player_state.get("completion", {})
    tracking_known = "monster_hearts_owned" in completion
    recorded_owned = set(completion.get("monster_hearts_owned", [])) if tracking_known else set()
    canonical_ids = {row["heart_id"] for row in rows}
    owned = recorded_owned & canonical_ids
    checkpoint_id = player_state.get("story", {}).get("checkpoint_id")
    checkpoint_sequence = None
    if checkpoint_id:
        with sqlite3.connect(db_path) as connection:
            checkpoint = connection.execute(
                "SELECT sequence_no FROM checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            ).fetchone()
        checkpoint_sequence = checkpoint[0] if checkpoint else None
    for row in rows:
        routes = _heart_routes(db_path, row["name"])
        row["route_count"] = len(routes)
        if not row["available_from_checkpoint_id"] and routes:
            row["available_from_checkpoint_id"] = routes[0]["available_from_checkpoint_id"]
            row["available_checkpoint"] = routes[0]["available_checkpoint"]
            row["availability_status"] = "route_normalized"
        else:
            row["availability_status"] = ("heart_gate" if row["available_from_checkpoint_id"]
                                          else "unknown")
        row["owned"] = (row["heart_id"] in owned) if tracking_known else None
        row["ownership_status"] = ("owned" if row["owned"] is True else
                                   "not_owned" if row["owned"] is False else "unknown")
        if checkpoint_sequence is None or not row["available_from_checkpoint_id"]:
            row["available_now"] = None
        else:
            with sqlite3.connect(db_path) as connection:
                gate = connection.execute(
                    "SELECT sequence_no FROM checkpoints WHERE checkpoint_id = ?",
                    (row["available_from_checkpoint_id"],),
                ).fetchone()
            row["available_now"] = bool(gate and gate[0] <= checkpoint_sequence)
    page = _page(rows, query, ("heart_id", "name", "effect_text",
        "available_checkpoint", "availability_notes"))
    page["hearts"] = page.pop("results")
    page["ownership_tracking"] = "explicit" if tracking_known else "unknown"
    page["owned_count"] = len(owned) if tracking_known else None
    page["unknown_state_ids"] = sorted(recorded_owned - canonical_ids)
    return page


def _heart_routes(db_path: Path, heart_name: str) -> list[dict]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute("""SELECT a.acquisition_id, a.method,
            a.route_label, a.location_text, a.time_period,
            a.available_from_checkpoint_id, c.name AS available_checkpoint,
            a.unavailable_after_checkpoint_id, a.prerequisite_json,
            a.quantity, a.supply_type, a.finite_total, a.is_free,
            a.confidence, a.verification_status, a.source_id,
            s.title AS source_title, s.url AS source_url, a.locator
            FROM item_acquisition_paths a JOIN items i USING(item_id)
            JOIN sources s USING(source_id)
            LEFT JOIN checkpoints c ON c.checkpoint_id=a.available_from_checkpoint_id
            WHERE lower(i.name)=lower(?)
            ORDER BY COALESCE(c.sequence_no, 999), a.acquisition_id""", (heart_name,))]
    for row in rows:
        row["prerequisites"] = json.loads(row.pop("prerequisite_json"))
        row["drop_rate"] = None
        row["drop_rate_status"] = "unknown" if row["method"] == "drop" else "not_applicable"
        row["dlc_scope"] = None
        row["dlc_scope_status"] = "unknown"
    return rows


def _missables(db_path: Path, query: dict, state_path: Path | None = None) -> dict:
    rows = _rows(db_path, """SELECT m.missable_id, m.name, m.available_from,
        m.unavailable_after, m.consequence, m.severity, m.confidence,
        m.verification_status, m.available_from_checkpoint_id, m.obligation_id,
        o.stop_before_advancing AS linked_stop, m.source_id, s.title AS source_title,
        s.url AS source_url, m.locator
        FROM missables m JOIN sources s USING(source_id)
        LEFT JOIN checkpoint_obligations o USING(obligation_id)
        ORDER BY CASE WHEN m.unavailable_after IS NULL THEN 1 ELSE 0 END, m.name""")
    for row in rows:
        row["window_status"] = ("verified" if row["available_from"] and
            row["unavailable_after"] and
            row["verification_status"].startswith("source_checked")
            else "unresolved")
        row["provenance_gap"] = not bool(row["locator"])
        row["window_gap_reason"] = (None if row["window_status"] == "verified"
            else "The current-version source warns that the opportunity disappears after later story progress but does not name the exact event or checkpoint.")
        row["stop_warning_eligible"] = (row["window_status"] == "verified"
                                        and row["linked_stop"] == 1)
        completed = set(_state(state_path).get("completion", {}).get("missables_completed", [])) if state_path else set()
        missed = set(_state(state_path).get("completion", {}).get("missables_missed", [])) if state_path else set()
        row["progress_status"] = ("completed" if row["missable_id"] in completed else
                                  "missed" if row["missable_id"] in missed else "unknown")
    page = _page(rows, query, ("missable_id", "name", "available_from",
        "unavailable_after", "consequence", "severity", "window_status",
        "verification_status", "locator"))
    page["missables"] = page.pop("results")
    return page


def _farms(db_path: Path, query: dict) -> dict:
    rows = _rows(db_path, """SELECT f.farming_id, f.target, f.location,
        f.time_period, f.available_from, f.available_from_checkpoint_id,
        c.name AS available_checkpoint, f.encounter_rate_text, f.strategy,
        f.confidence, f.verification_status, f.source_id, f.locator,
        s.title AS source_title, s.url AS source_url,
        f.strategy_source_id, f.strategy_locator,
        ss.title AS strategy_source_title, ss.url AS strategy_source_url
        FROM farming_spots f JOIN sources s USING(source_id)
        LEFT JOIN checkpoints c ON c.checkpoint_id=f.available_from_checkpoint_id
        LEFT JOIN sources ss ON ss.source_id=f.strategy_source_id
        ORDER BY f.location, f.target""")
    for row in rows:
        target = row["target"].casefold()
        row["farm_type"] = ("proficiency" if "proficiency" in target
            else "gold" if "gold" in target
            else "exp" if "metal" in target or "jewel" in target
            else "seeds" if "seed" in target else "other")
        row["rate_status"] = "numeric_unpublished"
        row["provenance_gap"] = False
        row["strategy_kind"] = "attributed_strategy" if row["strategy"] else None
    through_checkpoint = query.get("through_checkpoint", [""])[0].strip()
    if through_checkpoint:
        checkpoint = _rows(db_path,
            "SELECT sequence_no FROM checkpoints WHERE checkpoint_id=?",
            (through_checkpoint,))
        if not checkpoint:
            raise ValueError(f"Unknown checkpoint: {through_checkpoint}")
        sequence = checkpoint[0]["sequence_no"]
        gated = _rows(db_path, "SELECT checkpoint_id, sequence_no FROM checkpoints")
        sequence_by_id = {row["checkpoint_id"]: row["sequence_no"] for row in gated}
        rows = [row for row in rows
                if row["available_from_checkpoint_id"] is not None
                and sequence_by_id[row["available_from_checkpoint_id"]] <= sequence]
        for row in rows:
            row["availability_status"] = "available_by_checkpoint"
        query = {key: value for key, value in query.items()
                 if key != "through_checkpoint"}
    page = _page(rows, query, ("farming_id", "target", "location",
        "time_period", "available_from", "encounter_rate_text", "strategy", "farm_type"))
    page["farms"] = page.pop("results")
    return page


def _sources(db_path: Path, query: dict) -> dict:
    rows = _rows(db_path, """SELECT source_id, title, publisher, url,
        source_class, role, published_at, updated_at, retrieved_at, status, notes
        FROM sources ORDER BY publisher, title""")
    today = date.today()
    for row in rows:
        try:
            retrieved_age = (today - date.fromisoformat(row["retrieved_at"][:10])).days
        except (TypeError, ValueError):
            retrieved_age = None
        row["retrieval_age_days"] = retrieved_age
        row["retrieval_band"] = ("unknown" if retrieved_age is None else
                                 "over_180_days" if retrieved_age > 180 else
                                 "within_180_days")
        row["update_date_status"] = "known" if row["updated_at"] else "unknown"
    for key in ("role", "publisher", "retrieval_band", "update_date_status"):
        value = query.get(key, [""])[0].strip().casefold()
        if value:
            rows = [row for row in rows if str(row.get(key, "")).casefold() == value]
    publishers = sorted({row["publisher"] for row in _rows(db_path,
        "SELECT publisher FROM sources ORDER BY publisher")})
    page = _page(rows, query, ("source_id", "title", "publisher", "role",
        "source_class", "status"))
    page["sources"] = page.pop("results")
    page["publishers"] = publishers
    return page


def _evidence_gaps(db_path: Path, audit_path: Path = DEFAULT_EVIDENCE_GAPS) -> dict:
    gaps = json.loads(audit_path.read_text(encoding="utf-8"))
    source_rows = {row["source_id"]: row for row in _rows(db_path, """SELECT
        source_id, title, publisher, url, source_class, updated_at, retrieved_at
        FROM sources""")}
    today = date.today()
    for source in source_rows.values():
        try:
            age = (today - date.fromisoformat(source["retrieved_at"][:10])).days
        except (TypeError, ValueError):
            age = None
        source["retrieval_age_days"] = age
        source["retrieval_band"] = ("unknown" if age is None else
                                    "over_180_days" if age > 180 else
                                    "within_180_days")
    for gap in gaps:
        missing = [source_id for source_id in gap["source_ids"]
                   if source_id not in source_rows]
        if missing:
            raise ValueError(f"Unknown evidence-gap source ID(s): {missing}")
        gap["sources"] = [source_rows[source_id] for source_id in gap["source_ids"]]
        gap["source_count"] = len(gap["sources"])
        gap["verification_tier"] = (
            "unsupported" if gap["status"] == "no_publishable_source" else
            "single_source" if gap["source_count"] < 2 else
            "corroborated_but_unresolved"
        )
        gap["freshness_status"] = (
            "no_sources" if not gap["sources"] else
            "unknown" if any(source["retrieval_band"] == "unknown"
                             for source in gap["sources"]) else
            "stale" if any(source["retrieval_band"] == "over_180_days"
                           for source in gap["sources"]) else
            "current_retrieval"
        )
    conflict_rows = _rows(db_path, """SELECT ca.predicate, COUNT(*) AS count
        FROM conflicts c JOIN claims ca ON ca.claim_id=c.claim_a_id
        WHERE c.status='unresolved'
        GROUP BY ca.predicate ORDER BY count DESC, ca.predicate""")
    source_total = len(source_rows)
    freshness_counts = {"within_180_days": 0, "over_180_days": 0, "unknown": 0}
    for source in source_rows.values():
        freshness_counts[source["retrieval_band"]] += 1
    return {
        "total": len(gaps),
        "single_source": sum(gap["verification_tier"] == "single_source" for gap in gaps),
        "unsupported": sum(gap["verification_tier"] == "unsupported" for gap in gaps),
        "corroborated_but_unresolved": sum(
            gap["verification_tier"] == "corroborated_but_unresolved" for gap in gaps
        ),
        "unresolved_conflicts": sum(row["count"] for row in conflict_rows),
        "unresolved_conflicts_by_predicate": conflict_rows,
        "source_freshness": {"total": source_total, **freshness_counts},
        "gaps": gaps,
    }


def _seeds(db_path: Path, query: dict) -> dict:
    effects = _rows(db_path, """SELECT se.seed_effect_id AS seed_id,
        'effect' AS record_type, i.name, se.item_id, se.stat_key,
        se.increase_amount, se.game_version, se.dlc_scope, se.confidence,
        se.verification_status, se.locator, se.source_id,
        s.title AS source_title, s.url AS source_url
        FROM seed_effects se JOIN items i USING(item_id)
        JOIN sources s USING(source_id) ORDER BY i.name""")
    for row in effects:
        row["variant"] = "super" if row["name"].startswith("Super ") else "standard"
        row["dlc_scope_status"] = "specified" if row["dlc_scope"] else "not_recorded"
    rewards = _rows(db_path, """SELECT r.seed_reward_rule_id AS seed_id,
        'reward_rule' AS record_type, r.reward_family_text AS name,
        r.available_from_checkpoint_id, c.name AS available_checkpoint,
        r.location_text, r.trigger_text, r.reward_quantity,
        r.selection_method, r.eligible_items_json, r.repeatable,
        r.game_version, r.dlc_scope, r.confidence, r.verification_status,
        r.locator, r.source_id, s.title AS source_title, s.url AS source_url
        FROM seed_reward_rules r LEFT JOIN checkpoints c
        ON c.checkpoint_id = r.available_from_checkpoint_id
        JOIN sources s USING(source_id) ORDER BY r.reward_family_text""")
    for row in rewards:
        row["variant"] = "reward"
        row["eligible_items"] = (json.loads(row["eligible_items_json"])
                                 if row["eligible_items_json"] else None)
        row["eligible_pool_status"] = "known" if row["eligible_items"] is not None else "unknown"
        row["dlc_scope_status"] = "specified" if row["dlc_scope"] else "not_recorded"
        del row["eligible_items_json"]
    rows = effects + rewards
    variant = query.get("variant", [""])[0].strip().casefold()
    if variant:
        rows = [row for row in rows if row["variant"] == variant]
    stat = query.get("stat", [""])[0].strip().casefold()
    if stat:
        rows = [row for row in rows if str(row.get("stat_key", "")).casefold() == stat]
    page = _page(rows, query, ("seed_id", "name", "record_type", "variant",
        "stat_key", "location_text", "trigger_text", "source_title"))
    page["seeds"] = page.pop("results")
    return page


def _moonlighting(db_path: Path) -> dict:
    rows = _rows(db_path, """SELECT c.claim_id, c.predicate, c.value_json,
        c.confidence, c.verification_status, c.locator, c.source_id,
        s.title AS source_title, s.url AS source_url
        FROM claims c JOIN sources s USING(source_id)
        WHERE c.subject_key='system:moonlighting' AND c.claim_kind='fact'
        ORDER BY c.predicate""")
    facts = [{**row, "value": json.loads(row["value_json"])} for row in rows]
    for row in facts:
        del row["value_json"]
    unlocks = [row for row in facts if row["predicate"] == "unlocks_when"]
    mechanics = next((row for row in facts if row["predicate"] == "effect"), None)
    canonical = next((row for row in unlocks
                      if row["claim_id"] == "claim_moonlighting_sequence_corroborated"),
                     unlocks[0] if unlocks else None)
    venue_resolution = _rows(db_path, """SELECT status, rationale
        FROM conflicts
        WHERE (claim_a_id='claim_moonlighting_unlock'
               AND claim_b_id='claim_moonlighting_unlock_rpgsite')
           OR (claim_b_id='claim_moonlighting_unlock'
               AND claim_a_id='claim_moonlighting_unlock_rpgsite')""")
    retention_rows = _rows(db_path, """SELECT c.claim_id, c.value_json,
        c.confidence, c.verification_status, c.locator, c.source_id,
        s.title AS source_title, s.url AS source_url
        FROM claims c JOIN sources s USING(source_id)
        WHERE c.claim_id='claim_vocation_skill_retention'""")
    retention = None
    if retention_rows:
        retention = {**retention_rows[0], "value": json.loads(retention_rows[0]["value_json"])}
        del retention["value_json"]
    return {"unlock": canonical,
            "unlock_claims": unlocks,
            "venue_status": ("resolved_process_stages" if venue_resolution
                             and venue_resolution[0]["status"] == "resolved"
                             else "conflicting_sources" if len(unlocks) > 1 else "single_source"),
            "venue_resolution": venue_resolution[0] if venue_resolution else None,
            "mechanics": mechanics,
            "skill_retention": retention,
            "recommendation_notice": "Pairing suggestions are attributed recommendations, not legal-pairing rules."}


def _medals(db_path: Path, state_path: Path) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    found = set(state.get("completion", {}).get("mini_medals_found", []))
    rows = _rows(db_path, """SELECT medal_number, location, detail, time_period,
        checkpoint_id, available_checkpoint_id, available_from, unavailable_after
        FROM mini_medal_locations ORDER BY medal_number""")
    for row in rows:
        row["found"] = row["medal_number"] in found
    return {"total": len(rows), "found_count": sum(row["found"] for row in rows), "medals": rows}


def _tablets(db_path: Path, state_path: Path) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    found = set(state.get("completion", {}).get("tablet_fragments", []))
    rows = _rows(db_path, """SELECT t.tablet_id, t.destination_name AS tablet_name,
        f.fragment_id, f.location, f.time_period,
        f.available_from_checkpoint_id AS checkpoint_id
        FROM stone_tablets t JOIN tablet_fragments f USING(tablet_id)
        ORDER BY t.tablet_id, f.fragment_id""")
    for row in rows:
        row["found"] = row["fragment_id"] in found
    return {"tablet_count": len({row['tablet_id'] for row in rows}),
            "fragment_count": len(rows), "found_count": sum(row["found"] for row in rows),
            "fragments": rows}


def _dashboard(db_path: Path, state_path: Path) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    checkpoint_id = state.get("story", {}).get("checkpoint_id")
    checkpoint = load_report(db_path, state_path, checkpoint_id) if checkpoint_id else None
    achievements = load_achievement_report(db_path, state_path)
    return {
        "state": state,
        "checkpoint": checkpoint,
        "summaries": {
            "hoarder": load_hoarder_report(db_path, state_path, gaps_only=True),
            "achievements": {
                "total": achievements["total"],
                "unlocked_count": achievements["unlocked_count"],
                "remaining_count": len(achievements["achievements"]),
            },
            "monsters": load_monster_coverage(db_path, state_path),
            "open_conflicts": len(load_conflicts(db_path)),
        },
    }


def _checkpoint_view(db_path: Path, state_path: Path, checkpoint_id: str) -> dict:
    block = load_walkthrough(db_path, state_path, checkpoint_id, checkpoint_id)["blocks"][0]
    player_state = _state(state_path)
    completion = player_state.get("completion", {})
    completed_actions = set(completion.get("obligations_completed", []))
    found_medals = set(completion.get("mini_medals_found", []))
    defeated_monsters = set(completion.get("monster_entries", []))
    checkpoint = block["checkpoint"]
    checkpoint_rows = _checkpoints(db_path)
    checkpoint_index = next(index for index, row in enumerate(checkpoint_rows)
                            if row["checkpoint_id"] == checkpoint_id)
    next_checkpoint = (checkpoint_rows[checkpoint_index + 1]
                       if checkpoint_index + 1 < len(checkpoint_rows) else None)
    medal_groups = (("now", block["medals_now"]),
                    ("backtrack", block["medals_backtrack"]),
                    ("later", block["medals_later"]))
    medals = [row for _, rows in medal_groups for row in rows]
    sourced_rows = block["stops"] + block["now"] + block["advice"] + medals
    sources = {}
    for row in sourced_rows:
        source_id = row.get("source_id")
        if source_id:
            sources[(source_id, row.get("locator"))] = {
                "id": source_id, "title": row.get("source_title"),
                "url": row.get("source_url"), "locator": row.get("locator"),
            }
    monster_ids = [row["monster_id"] for row in block["monsters"]]
    drops: dict[str, list[str]] = {monster_id: [] for monster_id in monster_ids}
    if monster_ids:
        placeholders = ",".join("?" for _ in monster_ids)
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            drop_rows = connection.execute(
                f"""SELECT d.monster_id, d.item_name, d.locator, s.source_id,
                    s.title AS source_title, s.url AS source_url
                FROM monster_drops d JOIN sources s USING(source_id)
                WHERE d.monster_id IN ({placeholders})
                ORDER BY d.monster_id, d.item_name""",
                monster_ids,
            )
            for row in drop_rows:
                drops[row["monster_id"]].append(row["item_name"])
                sources[(row["source_id"], row["locator"])] = {
                    "id": row["source_id"], "title": row["source_title"],
                    "url": row["source_url"], "locator": row["locator"],
                }
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        tablet_fragments = [dict(row) for row in connection.execute(
            """SELECT f.fragment_id, f.source_ordinal, f.color, f.tablet_id,
                t.destination_name AS tablet_name, f.location, f.time_period,
                f.detail, f.unavailable_after_checkpoint_id,
                f.source_id, s.title AS source_title, s.url AS source_url,
                f.locator, f.confidence, f.verification_status
            FROM tablet_fragments f JOIN stone_tablets t USING(tablet_id)
            JOIN sources s ON s.source_id=f.source_id
            WHERE f.available_from_checkpoint_id=?
            ORDER BY f.source_ordinal""", (checkpoint_id,))]
    for row in tablet_fragments:
        sources[(row["source_id"], row["locator"])] = {
            "id": row["source_id"], "title": row["source_title"],
            "url": row["source_url"], "locator": row["locator"],
        }
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        item_route_rows = [dict(row) for row in connection.execute(
            """SELECT i.item_id, i.name, c.name AS category,
                a.acquisition_id, a.method, a.route_label, a.location_text,
                a.time_period, a.unavailable_after_checkpoint_id, a.is_free,
                a.quantity, a.source_id, s.title AS source_title,
                s.url AS source_url, a.locator, a.confidence,
                a.verification_status
            FROM item_acquisition_paths a JOIN items i USING(item_id)
            JOIN item_categories c USING(category_id)
            JOIN sources s ON s.source_id=a.source_id
            WHERE a.available_from_checkpoint_id=? AND a.supply_type='finite'
              AND i.heroic_hoarder_required=1
            ORDER BY c.heroic_hoarder_order, i.heroic_hoarder_ordinal,
                     a.acquisition_id""", (checkpoint_id,))]
    checkpoint_items: dict[str, dict] = {}
    obtained_items = set(completion.get("items_obtained", []))
    for row in item_route_rows:
        item = checkpoint_items.setdefault(row["item_id"], {
            "id": row["item_id"], "name": row["name"],
            "category": row["category"], "obtained": row["item_id"] in obtained_items,
            "routes": [],
        })
        item["routes"].append({key: row[key] for key in (
            "acquisition_id", "method", "route_label", "location_text",
            "time_period", "unavailable_after_checkpoint_id", "is_free",
            "quantity", "confidence", "verification_status")}
            | {"source": {"id": row["source_id"], "title": row["source_title"],
                          "url": row["source_url"], "locator": row["locator"]}})
        sources[(row["source_id"], row["locator"])] = {
            "id": row["source_id"], "title": row["source_title"],
            "url": row["source_url"], "locator": row["locator"],
        }
    achievement_rows = []
    for row in load_achievement_report(db_path, state_path, True)["achievements"]:
        timing = ("due_here" if row["completion_checkpoint_id"] == checkpoint_id else
                  "tracking_starts" if row["completion_checkpoint_id"] is None
                  and row["earliest_checkpoint_id"] == checkpoint_id else None)
        if timing is None:
            continue
        achievement_rows.append({
            "id": row["achievement_id"], "name": row["name"],
            "description": row["description"], "category": row["category"],
            "grade": row["grade"], "platform_scope": row["platform_scope"],
            "timing": timing, "unlocked": row["unlocked"],
            "dependency_progress": row["dependency_progress"],
            "source": {"id": row["source_id"], "title": row["source_title"],
                       "url": row["source_url"], "locator": row["locator"]},
            "confidence": row["confidence"],
            "verification_status": row["verification_status"],
        })
        sources[(row["source_id"], row["locator"])] = {
            "id": row["source_id"], "title": row["source_title"],
            "url": row["source_url"], "locator": row["locator"],
        }
    checkpoint_missables = [row for row in _missables(db_path, {}, state_path)["missables"]
                            if row["available_from_checkpoint_id"] == checkpoint_id]
    for row in checkpoint_missables:
        sources[(row["source_id"], row["locator"])] = {
            "id": row["source_id"], "title": row["source_title"],
            "url": row["source_url"], "locator": row["locator"],
        }
    open_required = [row for row in block["now"] if row["required_for_100_percent"]]
    saved_checkpoint_match = player_state.get("story", {}).get("checkpoint_id") == checkpoint_id
    if block["stops"]:
        readiness_status = "blocked_by_stop"
        readiness_reason = "Clear the STOP obligation before advancing."
    elif open_required:
        readiness_status = "required_actions_open"
        readiness_reason = "Complete the remaining required actions first."
    else:
        readiness_status = "manual_confirmation"
        readiness_reason = "No structured blocker remains; confirm the sourced safe condition yourself."
    advancement_readiness = {
        "status": readiness_status, "reason": readiness_reason,
        "open_stop_count": len(block["stops"]),
        "open_required_action_count": len(open_required),
        "open_optional_action_count": len(block["now"]) - len(open_required),
        "unrecorded_available_medal_count": len(block["medals_now"]) + len(block["medals_backtrack"]),
        "unrecorded_checkpoint_tablet_fragment_count": sum(
            row["fragment_id"] not in set(completion.get("tablet_fragments", []))
            for row in tablet_fragments),
        "unrecorded_finite_hoarder_item_count": sum(
            not row["obtained"] for row in checkpoint_items.values()),
        "unrecorded_due_achievement_count": sum(
            row["timing"] == "due_here" and not row["unlocked"]
            for row in achievement_rows),
        "unrecorded_checkpoint_missable_count": sum(
            row["progress_status"] == "unknown" for row in checkpoint_missables),
        "saved_checkpoint_match": saved_checkpoint_match,
        "safe_condition_requires_player_confirmation": True,
        "next_checkpoint": ({"id": next_checkpoint["checkpoint_id"],
                             "name": next_checkpoint["name"]}
                            if next_checkpoint else None),
        "can_confirm_and_save_next": bool(next_checkpoint and saved_checkpoint_match
                                           and readiness_status == "manual_confirmation"),
    }
    advice = [{
        "id": row["advice_id"], "type": row["advice_type"],
        "subject": row["subject"], "text": row["advice_text"],
        "goal": row["recommendation_goal"],
        "decision_group": ("optional_grind" if row["advice_type"] == "grind"
                           else "completion_safe" if row["recommendation_goal"] in ("completion_safe", "both")
                           else "strongest_now"),
        "applicability": json.loads(row["applicability_json"]),
        "tradeoff": json.loads(row["applicability_json"]).get("tradeoff"),
        "source": {"id": row["source_id"], "title": row["source_title"],
                   "url": row["source_url"], "locator": row["locator"]},
        "confidence": row["confidence"],
        "verification_status": row["verification_status"],
        "saved_state_applicability": _advice_applicability(
            db_path, player_state, json.loads(row["applicability_json"])),
    } for row in block["advice"]]
    party_members = player_state.get("party", {}).get("members", {})
    active_party = set(player_state.get("party", {}).get("active", []))
    explicit_party = [{
        "name": name, "level": member.get("level"),
        "primary_vocation": member.get("primary_vocation"),
        "secondary_vocation": member.get("secondary_vocation"),
        "active": name in active_party,
    } for name, member in party_members.items() if name in active_party or any((
        member.get("level") is not None, member.get("primary_vocation") is not None,
        member.get("secondary_vocation") is not None))]
    farm_options = _farms(db_path, {
        "through_checkpoint": [checkpoint_id], "limit": ["100"]
    })["farms"]
    equipment = (_equipment_readiness(db_path, state_path)
                 if saved_checkpoint_match else {"recommendations": []})
    strongest_candidates = [
        row for row in advice if row["decision_group"] == "strongest_now"
        and row["saved_state_applicability"]["status"] != "unmet"
    ]
    concise_strongest = []
    for advice_type in ("vocation", "gear", "boss", "grind"):
        row = next((candidate for candidate in strongest_candidates
                    if candidate["type"] == advice_type), None)
        if row is not None and row not in concise_strongest:
            concise_strongest.append(row)
    for row in strongest_candidates:
        if len(concise_strongest) >= 4:
            break
        if row not in concise_strongest:
            concise_strongest.append(row)
    safe_power_candidates = [
        row for row in advice if row["goal"] == "both"
        and row["type"] != "grind"
        and row["saved_state_applicability"]["status"] != "unmet"
    ]
    party_status = ("unknown" if not explicit_party else
                    "partial" if len(explicit_party) < len(party_members) else
                    "recorded")
    power_plan = {
        "state_scope": "explicit_saved_state_only",
        "state_status": party_status,
        "party_note": ("No party levels or vocations are recorded."
                       if party_status == "unknown" else
                       "Only explicitly recorded party entries are shown; omitted values remain unknown."
                       if party_status == "partial" else
                       "Every saved party member has at least one recorded level or vocation value."),
        "party": explicit_party,
        "strongest_now": concise_strongest,
        "additional_strongest_count": len(strongest_candidates) - len(concise_strongest),
        "safe_power": safe_power_candidates[:2],
        "additional_safe_power_count": max(len(safe_power_candidates) - 2, 0),
        "grind_ceiling": [row for row in advice if row["decision_group"] == "optional_grind"],
        "gear_checks": equipment["recommendations"],
        "available_farms": farm_options,
        "farm_note": ("Available sourced options, not a ranking. Use the attributed grind ceiling above when present."
                      if farm_options else "No checkpoint-gated farm is verified as available yet."),
    }
    return {
        "id": checkpoint_id, "name": checkpoint["name"],
        "time_period": checkpoint["time_period"], "region": checkpoint["region"],
        "stop_warnings": [row["action"] for row in block["stops"]],
        "stop_actions": [{
            "id": row["obligation_id"], "title": row["subject"],
            "action": row["action"], "completed": False,
            "required": bool(row["required_for_100_percent"]),
            "type": row["obligation_type"],
            "source": {"id": row["source_id"], "title": row["source_title"],
                       "url": row["source_url"], "locator": row["locator"]},
        } for row in block["stops"]],
        "actions": [{
            "id": row["obligation_id"], "title": row["subject"],
            "action": row["action"], "completed": row["obligation_id"] in completed_actions,
            "required": bool(row["required_for_100_percent"]),
            "type": row["obligation_type"], "display_order": row["display_order"],
            "is_next": index == 0,
            "source": {"id": row["source_id"], "title": row["source_title"],
                       "url": row["source_url"], "locator": row["locator"]},
        } for index, row in enumerate(block["now"])],
        "advice": advice,
        "power_plan": power_plan,
        "medals": [{"number": row["medal_number"], "location": row["location"],
                     "detail": row["detail"], "found": row["medal_number"] in found_medals,
                     "timing": timing,
                     "available_checkpoint": row["available_checkpoint"],
                     "available_from": row["available_from"]}
                    for timing, rows in medal_groups for row in rows],
        "tablet_fragments": [{
            "id": row["fragment_id"], "ordinal": row["source_ordinal"],
            "color": row["color"], "tablet_id": row["tablet_id"],
            "tablet_name": row["tablet_name"], "location": row["location"],
            "time_period": row["time_period"], "detail": row["detail"],
            "found": row["fragment_id"] in set(completion.get("tablet_fragments", [])),
            "unavailable_after_checkpoint_id": row["unavailable_after_checkpoint_id"],
            "source": {"id": row["source_id"], "title": row["source_title"],
                       "url": row["source_url"], "locator": row["locator"]},
            "confidence": row["confidence"],
            "verification_status": row["verification_status"],
        } for row in tablet_fragments],
        "checkpoint_items": list(checkpoint_items.values()),
        "checkpoint_achievements": achievement_rows,
        "checkpoint_missables": checkpoint_missables,
        "monsters": [{"id": row["monster_id"], "ordinal": row["source_ordinal"],
                       "name": row["english_name"], "location": row["locations"],
                       "drop": ", ".join(drops[row["monster_id"]]) or None,
                       "defeated": row["monster_id"] in defeated_monsters} for row in block["monsters"]],
        "safe_condition": checkpoint["safe_exit_condition"],
        "advancement_readiness": advancement_readiness,
        "sources": list(sources.values()),
    }


def _progress(db_path: Path, state_path: Path) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    completion = state.get("completion", {})
    hoarder = load_hoarder_report(db_path, state_path)
    achievements = load_achievement_report(db_path, state_path)
    monsters = load_monster_coverage(db_path, state_path)
    medal_count = completion.get("mini_medal_count")
    medals_found = completion.get("mini_medals_found", [])
    medals = medal_count if medal_count is not None else (len(medals_found) if medals_found else None)
    mastered = {
        vocation_id for member in state.get("party", {}).get("members", {}).values()
        for vocation_id, value in member.get("vocation_mastery", {}).items() if value is True
    }
    def identity_ledger(values: list, sql: str, total: int) -> dict:
        canonical = {next(iter(row.values())) for row in _rows(db_path, sql)}
        recorded = set(values)
        known = len(recorded & canonical)
        return {
            "status": ("unknown" if not recorded else
                       "complete" if known >= total else "partial"),
            "known_count": None if not recorded else known,
            "total": total,
            "unknown_state_ids": sorted(recorded - canonical),
        }

    ledgers = {
        "items": identity_ledger(completion.get("items_obtained", []),
            "SELECT item_id FROM items WHERE heroic_hoarder_required=1", hoarder["total"]),
        "monsters": identity_ledger(completion.get("monster_entries", []),
            "SELECT monster_id FROM monsters", monsters["total"]),
        "tablets": identity_ledger(completion.get("tablet_fragments", []),
            "SELECT fragment_id FROM tablet_fragments", 71),
        "achievements": identity_ledger(completion.get("achievements_unlocked", []),
            "SELECT achievement_id FROM achievements", achievements["total"]),
    }
    heart_tracking = "monster_hearts_owned" in completion
    heart_values = completion.get("monster_hearts_owned", [])
    hearts = identity_ledger(heart_values, "SELECT heart_id FROM monster_hearts", 46)
    if heart_tracking and not heart_values:
        hearts.update({"status": "partial", "known_count": 0})
    ledgers["hearts"] = hearts
    vocation_values = sorted(mastered)
    ledgers["vocations"] = identity_ledger(
        vocation_values, "SELECT vocation_id FROM vocations", 26
    )
    found_medals = completion.get("mini_medals_found", [])
    if medal_count is not None:
        ledgers["medals"] = {"status": "complete" if medal_count >= 100 else "partial",
            "known_count": medal_count, "total": 100, "unknown_state_ids": []}
    else:
        valid_medals = {number for number in found_medals
            if isinstance(number, int) and not isinstance(number, bool)
            and 1 <= number <= 100}
        invalid_medals = [number for number in set(found_medals)
            if number not in valid_medals]
        ledgers["medals"] = {"status": "unknown" if not found_medals else "partial",
            "known_count": None if not found_medals else len(valid_medals),
            "total": 100, "unknown_state_ids": sorted(invalid_medals, key=str)}
    completed_missables = set(completion.get("missables_completed", []))
    missed_missables = set(completion.get("missables_missed", []))
    missables = identity_ledger(sorted(completed_missables | missed_missables),
        "SELECT missable_id FROM missables", 7)
    missables["completed_count"] = len(completed_missables)
    missables["missed_count"] = len(missed_missables)
    if missed_missables:
        missables["status"] = "missed"
    ledgers["missables"] = missables

    def display(ledger: dict) -> str:
        count = ledger["known_count"]
        return "Unknown" if count is None else f"{count} / {ledger['total']}"
    return {
        "actions": {"display": f"{len(completion.get('obligations_completed', []))} recorded"},
        "medals": {"display": display(ledgers["medals"])},
        "mini_medal_count": medal_count,
        "items": {"display": display(ledgers["items"])},
        "monsters": {"display": display(ledgers["monsters"])},
        "tablets": {"display": display(ledgers["tablets"])},
        "hearts": {"display": display(ledgers["hearts"])},
        "missables": {"display": display(ledgers["missables"])},
        "vocations": {"display": display(ledgers["vocations"])},
        "achievements": {"display": display(ledgers["achievements"])},
        "ledger_audit": ledgers,
        "saved_checkpoint": state.get("story", {}).get("checkpoint_id"),
        "party": [{"name": name, "level": member.get("level"),
                   "primary_vocation": member.get("primary_vocation"),
                   "secondary_vocation": member.get("secondary_vocation"),
                   "active": name in set(state.get("party", {}).get("active", [])),
                   "mastered_vocations": sorted(vocation_id for vocation_id, value
                                                in member.get("vocation_mastery", {}).items()
                                                if value is True)}
                  for name, member in state.get("party", {}).get("members", {}).items()],
        "open_work": [{"title": "Player checkpoint", "detail": state.get("story", {}).get("checkpoint_id") or "Unknown — select your current checkpoint"}],
    }


def _dashboard_view(db_path: Path, state_path: Path) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    checkpoint_id = state.get("story", {}).get("checkpoint_id") or DEFAULT_FROM
    checkpoint = _checkpoint_view(db_path, state_path, checkpoint_id)
    progress = _progress(db_path, state_path)
    sequence = next(row["sequence_no"] for row in _checkpoints(db_path) if row["checkpoint_id"] == checkpoint_id)
    return {
        "checkpoint": {"id": checkpoint_id, "name": checkpoint["name"],
                       "sequence_label": f"{sequence:02d} / 33",
                       "is_saved": bool(state.get("story", {}).get("checkpoint_id"))},
        "stop_warnings": checkpoint["stop_warnings"],
        "progress": {key: (progress[key]["display"] if progress[key] else None)
                     for key in ("medals", "items", "monsters")},
        "next_actions": checkpoint["actions"][:5],
    }


def _record_ui_progress(db_path: Path, state_path: Path, payload: dict) -> str:
    kind, identifier, completed = payload.get("kind"), payload.get("id"), payload.get("completed")
    if not isinstance(completed, bool):
        raise ValueError("completed must be true or false")
    if kind == "action":
        with sqlite3.connect(db_path) as connection:
            row = connection.execute(
                "SELECT checkpoint_id, display_order FROM checkpoint_obligations WHERE obligation_id=?",
                (identifier,),
            ).fetchone()
        if row is None:
            raise ValueError("Unknown action")
        return update_progress(state_path, db_path, "done" if completed else "undo", [row[0], str(row[1])])
    if kind == "medal":
        return update_progress(state_path, db_path,
                               "medal-found" if completed else "medal-undo",
                               [str(identifier)])
    if kind == "monster":
        return update_progress(state_path, db_path, "monster-defeated" if completed else "monster-undo", [str(identifier)])
    raise ValueError("Unsupported progress kind")


def _record_resource_progress(db_path: Path, state_path: Path, path: str, payload: dict) -> str:
    completed = payload.get("completed")
    if path.startswith("/api/checkpoints/"):
        if payload.get("selected") is not True:
            raise ValueError("selected must be true")
        return update_progress(state_path, db_path, "checkpoint",
                               [unquote(path.removeprefix("/api/checkpoints/"))])
    if not isinstance(completed, bool):
        raise ValueError("completed must be true or false")
    mappings = {
        "/api/items/": ("item-obtained", "item-undo"),
        "/api/tablets/": ("tablet-found", "tablet-undo"),
        "/api/achievements/": ("achievement-unlocked", "achievement-undo"),
        "/api/monster-hearts/": ("heart-obtained", "heart-undo"),
    }
    for prefix, commands in mappings.items():
        if path.startswith(prefix):
            identifier = unquote(path.removeprefix(prefix))
            return update_progress(state_path, db_path, commands[0] if completed else commands[1],
                                   [identifier])
    if path.startswith("/api/vocations/"):
        character = payload.get("character")
        if not isinstance(character, str) or not character:
            raise ValueError("character is required")
        vocation_id = unquote(path.removeprefix("/api/vocations/"))
        command = "vocation-mastered" if completed else "vocation-undo"
        return update_progress(state_path, db_path, command, [character, vocation_id])
    if path.startswith("/api/missables/"):
        missable_id = unquote(path.removeprefix("/api/missables/"))
        return update_progress(state_path, db_path,
                               "missable-completed" if completed else "missable-undo",
                               [missable_id])
    raise ValueError("Unsupported resource mutation")


def _record_accessory_progress(db_path: Path, state_path: Path, path: str, payload: dict) -> str:
    suffix = path.removeprefix("/api/equipment/accessories/")
    parts = [unquote(value) for value in suffix.split("/")]
    if len(parts) != 2:
        raise ValueError("Accessory path must identify character and slot")
    item_id = payload.get("item_id")
    if item_id is not None and not isinstance(item_id, str):
        raise ValueError("item_id must be a canonical item ID or null")
    return update_progress(state_path, db_path, "accessory-set",
                           [parts[0], parts[1], item_id or "unknown"])


def make_handler(db_path: Path, state_path: Path, static_dir: Path,
                 pairing_token: str | None = None, trust_loopback: bool = True):
    db_path, state_path, static_dir = map(Path, (db_path, state_path, static_dir))
    state_write_lock = threading.Lock()

    class GuideHandler(BaseHTTPRequestHandler):
        server_version = "DQ7Guide/1.0"

        def _json(self, payload, status=HTTPStatus.OK):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _download_json(self, payload, filename):
            body = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status, message):
            self._json({"error": message}, status)

        def _is_loopback(self):
            return self.client_address[0] in {"127.0.0.1", "::1"}

        def _paired(self):
            if pairing_token is None or (trust_loopback and self._is_loopback()):
                return True
            header_token = self.headers.get("X-DQ7-Pair", "")
            if header_token and hmac.compare_digest(header_token, pairing_token):
                return True
            cookies = {}
            for field in self.headers.get_all("Cookie", []):
                for pair in field.split(";"):
                    name, separator, value = pair.strip().partition("=")
                    if separator:
                        cookies[name] = value
            supplied = cookies.get("dq7_pair", "")
            return bool(supplied) and hmac.compare_digest(supplied, pairing_token)

        def _accept_pairing(self, parsed):
            if pairing_token is None or parsed.path != "/":
                return False
            if parse_qs(parsed.query).get("paired", [""])[0] == "1":
                return False
            supplied = parse_qs(parsed.query).get("pair", [""])[0]
            if not supplied or not hmac.compare_digest(supplied, pairing_token):
                return False
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", f"/?pair={pairing_token}&paired=1#walkthrough")
            self.send_header(
                "Set-Cookie",
                f"dq7_pair={pairing_token}; Path=/; Max-Age=315360000; HttpOnly; SameSite=Strict",
            )
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return True

        def _require_pairing(self):
            if self._paired():
                return True
            self._error(
                HTTPStatus.UNAUTHORIZED,
                "Phone not paired. Open the current DQ7 guide (phone) URL shown on the Steam Deck.",
            )
            return False

        def do_GET(self):
            parsed = urlparse(self.path)
            if self._accept_pairing(parsed):
                return
            supplied_query = parse_qs(parsed.query).get("pair", [""])[0]
            query_is_paired = bool(supplied_query) and hmac.compare_digest(
                supplied_query, pairing_token or "")
            public_asset = parsed.path != "/" and not parsed.path.startswith("/api/")
            if not public_asset and not query_is_paired and not self._require_pairing():
                return
            try:
                if parsed.path == "/api/health":
                    return self._json({"status": "ok"})
                if parsed.path == "/api/dashboard":
                    return self._json(_dashboard_view(db_path, state_path))
                if parsed.path == "/api/checkpoints":
                    return self._json([{"id": row["checkpoint_id"], "sequence": row["sequence_no"],
                                        "name": row["name"]} for row in _checkpoints(db_path)])
                if parsed.path.startswith("/api/checkpoints/"):
                    checkpoint_id = unquote(parsed.path.removeprefix("/api/checkpoints/"))
                    return self._json(_checkpoint_view(db_path, state_path, checkpoint_id))
                if parsed.path == "/api/progress":
                    return self._json(_progress(db_path, state_path))
                if parsed.path == "/api/state-backup":
                    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    return self._download_json(_load_state(state_path),
                                               f"dq7-progress-{stamp}.json")
                if parsed.path == "/api/equipment":
                    return self._json(_equipment_readiness(db_path, state_path))
                if parsed.path == "/api/evidence-gaps":
                    return self._json(_evidence_gaps(db_path))
                if parsed.path == "/api/walkthrough":
                    query = parse_qs(parsed.query)
                    start = query.get("from", [DEFAULT_FROM])[0]
                    through = query.get("through", [DEFAULT_THROUGH])[0]
                    return self._json(load_walkthrough(db_path, state_path, start, through))
                if parsed.path == "/api/achievements":
                    query = parse_qs(parsed.query)
                    report = load_achievement_report(db_path, state_path, True)
                    page = _page(report["achievements"], query,
                                 ("achievement_id", "name", "category", "description"))
                    report["achievements"] = page.pop("results")
                    report["page"] = page
                    return self._json(report)
                if parsed.path.startswith("/api/achievements/"):
                    achievement_id = unquote(parsed.path.removeprefix("/api/achievements/"))
                    rows = load_achievement_report(db_path, state_path, True)["achievements"]
                    row = next((row for row in rows if row["achievement_id"] == achievement_id), None)
                    if row is None:
                        raise ValueError("Unknown achievement")
                    return self._json(row)
                if parsed.path == "/api/hoarder":
                    query = parse_qs(parsed.query)
                    gaps = query.get("gaps", ["0"])[0] == "1"
                    return self._json(load_hoarder_report(db_path, state_path, gaps))
                if parsed.path == "/api/monsters/coverage":
                    return self._json(load_monster_coverage(db_path, state_path))
                if parsed.path == "/api/monsters":
                    return self._json(_monsters(db_path, state_path, parse_qs(parsed.query)))
                if parsed.path.startswith("/api/monsters/"):
                    query = unquote(parsed.path.removeprefix("/api/monsters/"))
                    report = load_monster_report(db_path, query)
                    report["defeated"] = report["monster"]["monster_id"] in set(
                        _state(state_path).get("completion", {}).get("monster_entries", []))
                    return self._json(report)
                if parsed.path == "/api/monster-hearts":
                    return self._json(_monster_hearts(db_path, parse_qs(parsed.query), state_path))
                if parsed.path.startswith("/api/monster-hearts/"):
                    heart_id = unquote(parsed.path.removeprefix("/api/monster-hearts/"))
                    row = next((row for row in _monster_hearts(db_path, {}, state_path)["hearts"]
                                if row["heart_id"] == heart_id), None)
                    if row is None:
                        raise ValueError("Unknown Monster Heart")
                    row["routes"] = _heart_routes(db_path, row["name"])
                    return self._json(row)
                if parsed.path == "/api/missables":
                    return self._json(_missables(db_path, parse_qs(parsed.query), state_path))
                if parsed.path.startswith("/api/missables/"):
                    missable_id = unquote(parsed.path.removeprefix("/api/missables/"))
                    row = next((row for row in _missables(db_path, {}, state_path)["missables"]
                                if row["missable_id"] == missable_id), None)
                    if row is None:
                        raise ValueError("Unknown missable")
                    return self._json(row)
                if parsed.path == "/api/farms":
                    return self._json(_farms(db_path, parse_qs(parsed.query)))
                if parsed.path.startswith("/api/farms/"):
                    farming_id = unquote(parsed.path.removeprefix("/api/farms/"))
                    row = next((row for row in _farms(db_path, {})["farms"]
                                if row["farming_id"] == farming_id), None)
                    if row is None:
                        raise ValueError("Unknown farm")
                    return self._json(row)
                if parsed.path == "/api/medals":
                    return self._json(_medals(db_path, state_path))
                if parsed.path.startswith("/api/medals/"):
                    number = int(unquote(parsed.path.removeprefix("/api/medals/")))
                    row = next((row for row in _medals(db_path, state_path)["medals"]
                                if row["medal_number"] == number), None)
                    if row is None:
                        raise ValueError("Unknown Mini Medal")
                    return self._json(row)
                if parsed.path == "/api/tablets":
                    return self._json(_tablets(db_path, state_path))
                if parsed.path.startswith("/api/tablets/"):
                    tablet_id = unquote(parsed.path.removeprefix("/api/tablets/"))
                    rows = [row for row in _tablets(db_path, state_path)["fragments"]
                            if row["tablet_id"] == tablet_id]
                    if not rows:
                        raise ValueError("Unknown tablet")
                    return self._json({"tablet_id": tablet_id,
                        "tablet_name": rows[0]["tablet_name"], "fragments": rows})
                if parsed.path == "/api/vocations":
                    payload = _vocations(db_path, state_path, parse_qs(parsed.query))
                    payload["moonlighting"] = _moonlighting(db_path)
                    return self._json(payload)
                if parsed.path.startswith("/api/vocations/"):
                    query = unquote(parsed.path.removeprefix("/api/vocations/"))
                    report = load_vocation_details(db_path, query)
                    vocation_id = report["vocation"]["vocation_id"]
                    report["mastered_by"] = next(row["mastered_by"] for row in
                        _vocations(db_path, state_path, {})["vocations"]
                        if row["vocation_id"] == vocation_id)
                    report["unlock_progress"] = _vocation_unlock_progress(
                        db_path, state_path, vocation_id)
                    report["moonlighting"] = _moonlighting(db_path)
                    return self._json(report)
                if parsed.path == "/api/moonlighting":
                    return self._json(_moonlighting(db_path))
                if parsed.path == "/api/items":
                    return self._json(_items(db_path, state_path, parse_qs(parsed.query)))
                if parsed.path.startswith("/api/items/"):
                    query = unquote(parsed.path.removeprefix("/api/items/"))
                    item, routes = load_item_routes(db_path, query)
                    item["obtained"] = item["item_id"] in set(
                        _state(state_path).get("completion", {}).get("items_obtained", []))
                    return self._json({"item": item, "routes": routes})
                if parsed.path == "/api/conflicts":
                    query = parse_qs(parsed.query)
                    resolved = query.get("include_resolved", ["0"])[0] == "1"
                    rows = load_conflicts(db_path, resolved)
                    return self._json([{"id": row["conflict_id"],
                        "subject": row["subject_key"].replace("_", " "),
                        "predicate": row["predicate"].replace("_", " "),
                        "status": row["status"],
                        "resolution_claim_id": row["resolution_claim_id"],
                        "detection_method": row["detection_method"],
                        "rationale": row["rationale"],
                        "required_evidence": (None if row["status"] == "resolved" else
                            ("Direct in-game capture or patch-scoped map evidence confirming whether Tempest Shield exists in both Sanctum of the Cirrus and Ventus Tower, or which listed route is erroneous."
                             if row["subject_key"] == "item:tempest_shield" else
                             "A current-version capture or continuous video showing the post-Aishe Career Sphere message and the complete Jacqui activation interaction, including the displayed venue name."
                             if row["subject_key"] == "system:moonlighting" else
                             "A direct current-version English in-game Item List, inventory, shop, or acquisition-result capture with the full fan name legible; guide page titles alone are insufficient."
                             if row["subject_key"] == "item:stella_fan" else
                             "Direct current-version in-game or location-specific evidence that addresses the same scope and distinguishes the two claims.")),
                        "claims": [{
                            "id": row[f"claim_{side}_id"],
                            "is_resolution": row[f"claim_{side}_id"] == row["resolution_claim_id"],
                            "value": json.loads(row[f"value_{side}"]),
                            "scope": json.loads(row[f"scope_{side}"]),
                            "confidence": row[f"confidence_{side}"],
                            "verification_status": row[f"verification_status_{side}"],
                            "locator": row[f"locator_{side}"],
                            "source": {
                                "title": row[f"source_title_{side}"],
                                "url": row[f"source_url_{side}"],
                                "updated_at": row[f"source_updated_at_{side}"],
                                "retrieved_at": row[f"source_retrieved_at_{side}"],
                            },
                        } for side in ("a", "b")],
                    } for row in rows])
                if parsed.path == "/api/sources":
                    return self._json(_sources(db_path, parse_qs(parsed.query)))
                if parsed.path.startswith("/api/sources/"):
                    source_id = unquote(parsed.path.removeprefix("/api/sources/"))
                    row = next((row for row in _sources(db_path, {"q": [source_id], "limit": ["200"]})["sources"]
                                if row["source_id"] == source_id), None)
                    if row is None:
                        raise ValueError("Unknown source")
                    return self._json(row)
                if parsed.path == "/api/seeds":
                    return self._json(_seeds(db_path, parse_qs(parsed.query)))
                if parsed.path.startswith("/api/seeds/"):
                    seed_id = unquote(parsed.path.removeprefix("/api/seeds/"))
                    row = next((row for row in _seeds(db_path, {"q": [seed_id], "limit": ["200"]})["seeds"]
                                if row["seed_id"] == seed_id), None)
                    if row is None:
                        raise ValueError("Unknown seed mechanic")
                    return self._json(row)
                if parsed.path.startswith("/api/"):
                    return self._error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
                return self._static(parsed.path)
            except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as error:
                return self._error(_client_error_status(error), str(error))

        def do_POST(self):
            if not self._require_pairing():
                return
            path = urlparse(self.path).path
            if path not in ("/api/progress", "/api/state-restore"):
                return self._error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY_BYTES:
                    return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Invalid body size")
                payload = json.loads(self.rfile.read(length))
                if path == "/api/state-restore":
                    if payload.get("confirmation") != "RESTORE":
                        raise ValueError("Restore requires explicit RESTORE confirmation")
                    restored = payload.get("state")
                    if not isinstance(restored, dict):
                        raise ValueError("state must be a JSON object")
                    with state_write_lock:
                        current = _load_state(state_path)
                        for key in ("schema_version", "player", "game"):
                            if restored.get(key) != current.get(key):
                                raise ValueError(f"Backup {key} does not match this guide")
                        temporary = None
                        try:
                            with tempfile.NamedTemporaryFile(
                                mode="w", encoding="utf-8", dir=state_path.parent,
                                prefix=".dq7-restore-", suffix=".json", delete=False,
                            ) as handle:
                                json.dump(restored, handle, ensure_ascii=False)
                                temporary = Path(handle.name)
                            validated = _load_state(temporary)
                        finally:
                            if temporary is not None and temporary.exists():
                                temporary.unlink()
                        recovery = state_path.with_name(
                            f"{state_path.stem}.before-restore-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
                        )
                        recovery.write_bytes(state_path.read_bytes())
                        _save_state(state_path, validated)
                        dashboard = _dashboard(db_path, state_path)
                    return self._json({"message": "Progress restored.",
                                       "recovery_file": recovery.name,
                                       "dashboard": dashboard})
                command, values = payload.get("command"), payload.get("values")
                if command not in ALLOWED_PROGRESS_COMMANDS:
                    raise ValueError("Unsupported progress command")
                if not isinstance(values, list) or not values or any(
                    not isinstance(value, (str, int)) or isinstance(value, bool)
                    for value in values
                ):
                    raise ValueError("values must be a non-empty list of strings or integers")
                with state_write_lock:
                    message = update_progress(state_path, db_path, command, [str(v) for v in values])
                    dashboard = _dashboard(db_path, state_path)
                return self._json({"message": message, "dashboard": dashboard})
            except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                return self._error(_client_error_status(error), str(error))

        def do_PATCH(self):
            if not self._require_pairing():
                return
            path = urlparse(self.path).path
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY_BYTES:
                    return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Invalid body size")
                payload = json.loads(self.rfile.read(length))
                with state_write_lock:
                    if path == "/api/progress":
                        message = _record_ui_progress(db_path, state_path, payload)
                    elif path.startswith("/api/equipment/accessories/"):
                        message = _record_accessory_progress(db_path, state_path, path, payload)
                    elif any(path.startswith(prefix) for prefix in (
                        "/api/items/", "/api/tablets/", "/api/achievements/",
                        "/api/vocations/", "/api/checkpoints/",
                        "/api/missables/", "/api/monster-hearts/",
                    )):
                        message = _record_resource_progress(db_path, state_path, path, payload)
                    else:
                        return self._error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
                return self._json({"message": message})
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                return self._error(_client_error_status(error), str(error))

        def _static(self, request_path):
            relative = "index.html" if request_path == "/" else unquote(request_path).lstrip("/")
            root = static_dir.resolve()
            candidate = (root / relative).resolve()
            if root not in candidate.parents and candidate != root:
                return self._error(HTTPStatus.FORBIDDEN, "Invalid static path")
            if not candidate.is_file():
                return self._error(HTTPStatus.NOT_FOUND, "Static asset not found")
            body = candidate.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            if candidate.name == "service-worker.js":
                self.send_header("Service-Worker-Allowed", "/")
                self.send_header("Cache-Control", "no-cache")
            elif candidate.suffix in (".html", ".json"):
                self.send_header("Cache-Control", "no-cache")
            else:
                self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    return GuideHandler


def create_server(host="127.0.0.1", port=8765, db_path=DEFAULT_DB,
                  state_path=DEFAULT_STATE, static_dir=DEFAULT_STATIC,
                  pairing_token: str | None = None, trust_loopback: bool = True):
    return ThreadingHTTPServer(
        (host, port), make_handler(db_path, state_path, static_dir, pairing_token,
                                  trust_loopback)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--lan", action="store_true",
                        help="Let trusted devices on the local network open and edit the guide")
    parser.add_argument("--rotate-pairing", action="store_true",
                        help="Replace the saved phone credential and revoke previously paired phones")
    parser.add_argument("--pairing-file", type=Path, default=_default_pairing_file(),
                        help=argparse.SUPPRESS)
    parser.add_argument("--require-pairing-everywhere", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--static", type=Path, default=DEFAULT_STATIC)
    parser.add_argument("--open-browser", action="store_true",
                        help="Open the guide in the default browser after starting")
    args = parser.parse_args()
    if args.lan:
        if args.host != "127.0.0.1":
            parser.error("--lan cannot be combined with --host")
        args.host = "0.0.0.0"
    elif args.rotate_pairing:
        parser.error("--rotate-pairing requires --lan")
    pairing_token = (_load_or_create_pairing_token(args.pairing_file, args.rotate_pairing)
                     if args.lan else None)
    server = create_server(args.host, args.port, args.db, args.state, args.static,
                           pairing_token, not args.require_pairing_everywhere)
    local_url, phone_urls = _access_urls(args.host, server.server_port, pairing_token)
    print(f"DQ7 guide (this device): {local_url}", flush=True)
    if args.lan:
        print("PHONE MODE: only a browser paired with this Deck's private URL can edit progress.",
              flush=True)
        if phone_urls:
            for phone_url in phone_urls:
                print(f"DQ7 guide (phone): {phone_url}", flush=True)
        else:
            print("Phone address unavailable. Connect the Deck to Wi-Fi, then restart.", flush=True)
        print("Bookmark the pairing URL and keep it private. Use --rotate-pairing to revoke it.",
              flush=True)
        print("Keep this window open. Ctrl+C stops sharing.",
              flush=True)
    if args.open_browser:
        webbrowser.open(local_url)
    def stop_on_signal(_signal_number, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop_on_signal)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
