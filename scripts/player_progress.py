#!/usr/bin/env python3
"""Record explicit player-reported completion progress."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"
DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"


def _load_state(state_path: Path) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    completed = state.get("completion", {}).get("obligations_completed")
    if not isinstance(completed, list) or any(not isinstance(value, str) for value in completed):
        raise ValueError("completion.obligations_completed must be a list of strings")
    achievements = state.get("completion", {}).get("achievements_unlocked")
    if not isinstance(achievements, list) or any(
        not isinstance(value, str) for value in achievements
    ):
        raise ValueError("completion.achievements_unlocked must be a list of strings")
    items = state.get("completion", {}).get("items_obtained")
    if not isinstance(items, list) or any(not isinstance(value, str) for value in items):
        raise ValueError("completion.items_obtained must be a list of strings")
    fragments = state.get("completion", {}).get("tablet_fragments")
    if not isinstance(fragments, list) or any(
        not isinstance(value, str) for value in fragments
    ):
        raise ValueError("completion.tablet_fragments must be a list of strings")
    monsters = state.get("completion", {}).get("monster_entries")
    if not isinstance(monsters, list) or any(
        not isinstance(value, str) for value in monsters
    ):
        raise ValueError("completion.monster_entries must be a list of strings")
    hearts = state.get("completion", {}).get("monster_hearts_owned")
    if hearts is not None and (
        not isinstance(hearts, list)
        or any(not isinstance(value, str) for value in hearts)
    ):
        raise ValueError("completion.monster_hearts_owned must be a list of strings when present")
    for field in ("missables_completed", "missables_missed"):
        values = state.get("completion", {}).get(field)
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"completion.{field} must be a list of strings")
    members = state.get("party", {}).get("members")
    if not isinstance(members, dict):
        raise ValueError("party.members must be an object")
    for character, member in members.items():
        mastery = member.get("vocation_mastery") if isinstance(member, dict) else None
        if not isinstance(mastery, dict) or any(
            not isinstance(vocation_id, str) or value is not True
            for vocation_id, value in mastery.items()
        ):
            raise ValueError(
                f"party.members.{character}.vocation_mastery must map vocation IDs to true"
            )
        level = member.get("level")
        if level is not None and (not isinstance(level, int) or isinstance(level, bool) or level < 1):
            raise ValueError(f"party.members.{character}.level must be a positive integer or null")
        for field in ("primary_vocation", "secondary_vocation"):
            value = member.get(field)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"party.members.{character}.{field} must be a vocation ID or null")
        equipment = member.get("equipment")
        if not isinstance(equipment, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in equipment.items()
        ):
            raise ValueError(f"party.members.{character}.equipment must map slot names to item IDs")
    return state


def _save_state(state_path: Path, state: dict) -> None:
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=state_path.parent,
            prefix=f".{state_path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            handle.write(payload)
            handle.flush()
            temporary_path = Path(handle.name)
        temporary_path.replace(state_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _checkpoint_exists(connection: sqlite3.Connection, checkpoint_id: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,)
    ).fetchone() is not None


def _obligation_for_step(
    connection: sqlite3.Connection, checkpoint_id: str, display_order: int
) -> str:
    row = connection.execute(
        """SELECT obligation_id FROM checkpoint_obligations
        WHERE checkpoint_id = ? AND display_order = ?""",
        (checkpoint_id, display_order),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown checklist step: {checkpoint_id} {display_order}")
    return row["obligation_id"]


def _resolve_monsters(connection: sqlite3.Connection, values: list[str]) -> list[str]:
    resolved = []
    for value in values:
        number = value.removeprefix("#")
        if number.isdigit():
            rows = connection.execute(
                "SELECT monster_id FROM monsters WHERE source_ordinal = ?",
                (int(number),),
            ).fetchall()
        else:
            rows = connection.execute(
                """SELECT monster_id FROM monsters
                WHERE monster_id = ? OR lower(english_name) = lower(?)
                ORDER BY source_ordinal""",
                (value, value),
            ).fetchall()
        if not rows:
            raise ValueError(f"Unknown monster: {value}")
        if len(rows) > 1:
            raise ValueError(f"Ambiguous monster name: {value}; use its Monster List number")
        resolved.append(rows[0]["monster_id"])
    return resolved


def update_progress(
    state_path: Path,
    db_path: Path,
    command: str,
    values: list[str],
) -> str:
    state = _load_state(state_path)
    with _connect(db_path) as connection:
        if command == "checkpoint":
            checkpoint_id = values[0]
            if not _checkpoint_exists(connection, checkpoint_id):
                raise ValueError(f"Unknown checkpoint: {checkpoint_id}")
            state["story"]["checkpoint_id"] = checkpoint_id
            message = f"Checkpoint set to {checkpoint_id}."
        elif command == "party-setup":
            payload = json.loads(values[0])
            if not isinstance(payload, dict) or not isinstance(payload.get("members"), list):
                raise ValueError("Party setup must contain a members list")
            checkpoint_id = payload.get("checkpoint_id")
            if checkpoint_id is not None and (not isinstance(checkpoint_id, str)
                                               or not _checkpoint_exists(connection, checkpoint_id)):
                raise ValueError(f"Unknown checkpoint: {checkpoint_id}")
            members = state["party"]["members"]
            known_vocations = {row["vocation_id"]: row["exclusive_character"] for row in
                               connection.execute("SELECT vocation_id, exclusive_character FROM vocations")}
            seen = set()
            normalized = []
            for row in payload["members"]:
                if not isinstance(row, dict) or row.get("name") not in members:
                    raise ValueError("Party setup contains an unknown member")
                name = row["name"]
                if name in seen:
                    raise ValueError(f"Duplicate party member: {name}")
                seen.add(name)
                level = row.get("level")
                if level in (None, "", "unknown"):
                    level = None
                else:
                    level = int(level)
                    if level < 1:
                        raise ValueError("Level must be a positive integer or unknown")
                primary = row.get("primary_vocation")
                secondary = row.get("secondary_vocation")
                primary = None if primary in (None, "", "unknown") else primary
                secondary = None if secondary in (None, "", "unknown") else secondary
                for vocation_id in (primary, secondary):
                    if vocation_id is None:
                        continue
                    if vocation_id not in known_vocations:
                        raise ValueError(f"Unknown vocation ID: {vocation_id}")
                    if known_vocations[vocation_id] not in (None, name):
                        raise ValueError(f"Vocation unavailable to {name}: {vocation_id}")
                normalized.append((name, level, primary, secondary))
            active = payload.get("active")
            if not isinstance(active, list) or any(name not in seen for name in active):
                raise ValueError("Active party must contain only submitted members")
            if len(active) != len(set(active)):
                raise ValueError("Active party contains a duplicate member")
            state["story"]["checkpoint_id"] = checkpoint_id
            state["party"]["active"] = active
            for name, level, primary, secondary in normalized:
                members[name]["level"] = level
                members[name]["primary_vocation"] = primary
                members[name]["secondary_vocation"] = secondary
            message = f"Recorded checkpoint and {len(active)} active party members."
        elif command in ("medal-found", "medal-undo"):
            numbers = [int(value) for value in values]
            known = {
                row[0] for row in connection.execute(
                    "SELECT medal_number FROM mini_medal_locations"
                )
            }
            invalid = [number for number in numbers if number not in known]
            if invalid:
                raise ValueError(f"Unknown Mini Medal number(s): {invalid}")
            current = state["completion"]["mini_medals_found"]
            if not isinstance(current, list) or any(
                not isinstance(number, int) or isinstance(number, bool) for number in current
            ):
                raise ValueError("completion.mini_medals_found must be a list of integers")
            found = set(current)
            if command == "medal-found":
                found.update(numbers)
                message = f"Recorded Mini Medal number(s): {', '.join(map(str, numbers))}."
            else:
                found.difference_update(numbers)
                message = f"Reopened Mini Medal number(s): {', '.join(map(str, numbers))}."
            state["completion"]["mini_medals_found"] = sorted(found)
        elif command == "medal-count":
            count = int(values[0])
            if count < 0:
                raise ValueError("Mini Medal count must be non-negative")
            state["completion"]["mini_medal_count"] = count
            message = f"Mini Medal count set to {count}."
        elif command in ("done", "undo"):
            checkpoint_id, order_text = values
            if not _checkpoint_exists(connection, checkpoint_id):
                raise ValueError(f"Unknown checkpoint: {checkpoint_id}")
            obligation_id = _obligation_for_step(connection, checkpoint_id, int(order_text))
            completed = set(state["completion"]["obligations_completed"])
            if command == "done":
                completed.add(obligation_id)
                message = f"Completed {checkpoint_id} step {order_text}."
            else:
                completed.discard(obligation_id)
                message = f"Reopened {checkpoint_id} step {order_text}."
            state["completion"]["obligations_completed"] = sorted(completed)
        elif command in ("achievement-unlocked", "achievement-undo"):
            known = {
                row[0] for row in connection.execute(
                    "SELECT achievement_id FROM achievements"
                )
            }
            invalid = sorted(set(values) - known)
            if invalid:
                raise ValueError(f"Unknown achievement ID(s): {invalid}")
            unlocked = set(state["completion"]["achievements_unlocked"])
            if command == "achievement-unlocked":
                unlocked.update(values)
                message = f"Recorded achievement(s): {', '.join(values)}."
            else:
                unlocked.difference_update(values)
                message = f"Reopened achievement(s): {', '.join(values)}."
            state["completion"]["achievements_unlocked"] = sorted(unlocked)
        elif command in ("item-obtained", "item-undo"):
            known = {row[0] for row in connection.execute("SELECT item_id FROM items")}
            invalid = sorted(set(values) - known)
            if invalid:
                raise ValueError(f"Unknown item ID(s): {invalid}")
            obtained = set(state["completion"]["items_obtained"])
            if command == "item-obtained":
                obtained.update(values)
                message = f"Recorded item(s): {', '.join(values)}."
            else:
                obtained.difference_update(values)
                message = f"Reopened item(s): {', '.join(values)}."
            state["completion"]["items_obtained"] = sorted(obtained)
        elif command in ("missable-completed", "missable-undo"):
            links = {row[0]: row[1] for row in connection.execute(
                "SELECT missable_id, obligation_id FROM missables")}
            known = set(links)
            invalid = sorted(set(values) - known)
            if invalid:
                raise ValueError(f"Unknown missable ID(s): {invalid}")
            completed = set(state["completion"]["missables_completed"])
            missed = set(state["completion"]["missables_missed"])
            if command == "missable-completed":
                completed.update(values)
                missed.difference_update(values)
                state["completion"]["obligations_completed"] = sorted(
                    set(state["completion"]["obligations_completed"])
                    | {links[value] for value in values if links[value]})
                message = f"Recorded completed missable(s): {', '.join(values)}."
            else:
                completed.difference_update(values)
                state["completion"]["obligations_completed"] = sorted(
                    set(state["completion"]["obligations_completed"])
                    - {links[value] for value in values if links[value]})
                message = f"Reopened missable(s): {', '.join(values)}."
            state["completion"]["missables_completed"] = sorted(completed)
            state["completion"]["missables_missed"] = sorted(missed)
        elif command in ("tablet-found", "tablet-undo"):
            known = {
                row[0] for row in connection.execute(
                    "SELECT fragment_id FROM tablet_fragments"
                )
            }
            invalid = sorted(set(values) - known)
            if invalid:
                raise ValueError(f"Unknown tablet fragment ID(s): {invalid}")
            found = set(state["completion"]["tablet_fragments"])
            if command == "tablet-found":
                found.update(values)
                message = f"Recorded tablet fragment(s): {', '.join(values)}."
            else:
                found.difference_update(values)
                message = f"Reopened tablet fragment(s): {', '.join(values)}."
            state["completion"]["tablet_fragments"] = sorted(found)
        elif command in ("vocation-mastered", "vocation-undo"):
            character, *vocation_ids = values
            members = state["party"]["members"]
            if not vocation_ids:
                raise ValueError("At least one vocation ID is required")
            if character not in members:
                raise ValueError(f"Unknown party member: {character}")
            known = {
                row["vocation_id"]: row["exclusive_character"]
                for row in connection.execute(
                    "SELECT vocation_id, exclusive_character FROM vocations"
                )
            }
            invalid = sorted(set(vocation_ids) - set(known))
            if invalid:
                raise ValueError(f"Unknown vocation ID(s): {invalid}")
            ineligible = sorted(
                vocation_id for vocation_id in vocation_ids
                if known[vocation_id] not in (None, character)
            )
            if ineligible:
                raise ValueError(f"Vocation(s) unavailable to {character}: {ineligible}")
            mastery = members[character]["vocation_mastery"]
            if command == "vocation-mastered":
                mastery.update({vocation_id: True for vocation_id in vocation_ids})
                message = f"Recorded {character} mastery: {', '.join(vocation_ids)}."
            else:
                for vocation_id in vocation_ids:
                    mastery.pop(vocation_id, None)
                message = f"Reopened {character} mastery: {', '.join(vocation_ids)}."
        elif command == "party-level":
            character, level_text = values
            members = state["party"]["members"]
            if character not in members:
                raise ValueError(f"Unknown party member: {character}")
            if str(level_text).casefold() == "unknown":
                members[character]["level"] = None
                message = f"Cleared {character} level to unknown."
            else:
                level = int(level_text)
                if level < 1:
                    raise ValueError("Level must be a positive integer or unknown")
                members[character]["level"] = level
                message = f"Recorded {character} level: {level}."
        elif command == "party-vocations":
            character, primary_text, secondary_text = values
            members = state["party"]["members"]
            if character not in members:
                raise ValueError(f"Unknown party member: {character}")
            known = {row["vocation_id"]: row["exclusive_character"] for row in
                     connection.execute("SELECT vocation_id, exclusive_character FROM vocations")}
            selected = [value for value in (primary_text, secondary_text)
                        if str(value).casefold() != "unknown"]
            invalid = sorted(set(selected) - set(known))
            if invalid:
                raise ValueError(f"Unknown vocation ID(s): {invalid}")
            ineligible = sorted(value for value in selected
                                if known[value] not in (None, character))
            if ineligible:
                raise ValueError(f"Vocation(s) unavailable to {character}: {ineligible}")
            members[character]["primary_vocation"] = (None if str(primary_text).casefold() == "unknown" else primary_text)
            members[character]["secondary_vocation"] = (None if str(secondary_text).casefold() == "unknown" else secondary_text)
            message = f"Recorded {character} current vocations."
        elif command == "accessory-set":
            character, slot, item_text = values
            members = state["party"]["members"]
            if character not in members:
                raise ValueError(f"Unknown party member: {character}")
            if slot not in ("accessory_1", "accessory_2"):
                raise ValueError("Accessory slot must be accessory_1 or accessory_2")
            equipment = members[character]["equipment"]
            if str(item_text).casefold() == "unknown":
                equipment.pop(slot, None)
                message = f"Cleared {character} {slot} to unknown."
            else:
                item_id = item_text
                redirect = connection.execute(
                    "SELECT canonical_item_id FROM item_identity_redirects WHERE legacy_item_id=?",
                    (item_id,),
                ).fetchone()
                if redirect:
                    item_id = redirect["canonical_item_id"]
                row = connection.execute(
                    """SELECT i.item_id, c.name AS category, ec.can_equip,
                        a.agreement_status, mh.heart_id
                    FROM items i JOIN item_categories c USING(category_id)
                    LEFT JOIN equipment_compatibility_audits a USING(item_id)
                    LEFT JOIN equipment_compatibility ec
                      ON ec.item_id=i.item_id AND ec.character_name=?
                    LEFT JOIN monster_hearts mh ON mh.name=i.name
                    WHERE i.item_id=?""",
                    (character, item_id),
                ).fetchone()
                if row is None:
                    raise ValueError(f"Unknown item ID: {item_id}")
                if row["category"] != "Accessories":
                    raise ValueError("Only accessory-slot writes are supported")
                if row["agreement_status"] != "two_source_agreement" or row["can_equip"] != 1:
                    raise ValueError(f"Compatibility is not verified for {character}: {item_id}")
                item_owned = item_id in set(state["completion"]["items_obtained"])
                heart_owned = (row["heart_id"] is not None and
                               row["heart_id"] in set(state["completion"].get("monster_hearts_owned", [])))
                if not (item_owned or heart_owned):
                    raise ValueError(f"Item is not explicitly owned: {item_id}")
                other_slot = "accessory_2" if slot == "accessory_1" else "accessory_1"
                if equipment.get(other_slot) == item_id:
                    raise ValueError("Duplicate accessory IDs are not supported")
                equipment[slot] = item_id
                message = f"Recorded {character} {slot}: {item_id}."
        elif command in ("monster-defeated", "monster-undo"):
            monster_ids = _resolve_monsters(connection, values)
            entries = set(state["completion"]["monster_entries"])
            if command == "monster-defeated":
                entries.update(monster_ids)
                message = f"Recorded monster(s): {', '.join(monster_ids)}."
            else:
                entries.difference_update(monster_ids)
                message = f"Reopened monster(s): {', '.join(monster_ids)}."
            state["completion"]["monster_entries"] = sorted(entries)
        elif command in ("heart-obtained", "heart-undo"):
            known = {
                row[0] for row in connection.execute(
                    "SELECT heart_id FROM monster_hearts"
                )
            }
            invalid = sorted(set(values) - known)
            if invalid:
                raise ValueError(f"Unknown Monster Heart ID(s): {invalid}")
            # Absence means ownership has never been reported. The first explicit
            # mutation starts the dedicated ledger; story progress never does.
            owned = set(state["completion"].get("monster_hearts_owned", []))
            if command == "heart-obtained":
                owned.update(values)
                message = f"Recorded Monster Heart(s): {', '.join(values)}."
            else:
                owned.difference_update(values)
                message = f"Reopened Monster Heart(s): {', '.join(values)}."
            state["completion"]["monster_hearts_owned"] = sorted(owned)
        else:
            raise ValueError(f"Unknown progress command: {command}")
    _save_state(state_path, state)
    return message


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    subparsers = parser.add_subparsers(dest="command", required=True)
    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint.add_argument("values", nargs=1)
    medal_found = subparsers.add_parser("medal-found")
    medal_found.add_argument("values", nargs="+")
    medal_undo = subparsers.add_parser("medal-undo")
    medal_undo.add_argument("values", nargs="+")
    medal_count = subparsers.add_parser("medal-count")
    medal_count.add_argument("values", nargs=1)
    for name in ("done", "undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs=2, metavar=("CHECKPOINT", "STEP"))
    for name in ("achievement-unlocked", "achievement-undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs="+", metavar="ACHIEVEMENT_ID")
    for name in ("item-obtained", "item-undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs="+", metavar="ITEM_ID")
    for name in ("missable-completed", "missable-undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs="+", metavar="MISSABLE_ID")
    for name in ("tablet-found", "tablet-undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs="+", metavar="FRAGMENT_ID")
    for name in ("vocation-mastered", "vocation-undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs="+", metavar="CHARACTER_OR_VOCATION_ID")
    for name in ("monster-defeated", "monster-undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs="+", metavar="MONSTER")
    for name in ("heart-obtained", "heart-undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs="+", metavar="HEART_ID")
    progress = subparsers.add_parser("accessory-set")
    progress.add_argument("values", nargs=3, metavar=("CHARACTER", "SLOT", "ITEM_ID_OR_UNKNOWN"))
    args = parser.parse_args()
    try:
        print(update_progress(args.state, args.db, args.command, args.values))
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
