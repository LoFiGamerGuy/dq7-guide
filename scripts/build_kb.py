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
WALKTHROUGH_ORDERED_THROUGH_SEQUENCE = 33


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_key(name: str) -> str:
    return "vocation:" + "_".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in name).split()
    )


def normalize_identifier(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().lower().split())


def normalize_checkpoint_advice(rows: list[dict]) -> list[dict]:
    """Serialize structured applicability without accepting opaque non-objects."""
    normalized = []
    for advice in rows:
        applicability = advice.get("applicability", {})
        if not isinstance(applicability, dict):
            raise ValueError(
                f"checkpoint advice applicability must be an object: {advice.get('advice_id')}"
            )
        normalized.append(
            {
                **advice,
                "applicability_json": json.dumps(applicability, sort_keys=True),
            }
        )
    return normalized


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
    vocation_numeric_audit = load_json(
        ROOT / "data" / "seed" / "vocation_numeric_audit.json"
    )
    equipment_matrix = load_json(
        ROOT / "data" / "seed" / "equipment_compatibility.json"
    )
    accessory_matrix = load_json(
        ROOT / "data" / "seed" / "accessory_compatibility.json"
    )

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(schema)
        vocation_rank_skills = list(seed.get("vocation_rank_skills", []))
        for table in seed.get("vocation_skill_tables", []):
            vocation_slug = table["vocation_id"].removeprefix("vocation_")
            for proficiency_rank, skill_names in table["ranks"]:
                for skill_name in skill_names:
                    skill_slug = canonical_key(skill_name).removeprefix("vocation:")
                    vocation_rank_skills.append({
                        "vocation_skill_id": f"vskill_{vocation_slug}_{proficiency_rank:02d}_{skill_slug}",
                        "vocation_id": table["vocation_id"],
                        "proficiency_rank": proficiency_rank,
                        "skill_name": skill_name,
                        "skill_description": "Learned at the sourced proficiency rank.",
                        "source_id": table["source_id"],
                        "locator": (
                            f"{table['name']} Skill List > All Skills and Required "
                            f"Proficiency > {proficiency_rank}★ {skill_name}"
                        ),
                        "confidence": "high",
                        "verification_status": "source_checked",
                    })

        normalized_panel_matrix_paths = []
        normalized_panel_matrix_rewards = []
        for row in seed.get("lucky_panel_standard_matrix_rows", []):
            game_version = str(row.get("game_version", "3"))
            panel_rank = str(row.get("panel_rank", "2"))
            pool_id = row.get("pool_id") or (
                f"lp_pilgrims_rest_v{game_version}_rank_{panel_rank}_standard"
            )
            pool = next(
                pool for pool in seed.get("lucky_panel_pools", [])
                if pool["pool_id"] == pool_id
            )
            acquisition_id = (
                f"acq_{row['item_id'].removeprefix('item_')}"
                f"_lucky_panel_v{game_version}_rank{panel_rank}"
            )
            normalized_panel_matrix_paths.append({
                "acquisition_id": acquisition_id,
                "item_id": row["item_id"],
                "method": "lucky_panel",
                "route_label": (
                    f"Lucky Panel Version {game_version} Rank {panel_rank}"
                ),
                "location_text": "Pilgrim's Rest well",
                "time_period": pool["time_period"],
                "available_from_checkpoint_id": pool["available_from_checkpoint_id"],
                "unavailable_after_checkpoint_id": pool.get(
                    "unavailable_after_checkpoint_id"
                ),
                "prerequisites": {
                    "panel_version": int(game_version),
                    "rank": int(panel_rank),
                    **(
                        {"source_qualifier": row["source_qualifier"]}
                        if row.get("source_qualifier")
                        else {}
                    ),
                },
                "quantity": 1,
                "supply_type": "renewable",
                "finite_total": None,
                "is_free": None,
                "source_id": row.get("source_id", "rpgsite_lucky_panel"),
                "locator": row.get("locator") or (
                    f"Lucky Panel (Version {game_version}) > Rank {panel_rank} > "
                    f"{row['source_name']}"
                    + (
                        f" [{row['source_qualifier']}]"
                        if row.get("source_qualifier")
                        else ""
                    )
                ),
                "confidence": row.get("confidence", "high"),
                "verification_status": row.get("verification_status") or (
                    "source_checked_typographic_name_resolution_"
                    "probability_and_cost_unknown"
                    if row.get("name_resolution")
                    else (
                        "source_checked_exclusivity_qualifier_"
                        "probability_and_cost_unknown"
                        if row.get("source_qualifier")
                        else "source_checked_probability_and_cost_unknown"
                    )
                ),
            })
            normalized_panel_matrix_rewards.append({
                "acquisition_id": acquisition_id,
                "pool_id": pool_id,
                "reward_quantity": 1,
                "slot_count": None,
                "probability_text": None,
            })

        vocation_rank_costs = list(seed.get("vocation_rank_costs", []))
        cost_vocations = {row["vocation_id"] for row in vocation_rank_costs}
        for vocation_id, page, costs, _dqst, _dqorg, _reported_total in vocation_numeric_audit["rows"]:
            if costs is None or vocation_id in cost_vocations:
                continue
            cumulative = 0
            slug = vocation_id.removeprefix("vocation_")
            for rank, points in enumerate(costs, start=2):
                cumulative += points
                vocation_rank_costs.append({
                    "vocation_rank_cost_id": f"vrank_{slug}_{rank:02d}",
                    "vocation_id": vocation_id,
                    "proficiency_rank": rank,
                    "proficiency_points": points,
                    "cumulative_points": cumulative,
                    "source_id": "dqst_vocation_tables",
                    "corroborating_source_id": "dragonquestorg_vocation_pages",
                    "locator": f"{page} > Proficiency > rank {rank}",
                    "corroborating_locator": (
                        f"{page} > Dragon Quest VII Reimagined > Abilities > rank {rank}"
                    ),
                    "confidence": "verified",
                    "verification_status": "two_independent_current_version_tables_match",
                })
        character_codes = dict(zip("HKMRAS", (
            "Hero", "Kiefer", "Maribel", "Ruff", "Aishe", "Sir Mervyn"
        )))
        mapping_sources = {
            "weapon": "game8_en_weapon_matrix", "shield": "game8_en_shield_matrix",
            "helm": "game8_en_helm_matrix", "armor": "game8_en_armour_matrix",
        }
        equipment_compatibility_audits = []
        equipment_compatibility_claims = []
        preserved_compatibility_claims = {
            "item_liquid_metal_sword": (
                "HKMRAS", "hyperwiki", "hyperwiki_equipment_sword",
                "Equipment list > はぐれメタルの剣 > equipment characters",
            ),
            "item_white_shield": (
                "HMAS", "hyperwiki", "hyperwiki_equipment_shield",
                "Equipment list > ホワイトシールド > equipment characters",
            ),
            "item_iron_lance": (
                "HKMAS", "gamershigh", "gamers_high_equipment_weapon",
                "Equipment list > てつのやり > compatible characters",
            ),
        }
        for (item_id, source_name, kind, hyper_page, game8_chars, hyper_chars,
             _prior_status, gamers_high_chars) in equipment_matrix:
            source_b_id = (
                f"gamewith_jp_equipment_{hyper_page.removeprefix('gamewith_')}"
                if hyper_page and hyper_page.startswith("gamewith_")
                else f"hyperwiki_equipment_{hyper_page}" if hyper_page else None
            )
            source_b_locator = (
                "Equipment list > " + {
                    "パーティドレス": "パーティードレス",
                    "メタルキングのよろい": "メタルキングよろい",
                }.get(source_name, source_name) + " > compatible-character icons"
                if hyper_page and hyper_page.startswith("gamewith_")
                else f"Equipment list > {source_name} > equipment characters"
                if hyper_page else None
            )
            source_a_characters = [character_codes[code] for code in game8_chars]
            source_b_characters = (
                [character_codes[code] for code in hyper_chars]
                if hyper_chars is not None else None
            )
            source_c_characters = (
                [character_codes[code] for code in gamers_high_chars]
                if gamers_high_chars is not None else None
            )
            source_c_id = (
                "appmedia_iron_lance"
                if item_id == "item_iron_lance"
                else f"gamers_high_equipment_{kind}" if source_c_characters is not None else None
            )
            source_c_locator = (
                "Iron Lance > compatible characters"
                if item_id == "item_iron_lance"
                else f"Equipment list > {source_name} > compatible characters"
                if source_c_characters is not None else None
            )
            character_lists = [row for row in (
                source_a_characters, source_b_characters, source_c_characters
            ) if row is not None]
            consensus = next((row for row in character_lists
                              if character_lists.count(row) >= 2), None)
            status = ("agree" if consensus is not None else
                      "conflict" if len(character_lists) >= 2 else "single")
            equipment_compatibility_audits.append({
                "audit_id": f"equipcompat_{item_id.removeprefix('item_')}",
                "item_id": item_id,
                "source_display_name": source_name,
                "mapping_status": "mapped",
                "agreement_status": {
                    "agree": "two_source_agreement",
                    "conflict": "source_disagreement",
                    "single": "single_source",
                }[status],
                "allowed_characters": consensus,
                "source_a_characters": source_a_characters,
                "source_b_characters": source_b_characters,
                "source_c_characters": source_c_characters,
                "source_a_id": "game8_jp_equipment_matrix",
                "source_b_id": source_b_id,
                "source_c_id": source_c_id,
                "mapping_source_id": mapping_sources[kind],
                "source_a_locator": f"Equipment list > {source_name} > compatible characters",
                "source_b_locator": source_b_locator,
                "source_c_locator": source_c_locator,
                "mapping_locator": f"All {kind} equipment > corresponding English row",
                "confidence": "verified" if status == "agree" else "high" if status == "conflict" else "medium",
                "verification_status": {
                    "agree": "two_independent_current_version_rows_match",
                    "conflict": "two_current_version_rows_disagree_not_normalized",
                    "single": "one_current_version_source_only_not_normalized",
                }[status],
                "notes": (
                    "Japanese-to-English identity is bridged by matching Game8 regional row order and stats; "
                    "compatibility is accepted only when at least two independent publishers match."
                ),
            })
            for suffix, characters, source_id, locator in (
                ("game8jp", source_a_characters, "game8_jp_equipment_matrix",
                 f"Equipment list > {source_name} > compatible characters"),
                ("gamewith" if hyper_page and hyper_page.startswith("gamewith_") else "hyperwiki",
                 source_b_characters,
                 source_b_id, source_b_locator),
                ("appmedia" if item_id == "item_iron_lance" else "gamershigh",
                 source_c_characters, source_c_id, source_c_locator),
            ):
                if characters is None or source_id is None:
                    continue
                equipment_compatibility_claims.append({
                    "id": f"claim_equipcompat_{item_id.removeprefix('item_')}_{suffix}",
                    "subject_key": f"item:{item_id.removeprefix('item_')}",
                    "predicate": "equipment_compatible_characters",
                    "value": {"characters": characters},
                    "claim_kind": "fact",
                    "scope": {"game": "DQ7 Reimagined", "platform": "unknown",
                              "patch": "patch_unknown"},
                    "source_id": source_id,
                    "locator": locator,
                    "confidence": "high",
                    "verification_status": "source_checked_row_level_compatibility",
                    "notes": "Source-specific character list retained for automatic conflict detection.",
                })
            if item_id in preserved_compatibility_claims:
                codes, suffix, source_id, locator = preserved_compatibility_claims[item_id]
                equipment_compatibility_claims.append({
                    "id": f"claim_equipcompat_{item_id.removeprefix('item_')}_{suffix}",
                    "subject_key": f"item:{item_id.removeprefix('item_')}",
                    "predicate": "equipment_compatible_characters",
                    "value": {"characters": [character_codes[code] for code in codes]},
                    "claim_kind": "fact",
                    "scope": {"game": "DQ7 Reimagined", "platform": "unknown",
                              "patch": "patch_unknown"},
                    "source_id": source_id,
                    "locator": locator,
                    "confidence": "high",
                    "verification_status": "source_checked_row_level_compatibility",
                    "notes": "Disagreeing source-specific list preserved after independent adjudication.",
                })
        accessory_sources = (
            ("game8jp", "game8_jp_equipment_matrix"),
            ("game8en", "game8_accessories"),
            ("gamershigh", "gamers_high_accessories"),
        )
        for item_id, source_name, game8_jp, game8_en, gamers_high in accessory_matrix["ordinary"]:
            lists = [[character_codes[code] for code in value]
                     for value in (game8_jp, game8_en, gamers_high)]
            consensus = next((row for row in lists if lists.count(row) >= 2), None)
            status = "two_source_agreement" if consensus is not None else "source_disagreement"
            audit_id = f"equipcompat_{item_id.removeprefix('item_')}"
            equipment_compatibility_audits.append({
                "audit_id": audit_id, "item_id": item_id,
                "source_display_name": source_name, "mapping_status": "mapped",
                "agreement_status": status, "allowed_characters": consensus,
                "source_a_characters": lists[0], "source_b_characters": lists[1],
                "source_c_characters": lists[2],
                "source_a_id": accessory_sources[0][1], "source_b_id": accessory_sources[1][1],
                "source_c_id": accessory_sources[2][1], "mapping_source_id": "game8_accessories",
                "source_a_locator": f"Equipment list > {source_name} > compatible characters",
                "source_b_locator": f"Accessories > {source_name} > Usable By",
                "source_c_locator": f"Accessories > {source_name} > compatible characters",
                "mapping_locator": f"List of All Accessories > corresponding English row for {source_name}",
                "confidence": "verified" if consensus else "high",
                "verification_status": ("two_independent_current_version_rows_match" if consensus else
                                        "three_current_version_rows_disagree_not_normalized"),
                "notes": "Game8's Japanese and English editions establish identity; compatibility requires agreement by two independent publishers.",
            })
            for (suffix, source_id), characters in zip(accessory_sources, lists):
                equipment_compatibility_claims.append({
                    "id": f"claim_equipcompat_{item_id.removeprefix('item_')}_{suffix}",
                    "subject_key": f"item:{item_id.removeprefix('item_')}",
                    "predicate": "equipment_compatible_characters",
                    "value": {"characters": characters}, "claim_kind": "fact",
                    "scope": {"game": "DQ7 Reimagined", "platform": "unknown", "patch": "patch_unknown"},
                    "source_id": source_id,
                    "locator": (f"Accessories > {source_name} > Usable By" if suffix == "game8en" else
                                f"Equipment list > {source_name} > compatible characters"),
                    "confidence": "high", "verification_status": "source_checked_row_level_compatibility",
                    "notes": "Source-specific character list retained for automatic conflict detection.",
                })
        all_characters = list(character_codes.values())
        for item_id, source_name in accessory_matrix["hearts"]:
            audit_id = f"equipcompat_{item_id.removeprefix('item_')}"
            equipment_compatibility_audits.append({
                "audit_id": audit_id, "item_id": item_id,
                "source_display_name": source_name, "mapping_status": "mapped",
                "agreement_status": "two_source_agreement", "allowed_characters": all_characters,
                "source_a_characters": all_characters, "source_b_characters": all_characters,
                "source_c_characters": None,
                "source_a_id": "game8_jp_equipment_matrix", "source_b_id": "gamedeep_monster_hearts",
                "source_c_id": None, "mapping_source_id": "game8_hearts_all",
                "source_a_locator": f"Equipment list > {source_name} > compatible characters",
                "source_b_locator": f"Monster Hearts table > {source_name} > compatible characters: all characters",
                "source_c_locator": None,
                "mapping_locator": f"List of All Monster Hearts > corresponding English heart row for {source_name}",
                "confidence": "verified", "verification_status": "two_independent_current_version_rows_match",
                "notes": "The Japanese equipment matrix and GameDeep independently list every mapped Heart as usable by all characters.",
            })
            for suffix, source_id, locator in (
                ("game8jp", "game8_jp_equipment_matrix", f"Equipment list > {source_name} > compatible characters"),
                ("gamedeep", "gamedeep_monster_hearts", f"Monster Hearts table > {source_name} > compatible characters"),
            ):
                equipment_compatibility_claims.append({
                    "id": f"claim_equipcompat_{item_id.removeprefix('item_')}_{suffix}",
                    "subject_key": f"item:{item_id.removeprefix('item_')}",
                    "predicate": "equipment_compatible_characters", "value": {"characters": all_characters},
                    "claim_kind": "fact", "scope": {"game": "DQ7 Reimagined", "platform": "unknown", "patch": "patch_unknown"},
                    "source_id": source_id, "locator": locator, "confidence": "high",
                    "verification_status": "source_checked_row_level_compatibility",
                    "notes": "Source-specific character list retained for independent corroboration.",
                })
        audits_by_item = {row["item_id"]: row for row in equipment_compatibility_audits}
        for item_id, character_codes_value, source_id, locator in accessory_matrix["supplemental"]:
            characters = [character_codes[code] for code in character_codes_value]
            audit = audits_by_item[item_id]
            existing_lists = [row for row in (
                audit["source_a_characters"], audit["source_b_characters"],
                audit["source_c_characters"],
            ) if row is not None]
            independently_corroborated = characters in existing_lists
            if independently_corroborated:
                # Keep every original source claim below, but make the audit's third
                # visible column the adjudicating source so the promotion is inspectable.
                audit.update({
                    "agreement_status": "two_source_agreement",
                    "allowed_characters": characters,
                    "source_c_characters": characters,
                    "source_c_id": source_id,
                    "source_c_locator": locator,
                    "confidence": "verified",
                    "verification_status": "two_independent_current_version_rows_match_after_fourth_source",
                    "notes": (audit["notes"] + " A fourth current-version publisher matches one retained claim; "
                              "the other original claims remain visible in claims/conflicts."),
                })
            equipment_compatibility_claims.append({
                "id": f"claim_equipcompat_{item_id.removeprefix('item_')}_gamedeep",
                "subject_key": f"item:{item_id.removeprefix('item_')}",
                "predicate": "equipment_compatible_characters",
                "value": {"characters": characters}, "claim_kind": "fact",
                "scope": {"game": "DQ7 Reimagined", "platform": "unknown", "patch": "patch_unknown"},
                "source_id": source_id, "locator": locator, "confidence": "high",
                "verification_status": ("source_checked_row_level_compatibility_corroborates_existing_claim"
                                        if independently_corroborated else
                                        "source_checked_row_level_compatibility_disagrees_not_normalized"),
                "notes": "Fourth-source adjudication claim; original claims are retained.",
            })
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
                ("schema_version", "3"),
                ("package_version", "0.3.0-phase1"),
                ("build_type", "reconstructed_seed"),
                ("game", "Dragon Quest VII Reimagined"),
            ],
        )

        connection.executemany(
            """INSERT INTO equipment_rules(
                rule_id, rule_type, slot_name, numeric_value, applies_to,
                source_id, corroborating_source_id, locator,
                corroborating_locator, confidence, verification_status, notes
            ) VALUES (
                :rule_id, :rule_type, :slot_name, :numeric_value, :applies_to,
                :source_id, :corroborating_source_id, :locator,
                :corroborating_locator, :confidence, :verification_status, :notes
            )""",
            seed.get("equipment_rules", []),
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
                    vocation_id, tier, exclusive_character, let_loose, source_id,
                    locator, confidence, verification_status
                ) VALUES (?, ?, ?, ?, ?, ?, 'high', 'source_checked_registry_row')""",
                (
                    vocation["id"],
                    vocation["tier"],
                    vocation.get("exclusive_character"),
                    vocation.get("let_loose"),
                    vocation["source_id"],
                    vocation.get("locator") or (
                        "List of All Vocations > "
                        f"{'Character-Exclusive' if vocation['tier'] == 'default' else vocation['tier'].title()} "
                        f"Vocations > {vocation['name']}"
                    ),
                ),
            )

        for requirement in seed["vocation_requirements"]:
            group_id = requirement["id"]
            for item_number, prerequisite_id in enumerate(requirement["prerequisites"], 1):
                requirement_id = f"{group_id}_{item_number:02d}"
                connection.execute(
                    """INSERT INTO vocation_requirements(
                        requirement_id, vocation_id, group_id, rule,
                        required_count, prerequisite_vocation_id, source_id,
                        locator, confidence, verification_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'high',
                        'source_checked_requirement_row')""",
                    (
                        requirement_id,
                        requirement["vocation_id"],
                        group_id,
                        requirement["rule"],
                        requirement["required_count"],
                        prerequisite_id,
                        requirement["source_id"],
                        requirement.get("locator") or (
                            "Vocation Unlock Requirements > "
                            f"{next(v['name'] for v in seed['vocations'] if v['id'] == requirement['vocation_id'])} "
                            f"> {next(v['name'] for v in seed['vocations'] if v['id'] == prerequisite_id)} prerequisite"
                        ),
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
            """INSERT INTO vocation_rank_skills(
                vocation_skill_id,vocation_id,proficiency_rank,skill_name,
                skill_description,source_id,locator,confidence,verification_status
            ) VALUES (:vocation_skill_id,:vocation_id,:proficiency_rank,:skill_name,
                :skill_description,:source_id,:locator,:confidence,:verification_status)""",
            vocation_rank_skills,
        )
        connection.executemany(
            """INSERT INTO vocation_perks(
                vocation_perk_id,vocation_id,perk_type,perk_name,perk_description,
                source_id,locator,confidence,verification_status
            ) VALUES (:vocation_perk_id,:vocation_id,:perk_type,:perk_name,:perk_description,
                :source_id,:locator,:confidence,:verification_status)""",
            seed.get("vocation_perks", []),
        )
        connection.executemany(
            """INSERT INTO vocation_progression_rules(
                progression_rule_id,vocation_id,event_type,proficiency_setting,
                proficiency_points,rank_delta,affects_both_moonlight_vocations,
                rule_description,source_id,locator,confidence,verification_status
            ) VALUES (
                :progression_rule_id,:vocation_id,:event_type,:proficiency_setting,
                :proficiency_points,:rank_delta,:affects_both_moonlight_vocations,
                :rule_description,:source_id,:locator,:confidence,:verification_status
            )""",
            seed.get("vocation_progression_rules", []),
        )
        connection.executemany(
            """INSERT INTO vocation_rank_costs(
                vocation_rank_cost_id,vocation_id,proficiency_rank,
                proficiency_points,cumulative_points,source_id,
                corroborating_source_id,locator,corroborating_locator,
                confidence,verification_status
            ) VALUES (
                :vocation_rank_cost_id,:vocation_id,:proficiency_rank,
                :proficiency_points,:cumulative_points,:source_id,
                :corroborating_source_id,:locator,:corroborating_locator,
                :confidence,:verification_status
            )""",
            vocation_rank_costs,
        )
        vocation_progression_profiles = []
        vocation_progression_claims = []
        vocation_progression_resolutions = []
        personal_exceptions = {
            "vocation_wolf_boy": {
                "mode": "story_then_points", "total": 150, "first": 7, "last": 8,
                "accepted": {"ranks_2_to_6": "story_granted_no_positive_cost",
                             "rank_costs_7_to_8": [70, 80], "total_points": 150},
                "hyper": {"rank_costs_2_to_8": [25, 35, 40, 45, 65, 70, 80],
                          "total_points": 360},
                "hyper_source": "hyperwiki_vocation_wolf_boy",
            },
            "vocation_destinys_dancer": {
                "mode": "story_granted", "total": 0, "first": None, "last": None,
                "accepted": {"ranks_2_to_8": "story_granted_no_positive_cost",
                             "total_points": 0},
                "hyper": {"rank_costs_2_to_8": [25, 35, 40, 50, 65, 75, 95],
                          "total_points": 385},
                "hyper_source": "hyperwiki_vocation_destinys_dancer",
            },
            "vocation_chevalier": {
                "mode": "story_granted", "total": 0, "first": None, "last": None,
                "accepted": {"ranks_2_to_8": "story_granted_no_positive_cost",
                             "total_points": 0},
                "hyper": {"rank_costs_2_to_8": [25, 35, 40, 50, 50, 55, 95],
                          "total_points": 350},
                "hyper_source": "hyperwiki_vocation_chevalier",
            },
        }
        for vocation_id, page, costs, _dqst, _dqorg, _reported_total in vocation_numeric_audit["rows"]:
            exception = personal_exceptions.get(vocation_id)
            if exception:
                mode, total = exception["mode"], exception["total"]
                first, last = exception["first"], exception["last"]
                notes = "Two matching tables treat early personal-vocation ranks as story-granted; hyperWiki's differing positive costs remain retained."
                slug = vocation_id.removeprefix("vocation_")
                for suffix, value, source_id, locator in (
                    ("dqst", exception["accepted"], "dqst_vocation_tables", f"{page} > Proficiency"),
                    ("dqorg", exception["accepted"], "dragonquestorg_vocation_pages", f"{page} > Dragon Quest VII Reimagined > Abilities"),
                    ("hyperwiki", exception["hyper"], exception["hyper_source"], "Level-up proficiency requirements table"),
                ):
                    vocation_progression_claims.append({
                        "id": f"claim_{slug}_rank_progression_{suffix}",
                        "subject_key": f"vocation:{slug}", "predicate": "vocation_rank_progression",
                        "value": value, "claim_kind": "fact",
                        "scope": {"game": "DQ7 Reimagined", "platform": "unknown", "patch": "patch_unknown"},
                        "source_id": source_id, "locator": locator, "confidence": "high",
                        "verification_status": "source_checked_personal_vocation_progression",
                    })
                for accepted_suffix in ("dqst", "dqorg"):
                    accepted_claim = f"claim_{slug}_rank_progression_{accepted_suffix}"
                    vocation_progression_resolutions.append({
                        "claim_a_id": accepted_claim,
                        "claim_b_id": f"claim_{slug}_rank_progression_hyperwiki",
                        "resolution_claim_id": accepted_claim,
                        "rationale": "dq_st and Dragon Quest Wiki independently agree on story-granted/no-positive-cost progression; hyperWiki's numeric thresholds are retained as the dissenting claim.",
                        "detection_method": "two_source_personal_vocation_adjudication",
                    })
            else:
                mode, total, first, last = "full_points", sum(costs), 2, 8
                notes = "All seven rank increments match independently; total is their arithmetic sum."
            vocation_progression_profiles.append({
                "vocation_id": vocation_id, "progression_mode": mode,
                "normalized_total_points": total, "first_numeric_rank": first,
                "last_numeric_rank": last, "source_id": "dqst_vocation_tables",
                "corroborating_source_id": "dragonquestorg_vocation_pages",
                "locator": f"{page} > Proficiency",
                "corroborating_locator": f"{page} > Dragon Quest VII Reimagined > Abilities",
                "confidence": "verified",
                "verification_status": "two_independent_current_version_progression_tables",
                "notes": notes,
            })
        connection.executemany(
            """INSERT INTO vocation_progression_profiles(
                vocation_id,progression_mode,normalized_total_points,
                first_numeric_rank,last_numeric_rank,source_id,
                corroborating_source_id,locator,corroborating_locator,
                confidence,verification_status,notes
            ) VALUES (
                :vocation_id,:progression_mode,:normalized_total_points,
                :first_numeric_rank,:last_numeric_rank,:source_id,
                :corroborating_source_id,:locator,:corroborating_locator,
                :confidence,:verification_status,:notes
            )""", vocation_progression_profiles)
        vocation_stat_modifiers = list(seed.get("vocation_stat_modifiers", []))
        stat_labels = {
            "max_hp": "Max HP", "max_mp": "Max MP", "attack": "Atk",
            "defence": "Def", "magical_might": "Mag Mt", "charm": "Charm",
            "magical_mending": "Mag Mend", "strength": "Str",
            "deftness": "Deft", "resilience": "Res", "agility": "Agi",
        }
        for table in seed.get("vocation_stat_tables", []):
            vocation_slug = table["vocation_id"].removeprefix("vocation_")
            for stat_key, direction in table["modifiers"].items():
                vocation_stat_modifiers.append({
                    "vocation_stat_modifier_id": f"vstat_{vocation_slug}_{stat_key}",
                    "vocation_id": table["vocation_id"],
                    "proficiency_rank": table.get("proficiency_rank"),
                    "stat_key": stat_key,
                    "modifier_direction": direction,
                    "modifier_value": None,
                    "modifier_unit": None,
                    "source_id": table["source_id"],
                    "corroborating_source_id": None,
                    "locator": f"{table['name']} Overview > Stat Bonuses > {stat_labels[stat_key]}",
                    "corroborating_locator": None,
                    "confidence": "high",
                    "verification_status": "source_checked",
                })

        numeric_stat_claims = []
        numeric_conflict_resolutions = []
        stat_keys = vocation_numeric_audit["stat_keys"]
        for vocation_id, page, costs, dqst_values, dqorg_values, reported_total in vocation_numeric_audit["rows"]:
            slug = vocation_id.removeprefix("vocation_")
            for stat_key, dqst_value, dqorg_value in zip(stat_keys, dqst_values, dqorg_values):
                predicate = f"numeric_stat_modifier_{stat_key}"
                for publisher, value, source_id, locator in (
                    ("dqst", dqst_value, "dqst_vocation_tables", f"{page} > Stat modifiers > {stat_key}"),
                    ("dqorg", dqorg_value, "dragonquestorg_vocation_pages", f"{page} > Dragon Quest VII Reimagined > Stat Changes > {stat_key}"),
                ):
                    numeric_stat_claims.append({
                        "id": f"claim_{slug}_{predicate}_{publisher}",
                        "subject_key": f"vocation:{slug}",
                        "predicate": predicate,
                        "value": {"percent": value},
                        "claim_kind": "fact",
                        "scope": {"game": "DQ7 Reimagined", "platform": "unknown", "patch": "patch_unknown"},
                        "source_id": source_id,
                        "locator": locator,
                        "confidence": "high",
                        "verification_status": "source_checked_cell_level_numeric_audit",
                    })
                vocation_stat_modifiers.append({
                    "vocation_stat_modifier_id": f"vstatnum_{slug}_{stat_key}",
                    "vocation_id": vocation_id,
                    "proficiency_rank": None,
                    "stat_key": stat_key,
                    "modifier_direction": None,
                    "modifier_value": dqst_value,
                    "modifier_unit": "percent",
                    "source_id": "dqst_vocation_tables",
                    "corroborating_source_id": "hyperwiki_vocation_stats",
                    "locator": f"{page} > Stat modifiers > {stat_key}",
                    "corroborating_locator": f"Stat modifiers table > {page} > {stat_key}",
                    "confidence": "verified",
                    "verification_status": "two_independent_current_version_cells_match_dqst_hyperwiki",
                })
                if dqst_value != dqorg_value:
                    dqst_claim = f"claim_{slug}_{predicate}_dqst"
                    dqorg_claim = f"claim_{slug}_{predicate}_dqorg"
                    numeric_conflict_resolutions.append({
                        "claim_a_id": dqst_claim,
                        "claim_b_id": dqorg_claim,
                        "resolution_claim_id": dqst_claim,
                        "rationale": (
                            "hyperWiki's independent current-version stat table matches "
                            "the dq_st cell exactly; Dragon Quest Wiki's differing value is retained."
                        ),
                        "detection_method": "third_source_cell_level_adjudication",
                    })
            if costs is not None and sum(costs) != reported_total:
                for publisher, value, source_id, locator in (
                    ("dqst", sum(costs), "dqst_vocation_tables", f"{page} > Proficiency > rank 8 cumulative"),
                    ("dqorg", reported_total, "dragonquestorg_vocation_pages", f"{page} > Dragon Quest VII Reimagined > Stat Changes > Total proficiency points"),
                ):
                    numeric_stat_claims.append({
                        "id": f"claim_{slug}_numeric_mastery_total_{publisher}",
                        "subject_key": f"vocation:{slug}",
                        "predicate": "numeric_mastery_total",
                        "value": {"points": value},
                        "claim_kind": "fact",
                        "scope": {"game": "DQ7 Reimagined", "platform": "unknown", "patch": "patch_unknown"},
                        "source_id": source_id,
                        "locator": locator,
                        "confidence": "high",
                        "verification_status": "source_checked_conflicting_total",
                    })
                dqst_claim = f"claim_{slug}_numeric_mastery_total_dqst"
                numeric_conflict_resolutions.append({
                    "claim_a_id": dqst_claim,
                    "claim_b_id": f"claim_{slug}_numeric_mastery_total_dqorg",
                    "resolution_claim_id": dqst_claim,
                    "rationale": (
                        "hyperWiki independently publishes the same seven rank increments; "
                        "their arithmetic sum is 400, matching dq_st and contradicting the "
                        "Dragon Quest Wiki headline total of 405."
                    ),
                    "detection_method": "third_source_rank_cells_and_arithmetic",
                })

        numeric_conflict_resolutions.append({
            "claim_a_id": "claim_luminary_numeric_modifiers_dqst",
            "claim_b_id": "claim_luminary_numeric_modifiers_dqorg",
            "resolution_claim_id": "claim_luminary_numeric_modifiers_dqst",
            "rationale": (
                "hyperWiki's independent current-version Luminary row matches all nine "
                "dq_st values exactly; the Dragon Quest Wiki aggregate remains retained."
            ),
            "detection_method": "third_source_complete_row_adjudication",
        })


        connection.executemany(
            """INSERT INTO vocation_stat_modifiers(
                vocation_stat_modifier_id,vocation_id,proficiency_rank,stat_key,
                modifier_direction,modifier_value,modifier_unit,source_id,
                corroborating_source_id,locator,corroborating_locator,
                confidence,verification_status
            ) VALUES (
                :vocation_stat_modifier_id,:vocation_id,:proficiency_rank,:stat_key,
                :modifier_direction,:modifier_value,:modifier_unit,:source_id,
                :corroborating_source_id,:locator,:corroborating_locator,
                :confidence,:verification_status
            )""",
            vocation_stat_modifiers,
        )

        connection.executemany(
            """INSERT INTO medal_rewards(
                threshold, reward, source_id, locator, confidence,
                verification_status
            ) VALUES (
                :threshold, :reward, 'game8_medals', :locator, 'high',
                'source_checked_reward_row'
            )""",
            [
                {
                    **reward,
                    "locator": reward.get("locator") or (
                        "Mini Medal Rewards > All Mini Medal Rewards > "
                        f"{reward['threshold']} Medals — {reward['reward']}"
                    ),
                }
                for reward in seed["medal_rewards"]
            ],
        )

        connection.executemany(
            """INSERT INTO checkpoints(
                checkpoint_id, sequence_no, name, time_period, region,
                entry_condition, safe_exit_condition, source_id, locator, confidence,
                coverage_status
            ) VALUES (
                :id, :sequence_no, :name, :time_period, :region,
                :entry_condition, :safe_exit_condition, 'rpgsite_walkthrough', :locator,
                'medium', :coverage_status
            )""",
            [{**checkpoint, "locator": checkpoint.get("locator")}
             for checkpoint in seed["checkpoints"]],
        )

        connection.executemany(
            """INSERT INTO farming_spots(
                farming_id, target, location, time_period, available_from,
                available_from_checkpoint_id, encounter_rate_text, strategy,
                source_id, locator, strategy_source_id, strategy_locator,
                confidence, verification_status
            ) VALUES (
                :id, :target, :location, :time_period, :available_from,
                :available_from_checkpoint_id, :encounter_rate_text, :strategy,
                :source_id, :locator, :strategy_source_id, :strategy_locator,
                :confidence, :verification_status
            )""",
            seed["farming_spots"],
        )

        connection.executemany(
            """INSERT INTO monster_hearts(
                heart_id, name, effect_text, available_from_checkpoint_id,
                availability_notes, availability_source_id,
                availability_locator, source_id, locator, confidence,
                verification_status
            ) VALUES (
                :heart_id, :name, :effect_text, :available_from_checkpoint_id,
                :availability_notes, :availability_source_id,
                :availability_locator, :source_id, :locator, :confidence,
                :verification_status
            )""",
            [
                {
                    **heart,
                    "available_from_checkpoint_id": heart.get(
                        "available_from_checkpoint_id"
                    ),
                    "availability_notes": heart.get("availability_notes"),
                    "availability_source_id": heart.get("availability_source_id"),
                    "availability_locator": heart.get("availability_locator"),
                }
                for heart in seed.get("monster_hearts", [])
            ],
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
                display_order, required_for_100_percent, stop_before_advancing, available_from,
                unavailable_after, source_id, locator, confidence,
                verification_status
            ) VALUES (
                :obligation_id, :checkpoint_id, :obligation_type, :subject,
                :action, :display_order, :required_for_100_percent, :stop_before_advancing,
                :available_from, :unavailable_after, :source_id, :locator,
                :confidence, :verification_status
            )""",
            [
                {**row, "display_order": row.get("display_order")}
                for row in seed.get("checkpoint_obligations", [])
            ],
        )

        connection.executemany(
            """INSERT INTO missables(
                missable_id, name, available_from_checkpoint_id, obligation_id,
                available_from, unavailable_after,
                consequence, severity, source_id, locator, confidence, verification_status
            ) VALUES (
                :id, :name, :available_from_checkpoint_id, :obligation_id,
                :available_from, :unavailable_after, :consequence,
                :severity, 'game8_missables', :locator, :confidence, :verification_status
            )""",
            [
                {**row, **next(link for link in seed["missable_checkpoint_links"]
                               if link["missable_id"] == row["id"])}
                for row in seed["missables"]
            ],
        )

        invalid_early_obligation_order = connection.execute(
            """SELECT o.obligation_id
            FROM checkpoint_obligations o JOIN checkpoints c USING(checkpoint_id)
            WHERE c.sequence_no BETWEEN 1 AND ?
              AND (o.display_order IS NULL OR o.display_order <= 0)
            UNION ALL
            SELECT min(o.obligation_id)
            FROM checkpoint_obligations o JOIN checkpoints c USING(checkpoint_id)
            WHERE c.sequence_no BETWEEN 1 AND ?
            GROUP BY o.checkpoint_id, o.display_order
            HAVING count(*) > 1""",
            (
                WALKTHROUGH_ORDERED_THROUGH_SEQUENCE,
                WALKTHROUGH_ORDERED_THROUGH_SEQUENCE,
            ),
        ).fetchall()
        if invalid_early_obligation_order:
            raise ValueError(
                "Every obligation through checkpoint sequence "
                f"{WALKTHROUGH_ORDERED_THROUGH_SEQUENCE} requires a unique positive "
                "display_order"
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

        advice_rows = normalize_checkpoint_advice(seed.get("checkpoint_advice", []))
        connection.executemany(
            """INSERT INTO checkpoint_advice(
                advice_id, checkpoint_id, advice_type, subject, advice_text,
                recommendation_goal, display_order, applicability_json,
                ready_for_play, source_id, locator, confidence,
                verification_status
            ) VALUES (
                :advice_id, :checkpoint_id, :advice_type, :subject,
                :advice_text, :recommendation_goal, :display_order,
                :applicability_json, :ready_for_play, :source_id, :locator,
                :confidence, :verification_status
            )""",
            advice_rows,
        )

        connection.executemany(
            """INSERT INTO boss_skill_recommendations(
                boss_skill_recommendation_id, checkpoint_id, advice_id,
                boss_name, character_name, vocation_skill_id,
                recommendation_strength, recommendation_verification_status,
                corroborating_source_id, corroborating_locator, notes
            ) VALUES (
                :boss_skill_recommendation_id, :checkpoint_id, :advice_id,
                :boss_name, :character_name, :vocation_skill_id,
                :recommendation_strength, :recommendation_verification_status,
                :corroborating_source_id, :corroborating_locator, :notes
            )""",
            seed.get("boss_skill_recommendations", []),
        )

        connection.executemany(
            """INSERT INTO achievements(
                achievement_id, name, description, category, hidden, grade,
                platform_scope, earliest_checkpoint_id,
                completion_checkpoint_id, missable, source_id, locator,
                confidence, verification_status
            ) VALUES (
                :achievement_id, :name, :description, :category, :hidden,
                :grade, :platform_scope, :earliest_checkpoint_id,
                :completion_checkpoint_id, :missable, :source_id, :locator,
                :confidence, :verification_status
            )""",
            seed.get("achievements", []),
        )
        connection.executemany(
            """INSERT INTO achievement_aliases(
                alias_id, achievement_id, alias, platform_scope, source_id,
                locator, confidence, verification_status
            ) VALUES (
                :alias_id, :achievement_id, :alias, :platform_scope,
                :source_id, :locator, :confidence, :verification_status
            )""",
            seed.get("achievement_aliases", []),
        )

        invalid_achievement_windows = connection.execute(
            """SELECT a.achievement_id FROM achievements a
            JOIN checkpoints first ON first.checkpoint_id = a.earliest_checkpoint_id
            JOIN checkpoints done ON done.checkpoint_id = a.completion_checkpoint_id
            WHERE done.sequence_no < first.sequence_no"""
        ).fetchall()
        if invalid_achievement_windows:
            raise ValueError("Achievement completion checkpoint precedes availability")

        connection.executemany(
            """INSERT INTO item_categories(category_id, name, heroic_hoarder_order)
            VALUES (:category_id, :name, :heroic_hoarder_order)""",
            seed.get("item_categories", []),
        )
        connection.executemany(
            """INSERT INTO stone_tablets(tablet_id,color,destination_name,required_fragment_count,
            available_from_checkpoint_id,completion_checkpoint_id,source_id,locator,confidence,verification_status)
            VALUES (:tablet_id,:color,:destination_name,:required_fragment_count,:available_from_checkpoint_id,
            :completion_checkpoint_id,:source_id,:locator,:confidence,:verification_status)""",
            seed.get("stone_tablets", []),
        )
        connection.executemany(
            """INSERT INTO tablet_fragments(fragment_id,source_ordinal,color,tablet_id,location,time_period,detail,
            available_from_checkpoint_id,unavailable_after_checkpoint_id,source_id,locator,confidence,verification_status)
            VALUES (:fragment_id,:source_ordinal,:color,:tablet_id,:location,:time_period,:detail,
            :available_from_checkpoint_id,:unavailable_after_checkpoint_id,:source_id,:locator,:confidence,:verification_status)""",
            seed.get("tablet_fragments", []),
        )
        mismatched_tablets = connection.execute(
            """SELECT t.tablet_id FROM stone_tablets t LEFT JOIN tablet_fragments f ON f.tablet_id=t.tablet_id
            GROUP BY t.tablet_id HAVING COUNT(f.fragment_id)<>t.required_fragment_count"""
        ).fetchall()
        if mismatched_tablets:
            raise ValueError("Tablet fragment counts do not match: " + ", ".join(r[0] for r in mismatched_tablets))
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
            """INSERT INTO item_aliases(
                alias_id, item_id, alias, scope, source_id, locator,
                confidence, verification_status
            ) VALUES (
                :alias_id, :item_id, :alias, :scope, :source_id, :locator,
                :confidence, :verification_status
            )""",
            seed.get("item_aliases", []),
        )
        connection.executemany(
            """INSERT INTO equipment_compatibility_audits(
                audit_id, item_id, source_display_name, mapping_status,
                agreement_status, allowed_characters_json,
                source_a_characters_json, source_b_characters_json,
                source_c_characters_json, source_a_id, source_b_id, source_c_id,
                mapping_source_id, source_a_locator, source_b_locator,
                source_c_locator, mapping_locator,
                confidence, verification_status, notes
            ) VALUES (
                :audit_id, :item_id, :source_display_name, :mapping_status,
                :agreement_status, :allowed_characters_json,
                :source_a_characters_json, :source_b_characters_json,
                :source_c_characters_json, :source_a_id, :source_b_id, :source_c_id,
                :mapping_source_id, :source_a_locator, :source_b_locator,
                :source_c_locator, :mapping_locator,
                :confidence, :verification_status, :notes
            )""",
            [
                {
                    **row,
                    "allowed_characters_json": (
                        json.dumps(row["allowed_characters"], ensure_ascii=False, sort_keys=True)
                        if row.get("allowed_characters") is not None else None
                    ),
                    "source_a_characters_json": json.dumps(
                        row.get("source_a_characters", []), ensure_ascii=False, sort_keys=True
                    ),
                    "source_b_characters_json": (
                        json.dumps(row["source_b_characters"], ensure_ascii=False, sort_keys=True)
                        if row.get("source_b_characters") is not None else None
                    ),
                    "source_c_characters_json": (
                        json.dumps(row["source_c_characters"], ensure_ascii=False, sort_keys=True)
                        if row.get("source_c_characters") is not None else None
                    ),
                }
                for row in equipment_compatibility_audits
            ],
        )
        compatibility_rows = []
        for row in equipment_compatibility_audits:
            if row["agreement_status"] != "two_source_agreement":
                continue
            allowed = set(row["allowed_characters"])
            compatibility_rows.extend(
                (row["item_id"], character, int(character in allowed), row["audit_id"])
                for character in ("Hero", "Kiefer", "Maribel", "Ruff", "Aishe", "Sir Mervyn")
            )
        connection.executemany(
            """INSERT INTO equipment_compatibility(
                item_id, character_name, can_equip, audit_id
            ) VALUES (?, ?, ?, ?)""",
            compatibility_rows,
        )
        connection.executemany(
            """INSERT INTO item_identity_redirects(
                legacy_item_id, canonical_item_id, source_id,
                corroborating_source_id, locator, corroborating_locator,
                confidence, verification_status, notes
            ) VALUES (
                :legacy_item_id, :canonical_item_id, :source_id,
                :corroborating_source_id, :locator, :corroborating_locator,
                :confidence, :verification_status, :notes
            )""",
            accessory_matrix["identity_redirects"],
        )

        connection.executemany(
            """INSERT INTO achievement_requirements(
                requirement_id, achievement_id, target_type, target_key,
                required_count, source_id, locator, confidence,
                verification_status
            ) VALUES (
                :requirement_id, :achievement_id, :target_type, :target_key,
                :required_count, :source_id, :locator, :confidence,
                :verification_status
            )""",
            seed.get("achievement_requirements", []),
        )

        connection.executemany(
            """INSERT INTO monsters(
                monster_id, source_ordinal, source_display_name, english_name,
                family, level, hp, strength, defence, experience,
                vocation_experience, gold, rampaging, source_id, locator,
                confidence, verification_status
            ) VALUES (
                :monster_id, :source_ordinal, :source_display_name, :english_name,
                :family, :level, :hp, :strength, :defence, :experience,
                :vocation_experience, :gold, :rampaging, :source_id, :locator,
                :confidence, :verification_status
            )""",
            seed.get("monsters", []),
        )

        connection.executemany(
            """INSERT INTO monster_encounters(
                encounter_id, monster_id, location_text, time_period,
                available_from_checkpoint_id, unavailable_after_checkpoint_id,
                source_id, locator, confidence, verification_status
            ) VALUES (
                :encounter_id, :monster_id, :location_text, :time_period,
                :available_from_checkpoint_id, :unavailable_after_checkpoint_id,
                :source_id, :locator, :confidence, :verification_status
            )""",
            seed.get("monster_encounters", []),
        )
        connection.executemany(
            """INSERT INTO monster_drops(
                drop_id, monster_id, item_name, drop_rate_text, source_id,
                locator, confidence, verification_status
            ) VALUES (
                :drop_id, :monster_id, :item_name, :drop_rate_text, :source_id,
                :locator, :confidence, :verification_status
            )""",
            seed.get("monster_drops", []),
        )

        connection.executemany(
            """INSERT INTO vicious_targets(
                vicious_target_id, name, source_id, locator, confidence,
                verification_status
            ) VALUES (
                :vicious_target_id, :name, :source_id, :locator, :confidence,
                :verification_status
            )""",
            seed.get("vicious_targets", []),
        )
        connection.executemany(
            """INSERT INTO vicious_encounters(
                vicious_encounter_id, vicious_target_id, obligation_id,
                checkpoint_id, encounter_size, source_id, locator, confidence,
                verification_status
            ) VALUES (
                :vicious_encounter_id, :vicious_target_id, :obligation_id,
                :checkpoint_id, :encounter_size, :source_id, :locator,
                :confidence, :verification_status
            )""",
            seed.get("vicious_encounters", []),
        )

        unresolved_typed_requirements = connection.execute(
            """SELECT requirement_id FROM achievement_requirements
            WHERE target_type = 'checkpoint_obligation'
              AND target_key NOT IN (SELECT obligation_id FROM checkpoint_obligations)
            UNION ALL
            SELECT requirement_id FROM achievement_requirements
            WHERE target_type = 'item_registry'
              AND target_key NOT IN ('heroic_hoarder_required')
              AND target_key NOT IN (SELECT item_id FROM items)
            UNION ALL
            SELECT requirement_id FROM achievement_requirements
            WHERE target_type='stone_tablet_registry'
              AND (target_key<>'all' OR required_count<>(SELECT COUNT(*) FROM stone_tablets))
            UNION ALL
            SELECT requirement_id FROM achievement_requirements
            WHERE target_type='vocation_registry'
              AND (target_key<>'all' OR required_count<>(SELECT COUNT(*) FROM vocations))
            UNION ALL
            SELECT requirement_id FROM achievement_requirements
            WHERE target_type='vicious_registry'
              AND (target_key<>'defeat_count'
                   OR required_count > (SELECT COALESCE(SUM(encounter_size), 0) FROM vicious_encounters))
            UNION ALL
            SELECT requirement_id FROM achievement_requirements
            WHERE target_type='monster_registry'
              AND (target_key<>'all' OR required_count<>(SELECT COUNT(*) FROM monsters))"""
        ).fetchall()
        if unresolved_typed_requirements:
            raise ValueError(
                "Typed achievement requirement targets must resolve: "
                + ", ".join(row[0] for row in unresolved_typed_requirements)
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
            """INSERT INTO lucky_panel_rules(
                rule_id,max_attempts_per_day,reset_action,entry_cost,currency,
                source_id,corroborating_source_id,locator,
                corroborating_locator,confidence,verification_status
            ) VALUES (
                :rule_id,:max_attempts_per_day,:reset_action,:entry_cost,:currency,
                :source_id,:corroborating_source_id,:locator,
                :corroborating_locator,:confidence,:verification_status
            )""",
            seed.get("lucky_panel_rules", []),
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
                for item in (
                    seed.get("item_acquisition_paths", [])
                    + normalized_panel_matrix_paths
                )
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
            seed.get("lucky_panel_rewards", []) + normalized_panel_matrix_rewards,
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
        missing_shop_details = connection.execute(
            """SELECT a.acquisition_id FROM item_acquisition_paths a
            LEFT JOIN shop_inventory si USING(acquisition_id)
            WHERE a.method = 'shop' AND si.acquisition_id IS NULL"""
        ).fetchall()
        missing_panel_details = connection.execute(
            """SELECT a.acquisition_id FROM item_acquisition_paths a
            LEFT JOIN lucky_panel_rewards lr USING(acquisition_id)
            WHERE a.method = 'lucky_panel' AND lr.acquisition_id IS NULL"""
        ).fetchall()
        inconsistent_shop_routes = connection.execute(
            """SELECT a.acquisition_id FROM item_acquisition_paths a
            JOIN shop_inventory si USING(acquisition_id)
            JOIN shops sh USING(shop_id)
            WHERE a.time_period != sh.time_period
               OR a.available_from_checkpoint_id IS NOT sh.available_from_checkpoint_id
               OR a.unavailable_after_checkpoint_id IS NOT sh.unavailable_after_checkpoint_id"""
        ).fetchall()
        inconsistent_panel_routes = connection.execute(
            """SELECT a.acquisition_id FROM item_acquisition_paths a
            JOIN lucky_panel_rewards lr USING(acquisition_id)
            JOIN lucky_panel_pools lp USING(pool_id)
            WHERE a.time_period != lp.time_period
               OR a.available_from_checkpoint_id IS NOT lp.available_from_checkpoint_id
               OR a.unavailable_after_checkpoint_id IS NOT lp.unavailable_after_checkpoint_id"""
        ).fetchall()
        contradictory_costs = connection.execute(
            """SELECT a.acquisition_id FROM item_acquisition_paths a
            LEFT JOIN shop_inventory si USING(acquisition_id)
            LEFT JOIN lucky_panel_rewards lr USING(acquisition_id)
            LEFT JOIN lucky_panel_pools lp USING(pool_id)
            WHERE (a.is_free = 1 AND (si.price > 0 OR lp.entry_cost > 0))
               OR (a.is_free = 0 AND (si.price = 0 OR lp.entry_cost = 0))
               OR (lp.entry_cost > 0 AND lp.currency IS NULL)"""
        ).fetchall()
        reversed_windows = connection.execute(
            """SELECT a.acquisition_id FROM item_acquisition_paths a
            JOIN checkpoints available
              ON available.checkpoint_id = a.available_from_checkpoint_id
            JOIN checkpoints unavailable
              ON unavailable.checkpoint_id = a.unavailable_after_checkpoint_id
            WHERE available.sequence_no > unavailable.sequence_no"""
        ).fetchall()
        if any((
            invalid_shop_details, invalid_panel_details, missing_shop_details,
            missing_panel_details, inconsistent_shop_routes,
            inconsistent_panel_routes, contradictory_costs, reversed_windows,
        )):
            raise ValueError("Typed acquisition detail does not match its parent method")

        for claim in [*seed["claims"], *numeric_stat_claims,
                      *vocation_progression_claims,
                      *equipment_compatibility_claims]:
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
        for audit in equipment_compatibility_audits:
            if audit["agreement_status"] != "two_source_agreement":
                continue
            subject_key = f"item:{audit['item_id'].removeprefix('item_')}"
            consensus_value = json.dumps(
                {"characters": audit["allowed_characters"]},
                ensure_ascii=False, sort_keys=True,
            )
            conflict_rows = connection.execute(
                """SELECT f.conflict_id, f.claim_a_id, f.claim_b_id,
                    a.value_json AS value_a, b.value_json AS value_b
                FROM conflicts f
                JOIN claims a ON a.claim_id=f.claim_a_id
                JOIN claims b ON b.claim_id=f.claim_b_id
                WHERE a.subject_key=? AND a.predicate='equipment_compatible_characters'""",
                (subject_key,),
            ).fetchall()
            consensus_claims = connection.execute(
                """SELECT claim_id FROM claims
                WHERE subject_key=? AND predicate='equipment_compatible_characters'
                  AND value_json=? ORDER BY claim_id""",
                (subject_key, consensus_value),
            ).fetchall()
            consensus_claim_id = (consensus_claims[0]["claim_id"]
                                  if consensus_claims else None)
            for conflict in conflict_rows:
                winner = (conflict["claim_a_id"] if conflict["value_a"] == consensus_value
                          else conflict["claim_b_id"] if conflict["value_b"] == consensus_value
                          else consensus_claim_id)
                if winner:
                    external = winner not in (conflict["claim_a_id"],
                                              conflict["claim_b_id"])
                    connection.execute(
                        """UPDATE conflicts SET status='resolved', resolution_claim_id=?,
                            rationale=?, detection_method=?
                        WHERE conflict_id=?""",
                        (winner,
                         ("Two independent current-version publishers agree on a third complete character list; both conflicting claims remain visible and the matching consensus claim is linked separately."
                          if external else
                          "Two independent current-version publishers agree on the complete character list; the outlying claim is retained."),
                         ("two_independent_source_consensus_external_claim"
                          if external else "two_independent_source_consensus"),
                         conflict["conflict_id"]),
                    )
        for resolution in [*seed.get("conflict_resolutions", []),
                           *numeric_conflict_resolutions,
                           *vocation_progression_resolutions]:
            claim_a, claim_b = sorted((resolution["claim_a_id"], resolution["claim_b_id"]))
            if resolution["resolution_claim_id"] not in (claim_a, claim_b):
                raise ValueError(
                    "Conflict resolution claim must be one of the conflicting claims: "
                    f"{claim_a}, {claim_b}"
                )
            cursor = connection.execute(
                """UPDATE conflicts
                SET status='resolved', resolution_claim_id=?, rationale=?, detection_method=?
                WHERE claim_a_id=? AND claim_b_id=?""",
                (resolution["resolution_claim_id"], resolution["rationale"],
                 resolution["detection_method"], claim_a, claim_b),
            )
            if cursor.rowcount != 1:
                raise ValueError(
                    f"Conflict resolution did not match exactly one conflict: {claim_a}, {claim_b}"
                )

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

        connection.executemany(
            """INSERT INTO seed_effects(
                seed_effect_id, item_id, stat_key, increase_amount,
                game_version, dlc_scope, source_id, locator, confidence,
                verification_status
            ) VALUES (
                :seed_effect_id, :item_id, :stat_key, :increase_amount,
                :game_version, :dlc_scope, :source_id, :locator, :confidence,
                :verification_status
            )""",
            seed.get("seed_effects", []),
        )
        connection.executemany(
            """INSERT INTO seed_reward_rules(
                seed_reward_rule_id, reward_family_text,
                available_from_checkpoint_id, location_text, trigger_text,
                reward_quantity, selection_method, eligible_items_json,
                repeatable, game_version, dlc_scope, source_id, locator,
                confidence, verification_status
            ) VALUES (
                :seed_reward_rule_id, :reward_family_text,
                :available_from_checkpoint_id, :location_text, :trigger_text,
                :reward_quantity, :selection_method, :eligible_items_json,
                :repeatable, :game_version, :dlc_scope, :source_id, :locator,
                :confidence, :verification_status
            )""",
            [
                {
                    **rule,
                    "eligible_items_json": (
                        json.dumps(rule["eligible_items"], sort_keys=True)
                        if rule.get("eligible_items") is not None else None
                    ),
                }
                for rule in seed.get("seed_reward_rules", [])
            ],
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
            "sources", "entities", "relationships", "claims", "documents", "equipment_rules",
            "equipment_compatibility_audits", "equipment_compatibility", "item_identity_redirects",
            "vocations", "vocation_requirements", "vocation_rank_skills", "vocation_perks",
            "vocation_progression_rules", "vocation_rank_costs",
            "vocation_progression_profiles", "vocation_stat_modifiers",
            "medal_rewards", "missables",
            "farming_spots", "seed_effects", "seed_reward_rules",
            "monster_hearts", "checkpoints", "conflicts"
            , "mini_medal_locations", "mini_medal_evidence", "checkpoint_obligations"
            , "checkpoint_advice", "boss_skill_recommendations", "achievements", "achievement_aliases"
            , "achievement_requirements"
            , "monsters", "monster_encounters", "monster_drops"
            , "vicious_targets", "vicious_encounters"
            , "stone_tablets", "tablet_fragments"
            , "item_categories", "items", "item_aliases", "item_acquisition_paths", "shops"
            , "shop_inventory", "lucky_panel_pools", "lucky_panel_rules", "lucky_panel_rewards"
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
