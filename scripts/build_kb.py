#!/usr/bin/env python3
"""Build the reproducible DQ7 Reimagined SQLite knowledge base."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "dq7_reimagined.sqlite"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_key(name: str) -> str:
    return "vocation:" + "_".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in name).split()
    )


def normalize_identifier(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().lower().split())


def detect_conflicts(
    connection: sqlite3.Connection,
    predicate_registry: dict | None = None,
) -> int:
    """Open stable conflicts for incompatible factual claims in identical scope."""
    if predicate_registry is None:
        predicate_registry = load_json(ROOT / "data" / "predicate_registry.json")
    rows = connection.execute(
        """SELECT claim_id, subject_key, predicate, scope_json, value_json
        FROM claims
        WHERE claim_kind = 'fact'
        ORDER BY subject_key, predicate, scope_json, claim_id"""
    ).fetchall()
    groups: dict[tuple[str, str, str], list[sqlite3.Row]] = {}
    for row in rows:
        predicate = normalize_identifier(row["predicate"]).replace("-", "_").replace(" ", "_")
        if predicate_registry.get(predicate, {}).get("comparison") != "single":
            continue
        normalized_scope = json.dumps(json.loads(row["scope_json"]), sort_keys=True)
        key = (normalize_identifier(row["subject_key"]), predicate, normalized_scope)
        groups.setdefault(key, []).append(row)

    inserted = 0
    for (subject, predicate, scope), claims in groups.items():
        conflict_key = f"{subject}|{predicate}|{scope}"
        for index, first in enumerate(claims):
            for second in claims[index + 1:]:
                if json.loads(first["value_json"]) == json.loads(second["value_json"]):
                    continue
                claim_a, claim_b = sorted((first["claim_id"], second["claim_id"]))
                digest = hashlib.sha256(
                    f"{conflict_key}|{claim_a}|{claim_b}".encode("utf-8")
                ).hexdigest()[:16]
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO conflicts(
                        conflict_id, conflict_key, claim_a_id, claim_b_id,
                        status, rationale, detection_method
                    ) VALUES (?, ?, ?, ?, 'unresolved', ?, 'automatic_exact_scope')""",
                    (
                        f"conflict_{digest}", conflict_key, claim_a, claim_b,
                        "Differing factual values share the same normalized subject, predicate, and scope.",
                    ),
                )
                inserted += cursor.rowcount
    return inserted


def _build_database(db_path: Path) -> dict[str, int]:
    db_path = db_path.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    schema = (ROOT / "data" / "schema.sql").read_text(encoding="utf-8")
    sources = load_json(ROOT / "data" / "seed" / "sources.json")
    seed = load_json(ROOT / "data" / "seed" / "seed_data.json")

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(schema)
        connection.executemany(
            """INSERT INTO sources(
                source_id, title, publisher, url, source_class, role,
                published_at, updated_at, retrieved_at, status, notes
            ) VALUES (
                :source_id, :title, :publisher, :url, :source_class, :role,
                :published_at, :updated_at, :retrieved_at,
                COALESCE(:status, 'active'), :notes
            )""",
            [
                {
                    **item,
                    "status": item.get("status"),
                    "notes": item.get("notes"),
                }
                for item in sources
            ],
        )

        connection.executemany(
            "INSERT INTO meta(key, value) VALUES (?, ?)",
            [
                ("schema_version", "2"),
                ("package_version", "0.3.0-phase1"),
                ("build_type", "reconstructed_seed"),
                ("game", "Dragon Quest VII Reimagined"),
            ],
        )

        for vocation in seed["vocations"]:
            connection.execute(
                """INSERT INTO entities(
                    entity_id, entity_type, name, canonical_key, description,
                    reconstruction_status
                ) VALUES (?, 'vocation', ?, ?, ?, 'reconstructed_seed')""",
                (
                    vocation["id"],
                    vocation["name"],
                    canonical_key(vocation["name"]),
                    f"{vocation['tier'].title()} vocation",
                ),
            )
            connection.execute(
                """INSERT INTO vocations(
                    vocation_id, tier, exclusive_character, let_loose, source_id
                ) VALUES (?, ?, ?, ?, ?)""",
                (
                    vocation["id"],
                    vocation["tier"],
                    vocation.get("exclusive_character"),
                    vocation.get("let_loose"),
                    vocation["source_id"],
                ),
            )

        for requirement in seed["vocation_requirements"]:
            group_id = requirement["id"]
            for item_number, prerequisite_id in enumerate(requirement["prerequisites"], 1):
                requirement_id = f"{group_id}_{item_number:02d}"
                connection.execute(
                    """INSERT INTO vocation_requirements(
                        requirement_id, vocation_id, group_id, rule,
                        required_count, prerequisite_vocation_id, source_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        requirement_id,
                        requirement["vocation_id"],
                        group_id,
                        requirement["rule"],
                        requirement["required_count"],
                        prerequisite_id,
                        requirement["source_id"],
                    ),
                )
                connection.execute(
                    """INSERT INTO relationships(
                        relationship_id, subject_id, predicate, object_id,
                        qualifier_json, source_id, confidence
                    ) VALUES (?, ?, 'requires_mastery_of', ?, ?, ?, 'high')""",
                    (
                        f"rel_{requirement_id}",
                        requirement["vocation_id"],
                        prerequisite_id,
                        json.dumps(
                            {
                                "group_id": group_id,
                                "rule": requirement["rule"],
                                "required_count": requirement["required_count"],
                            },
                            sort_keys=True,
                        ),
                        requirement["source_id"],
                    ),
                )

        connection.executemany(
            """INSERT INTO medal_rewards(threshold, reward, source_id, confidence)
            VALUES (:threshold, :reward, 'game8_medals', 'high')""",
            seed["medal_rewards"],
        )

        connection.executemany(
            """INSERT INTO missables(
                missable_id, name, available_from, unavailable_after,
                consequence, severity, source_id, confidence, verification_status
            ) VALUES (
                :id, :name, :available_from, :unavailable_after, :consequence,
                :severity, 'game8_missables', :confidence, :verification_status
            )""",
            seed["missables"],
        )

        for farm in seed["farming_spots"]:
            connection.execute(
                """INSERT INTO farming_spots(
                    farming_id, target, location, time_period, available_from,
                    strategy, source_id, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    farm["id"],
                    farm["target"],
                    farm["location"],
                    farm.get("time_period"),
                    farm.get("available_from"),
                    farm.get("strategy"),
                    farm.get("source_id", "game8_exp_farming"),
                    "high" if farm["id"] != "farm_super_seeds_almighty" else "medium",
                ),
            )

        connection.executemany(
            """INSERT INTO checkpoints(
                checkpoint_id, sequence_no, name, time_period, region,
                entry_condition, safe_exit_condition, source_id, confidence,
                coverage_status
            ) VALUES (
                :id, :sequence_no, :name, :time_period, :region,
                :entry_condition, :safe_exit_condition, 'rpgsite_walkthrough',
                'medium', :coverage_status
            )""",
            seed["checkpoints"],
        )

        connection.executemany(
            """INSERT INTO mini_medal_locations(
                medal_number, location, detail, time_period, checkpoint_id,
                available_checkpoint_id,
                available_from, unavailable_after, source_id, locator,
                confidence, verification_status
            ) VALUES (
                :medal_number, :location, :detail, :time_period, :checkpoint_id,
                :available_checkpoint_id,
                :available_from, :unavailable_after, :source_id, :locator,
                :confidence, :verification_status
            )""",
            [
                {
                    **item,
                    "available_checkpoint_id": item.get(
                        "available_checkpoint_id", item["checkpoint_id"]
                    ),
                }
                for item in seed.get("mini_medal_locations", [])
            ],
        )

        connection.executemany(
            """INSERT INTO checkpoint_obligations(
                obligation_id, checkpoint_id, obligation_type, subject, action,
                required_for_100_percent, stop_before_advancing, available_from,
                unavailable_after, source_id, locator, confidence,
                verification_status
            ) VALUES (
                :obligation_id, :checkpoint_id, :obligation_type, :subject,
                :action, :required_for_100_percent, :stop_before_advancing,
                :available_from, :unavailable_after, :source_id, :locator,
                :confidence, :verification_status
            )""",
            seed.get("checkpoint_obligations", []),
        )

        connection.executemany(
            """INSERT INTO mini_medal_evidence(
                evidence_id, medal_number, source_id, locator, source_ordinal,
                ordinal_scheme, notes
            ) VALUES (
                :evidence_id, :medal_number, :source_id, :locator,
                :source_ordinal, :ordinal_scheme, :notes
            )""",
            seed.get("mini_medal_evidence", []),
        )

        connection.executemany(
            """INSERT INTO item_categories(category_id, name, heroic_hoarder_order)
            VALUES (:category_id, :name, :heroic_hoarder_order)""",
            seed.get("item_categories", []),
        )
        connection.executemany(
            """INSERT INTO items(
                item_id, category_id, name, canonical_key,
                heroic_hoarder_ordinal, heroic_hoarder_required, source_id,
                locator, confidence, verification_status
            ) VALUES (
                :item_id, :category_id, :name, :canonical_key,
                :heroic_hoarder_ordinal, :heroic_hoarder_required, :source_id,
                :locator, :confidence, :verification_status
            )""",
            seed.get("items", []),
        )
        connection.executemany(
            """INSERT INTO shops(
                shop_id, name, location, time_period,
                available_from_checkpoint_id, unavailable_after_checkpoint_id,
                source_id, locator, confidence, verification_status
            ) VALUES (
                :shop_id, :name, :location, :time_period,
                :available_from_checkpoint_id, :unavailable_after_checkpoint_id,
                :source_id, :locator, :confidence, :verification_status
            )""",
            seed.get("shops", []),
        )
        connection.executemany(
            """INSERT INTO lucky_panel_pools(
                pool_id, venue, game_version, panel_rank, chest_tier,
                time_period, available_from_checkpoint_id,
                unavailable_after_checkpoint_id, entry_cost, currency,
                source_id, locator, confidence, verification_status
            ) VALUES (
                :pool_id, :venue, :game_version, :panel_rank, :chest_tier,
                :time_period, :available_from_checkpoint_id,
                :unavailable_after_checkpoint_id, :entry_cost, :currency,
                :source_id, :locator, :confidence, :verification_status
            )""",
            seed.get("lucky_panel_pools", []),
        )
        connection.executemany(
            """INSERT INTO item_acquisition_paths(
                acquisition_id, item_id, method, route_label, location_text,
                time_period, available_from_checkpoint_id,
                unavailable_after_checkpoint_id, prerequisite_json, quantity,
                supply_type, finite_total, is_free, source_id, locator,
                confidence, verification_status
            ) VALUES (
                :acquisition_id, :item_id, :method, :route_label,
                :location_text, :time_period, :available_from_checkpoint_id,
                :unavailable_after_checkpoint_id, :prerequisite_json, :quantity,
                :supply_type, :finite_total, :is_free, :source_id, :locator,
                :confidence, :verification_status
            )""",
            [
                {
                    **item,
                    "prerequisite_json": json.dumps(
                        item.get("prerequisites", {}), sort_keys=True
                    ),
                }
                for item in seed.get("item_acquisition_paths", [])
            ],
        )
        connection.executemany(
            """INSERT INTO shop_inventory(
                acquisition_id, shop_id, price, currency, stock_limit
            ) VALUES (
                :acquisition_id, :shop_id, :price, :currency, :stock_limit
            )""",
            seed.get("shop_inventory", []),
        )
        connection.executemany(
            """INSERT INTO lucky_panel_rewards(
                acquisition_id, pool_id, reward_quantity, slot_count,
                probability_text
            ) VALUES (
                :acquisition_id, :pool_id, :reward_quantity, :slot_count,
                :probability_text
            )""",
            seed.get("lucky_panel_rewards", []),
        )

        invalid_shop_details = connection.execute(
            """SELECT si.acquisition_id FROM shop_inventory si
            JOIN item_acquisition_paths a USING(acquisition_id)
            WHERE a.method != 'shop'"""
        ).fetchall()
        invalid_panel_details = connection.execute(
            """SELECT lr.acquisition_id FROM lucky_panel_rewards lr
            JOIN item_acquisition_paths a USING(acquisition_id)
            WHERE a.method != 'lucky_panel'"""
        ).fetchall()
        if invalid_shop_details or invalid_panel_details:
            raise ValueError("Typed acquisition detail does not match its parent method")

        for claim in seed["claims"]:
            connection.execute(
                """INSERT INTO claims(
                    claim_id, subject_key, predicate, value_json, claim_kind,
                    scope_json, source_id, locator, confidence,
                    verification_status, reconstruction_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'reconstructed_seed', ?)""",
                (
                    claim["id"],
                    claim["subject_key"],
                    claim["predicate"],
                    json.dumps(claim["value"], ensure_ascii=False, sort_keys=True),
                    claim["claim_kind"],
                    json.dumps(claim.get("scope", {"game":"DQ7 Reimagined"}), sort_keys=True),
                    claim["source_id"],
                    claim.get("locator"),
                    claim["confidence"],
                    claim["verification_status"],
                    claim.get("notes"),
                ),
            )

        detect_conflicts(connection)

        for document in seed["documents"]:
            connection.execute(
                """INSERT INTO documents(
                    document_id, title, body, domain, checkpoint_key, source_id,
                    locator, confidence, reconstruction_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'reconstructed_seed')""",
                (
                    document["id"],
                    document["title"],
                    document["body"],
                    document["domain"],
                    document.get("checkpoint_key"),
                    document.get("source_id"),
                    document.get("locator"),
                    document["confidence"],
                ),
            )

        # Add searchable domain summaries generated from structured rows.
        for reward in seed["medal_rewards"]:
            connection.execute(
                """INSERT INTO documents(
                    document_id, title, body, domain, source_id, locator,
                    confidence, reconstruction_status
                ) VALUES (?, ?, ?, 'collectibles', 'game8_medals',
                    'Mini Medal Rewards table', 'high', 'reconstructed_seed')""",
                (
                    f"doc_medal_reward_{reward['threshold']:03d}",
                    f"Mini Medal reward at {reward['threshold']}",
                    f"Collecting {reward['threshold']} Mini Medals rewards {reward['reward']}.",
                ),
            )

        connection.commit()

        counts = {}
        for table in (
            "sources", "entities", "relationships", "claims", "documents",
            "vocations", "vocation_requirements", "medal_rewards", "missables",
            "farming_spots", "checkpoints", "conflicts"
            , "mini_medal_locations", "mini_medal_evidence", "checkpoint_obligations"
            , "item_categories", "items", "item_acquisition_paths", "shops"
            , "shop_inventory", "lucky_panel_pools", "lucky_panel_rewards"
        ):
            counts[table] = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

        fts_count = connection.execute(
            "SELECT COUNT(*) FROM document_fts"
        ).fetchone()[0]
        if fts_count != counts["documents"]:
            raise RuntimeError(
                f"FTS row count {fts_count} does not match documents {counts['documents']}"
            )
        return counts
    finally:
        connection.close()


def build_database(db_path: Path = DEFAULT_DB) -> dict[str, int]:
    """Build and validate a database, then atomically replace the target."""
    db_path = db_path.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{db_path.name}.", suffix=".tmp", dir=db_path.parent
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    temporary_path.unlink()
    try:
        counts = _build_database(temporary_path)
        with sqlite3.connect(temporary_path) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        if foreign_key_errors:
            raise RuntimeError(f"SQLite foreign-key check failed: {foreign_key_errors}")
        os.replace(temporary_path, db_path)
        return counts
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Output SQLite path")
    args = parser.parse_args()
    counts = build_database(args.db)
    print(f"Built {args.db.resolve()}")
    print(" ".join(f"{name}={count}" for name, count in counts.items()))


if __name__ == "__main__":
    main()
