#!/usr/bin/env python3
"""Record explicit player-reported completion progress."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


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
    return state


def _save_state(state_path: Path, state: dict) -> None:
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


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
        elif command == "medal-found":
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
            state["completion"]["mini_medals_found"] = sorted(set(current) | set(numbers))
            message = f"Recorded Mini Medal number(s): {', '.join(map(str, numbers))}."
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
        elif command in ("monster-defeated", "monster-undo"):
            known = {row[0] for row in connection.execute("SELECT monster_id FROM monsters")}
            invalid = sorted(set(values) - known)
            if invalid:
                raise ValueError(f"Unknown monster ID(s): {invalid}")
            entries = set(state["completion"]["monster_entries"])
            if command == "monster-defeated":
                entries.update(values)
                message = f"Recorded monster(s): {', '.join(values)}."
            else:
                entries.difference_update(values)
                message = f"Reopened monster(s): {', '.join(values)}."
            state["completion"]["monster_entries"] = sorted(entries)
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
    for name in ("tablet-found", "tablet-undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs="+", metavar="FRAGMENT_ID")
    for name in ("vocation-mastered", "vocation-undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs="+", metavar="CHARACTER_OR_VOCATION_ID")
    for name in ("monster-defeated", "monster-undo"):
        progress = subparsers.add_parser(name)
        progress.add_argument("values", nargs="+", metavar="MONSTER_ID")
    args = parser.parse_args()
    try:
        print(update_progress(args.state, args.db, args.command, args.values))
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
