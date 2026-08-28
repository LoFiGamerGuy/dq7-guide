#!/usr/bin/env python3
"""Dependency-free local JSON API and static server for the DQ7 guide."""

from __future__ import annotations

import argparse
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, unquote, urlparse
import webbrowser

from achievement_report import load_achievement_report
from checkpoint_report import load_report
from conflict_report import load_conflicts
from early_walkthrough import DEFAULT_FROM, DEFAULT_THROUGH, load_walkthrough
from hoarder_report import load_hoarder_report
from item_report import load_item_routes
from monster_report import load_monster_coverage, load_monster_report
from player_progress import update_progress
from vocation_report import load_vocation_details


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"
DEFAULT_STATE = ROOT / "player" / "ryan-save-state.json"
DEFAULT_STATIC = ROOT / "web"
MAX_BODY_BYTES = 64 * 1024
ALLOWED_PROGRESS_COMMANDS = {
    "checkpoint", "medal-found", "medal-count", "done", "undo",
    "achievement-unlocked", "achievement-undo", "item-obtained", "item-undo",
    "tablet-found", "tablet-undo", "monster-defeated", "monster-undo",
    "vocation-mastered", "vocation-undo",
}


def _checkpoints(db_path: Path) -> list[dict]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(
            """SELECT checkpoint_id, sequence_no, name, time_period, region,
                safe_exit_condition, coverage_status
            FROM checkpoints ORDER BY sequence_no"""
        )]


def _rows(db_path: Path, sql: str) -> list[dict]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(sql)]


def _state(state_path: Path) -> dict:
    return json.loads(state_path.read_text(encoding="utf-8"))


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


def _monster_hearts(db_path: Path, query: dict) -> dict:
    rows = _rows(db_path, """SELECT h.heart_id, h.name, h.effect_text,
        h.available_from_checkpoint_id, c.name AS available_checkpoint,
        h.availability_notes, h.confidence, h.verification_status,
        h.source_id, s.title AS source_title, s.url AS source_url, h.locator
        FROM monster_hearts h
        LEFT JOIN checkpoints c ON c.checkpoint_id=h.available_from_checkpoint_id
        JOIN sources s USING(source_id)
        ORDER BY COALESCE(c.sequence_no, 999), h.name""")
    page = _page(rows, query, ("heart_id", "name", "effect_text",
        "available_checkpoint", "availability_notes"))
    page["hearts"] = page.pop("results")
    return page


def _missables(db_path: Path, query: dict) -> dict:
    rows = _rows(db_path, """SELECT m.missable_id, m.name, m.available_from,
        m.unavailable_after, m.consequence, m.severity, m.confidence,
        m.verification_status, m.source_id, s.title AS source_title,
        s.url AS source_url, m.locator
        FROM missables m JOIN sources s USING(source_id)
        ORDER BY CASE WHEN m.unavailable_after IS NULL THEN 1 ELSE 0 END, m.name""")
    for row in rows:
        row["window_status"] = ("verified" if row["available_from"] and
            row["unavailable_after"] and
            row["verification_status"].startswith("source_checked")
            else "unresolved")
        row["provenance_gap"] = not bool(row["locator"])
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
        row["farm_type"] = ("exp" if "metal" in target or "jewel" in target
            else "seeds" if "seed" in target else "other")
        row["rate_status"] = "numeric_unpublished"
        row["provenance_gap"] = False
        row["strategy_kind"] = "attributed_strategy" if row["strategy"] else None
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
    completion = _state(state_path).get("completion", {})
    completed_actions = set(completion.get("obligations_completed", []))
    found_medals = set(completion.get("mini_medals_found", []))
    defeated_monsters = set(completion.get("monster_entries", []))
    checkpoint = block["checkpoint"]
    medals = block["medals_now"] + block["medals_backtrack"] + block["medals_later"]
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
    return {
        "id": checkpoint_id, "name": checkpoint["name"],
        "time_period": checkpoint["time_period"], "region": checkpoint["region"],
        "stop_warnings": [row["action"] for row in block["stops"]],
        "actions": [{
            "id": row["obligation_id"], "title": f"Step {row['display_order']}",
            "action": row["action"], "completed": row["obligation_id"] in completed_actions,
            "required": bool(row["required_for_100_percent"]),
        } for row in block["now"]],
        "advice": [{
            "id": row["advice_id"], "type": row["advice_type"],
            "subject": row["subject"], "text": row["advice_text"],
            "goal": row["recommendation_goal"],
            "decision_group": ("optional_grind" if row["advice_type"] == "grind"
                               else "completion_safe" if row["recommendation_goal"] in ("completion_safe", "both")
                               else "strongest_now"),
        } for row in block["advice"]],
        "medals": [{"number": row["medal_number"], "location": row["location"],
                     "detail": row["detail"], "found": row["medal_number"] in found_medals} for row in medals],
        "monsters": [{"id": row["monster_id"], "ordinal": row["source_ordinal"],
                       "name": row["english_name"], "location": row["locations"],
                       "drop": ", ".join(drops[row["monster_id"]]) or None,
                       "defeated": row["monster_id"] in defeated_monsters} for row in block["monsters"]],
        "safe_condition": checkpoint["safe_exit_condition"],
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
    return {
        "actions": {"display": f"{len(completion.get('obligations_completed', []))} recorded"},
        "medals": None if medals is None else {"display": f"{medals} / 100"},
        "items": {"display": f"{hoarder['obtained_count']} / {hoarder['total']}"},
        "monsters": {"display": f"{monsters['defeated']} / {monsters['total']}"},
        "vocations": {"display": f"{len(mastered)} / 26"},
        "achievements": {"display": f"{achievements['unlocked_count']} / {achievements['total']}"},
        "open_work": [{"title": "Player checkpoint", "detail": state.get("story", {}).get("checkpoint_id") or "Unknown — select your current checkpoint"}],
    }


def _dashboard_view(db_path: Path, state_path: Path) -> dict:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    checkpoint_id = state.get("story", {}).get("checkpoint_id") or DEFAULT_FROM
    checkpoint = _checkpoint_view(db_path, state_path, checkpoint_id)
    progress = _progress(db_path, state_path)
    sequence = next(row["sequence_no"] for row in _checkpoints(db_path) if row["checkpoint_id"] == checkpoint_id)
    return {
        "checkpoint": {"id": checkpoint_id, "sequence_label": f"{sequence:02d} / 33"},
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
        if not completed:
            raise ValueError("Mini Medal removal is not supported; correct the state file explicitly")
        return update_progress(state_path, db_path, "medal-found", [str(identifier)])
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
    raise ValueError("Unsupported resource mutation")


def make_handler(db_path: Path, state_path: Path, static_dir: Path):
    db_path, state_path, static_dir = map(Path, (db_path, state_path, static_dir))

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

        def _error(self, status, message):
            self._json({"error": message}, status)

        def do_GET(self):
            parsed = urlparse(self.path)
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
                    return self._json(_monster_hearts(db_path, parse_qs(parsed.query)))
                if parsed.path.startswith("/api/monster-hearts/"):
                    heart_id = unquote(parsed.path.removeprefix("/api/monster-hearts/"))
                    row = next((row for row in _monster_hearts(db_path, {})["hearts"]
                                if row["heart_id"] == heart_id), None)
                    if row is None:
                        raise ValueError("Unknown Monster Heart")
                    return self._json(row)
                if parsed.path == "/api/missables":
                    return self._json(_missables(db_path, parse_qs(parsed.query)))
                if parsed.path.startswith("/api/missables/"):
                    missable_id = unquote(parsed.path.removeprefix("/api/missables/"))
                    row = next((row for row in _missables(db_path, {})["missables"]
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
                    return self._json(_vocations(db_path, state_path, parse_qs(parsed.query)))
                if parsed.path.startswith("/api/vocations/"):
                    query = unquote(parsed.path.removeprefix("/api/vocations/"))
                    report = load_vocation_details(db_path, query)
                    vocation_id = report["vocation"]["vocation_id"]
                    report["mastered_by"] = next(row["mastered_by"] for row in
                        _vocations(db_path, state_path, {})["vocations"]
                        if row["vocation_id"] == vocation_id)
                    return self._json(report)
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
                        "detection_method": row["detection_method"],
                        "rationale": row["rationale"],
                        "claims": [{
                            "id": row[f"claim_{side}_id"],
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
                if parsed.path.startswith("/api/"):
                    return self._error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
                return self._static(parsed.path)
            except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as error:
                return self._error(HTTPStatus.BAD_REQUEST, str(error))

        def do_POST(self):
            if urlparse(self.path).path != "/api/progress":
                return self._error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY_BYTES:
                    return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Invalid body size")
                payload = json.loads(self.rfile.read(length))
                command, values = payload.get("command"), payload.get("values")
                if command not in ALLOWED_PROGRESS_COMMANDS:
                    raise ValueError("Unsupported progress command")
                if not isinstance(values, list) or not values or any(
                    not isinstance(value, (str, int)) or isinstance(value, bool)
                    for value in values
                ):
                    raise ValueError("values must be a non-empty list of strings or integers")
                message = update_progress(state_path, db_path, command, [str(v) for v in values])
                return self._json({"message": message, "dashboard": _dashboard(db_path, state_path)})
            except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                return self._error(HTTPStatus.BAD_REQUEST, str(error))

        def do_PATCH(self):
            path = urlparse(self.path).path
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY_BYTES:
                    return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Invalid body size")
                payload = json.loads(self.rfile.read(length))
                if path == "/api/progress":
                    message = _record_ui_progress(db_path, state_path, payload)
                elif any(path.startswith(prefix) for prefix in (
                    "/api/items/", "/api/tablets/", "/api/achievements/",
                    "/api/vocations/", "/api/checkpoints/",
                )):
                    message = _record_resource_progress(db_path, state_path, path, payload)
                else:
                    return self._error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
                return self._json({"message": message})
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                return self._error(HTTPStatus.BAD_REQUEST, str(error))

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
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    return GuideHandler


def create_server(host="127.0.0.1", port=8765, db_path=DEFAULT_DB,
                  state_path=DEFAULT_STATE, static_dir=DEFAULT_STATIC):
    return ThreadingHTTPServer((host, port), make_handler(db_path, state_path, static_dir))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--static", type=Path, default=DEFAULT_STATIC)
    parser.add_argument("--open-browser", action="store_true",
                        help="Open the guide in the default browser after starting")
    args = parser.parse_args()
    server = create_server(args.host, args.port, args.db, args.state, args.static)
    url = f"http://{args.host}:{server.server_port}"
    print(f"DQ7 guide: {url}")
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
