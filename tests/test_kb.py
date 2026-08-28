from __future__ import annotations

import json
import io
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_kb import (  # noqa: E402
    build_database,
    detect_conflicts,
    normalize_checkpoint_advice,
)
from achievement_report import load_achievement_report  # noqa: E402
from checkpoint_report import load_report  # noqa: E402
from conflict_report import load_conflicts  # noqa: E402
from early_walkthrough import (  # noqa: E402
    classify_medal_tracking,
    load_walkthrough,
    print_walkthrough,
    resolve_checkpoint_range,
    main as early_walkthrough_main,
)
from medal_report import medals_available_through  # noqa: E402
from item_report import load_item_routes, load_purchase_advice  # noqa: E402
from monster_report import (  # noqa: E402
    load_checkpoint_monsters,
    load_monster_coverage,
    load_monster_report,
    print_monster_report,
)
from hoarder_report import load_hoarder_report  # noqa: E402
from player_progress import update_progress  # noqa: E402
from query_kb import search  # noqa: E402
from vocation_report import load_vocation_details, print_vocation_details  # noqa: E402
from update_state import update_state  # noqa: E402
from walkthrough import main as walkthrough_main  # noqa: E402


class KnowledgeBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tempdir.name) / "test.sqlite"
        cls.counts = build_database(cls.db_path)
        cls.connection = sqlite3.connect(cls.db_path)
        cls.connection.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        cls.tempdir.cleanup()

    def test_expected_seed_counts(self):
        self.assertEqual(self.counts["sources"], 411)
        self.assertEqual(self.counts["vocations"], 26)
        self.assertEqual(self.counts["medal_rewards"], 19)
        self.assertEqual(self.counts["missables"], 7)
        self.assertEqual(self.counts["mini_medal_locations"], 100)
        self.assertEqual(self.counts["checkpoint_obligations"], 222)
        self.assertEqual(self.counts["checkpoint_advice"], 104)
        self.assertEqual(self.counts["mini_medal_evidence"], 86)
        self.assertEqual(self.counts["item_categories"], 6)
        self.assertEqual(self.counts["items"], 355)
        self.assertEqual(self.counts["item_aliases"], 4)
        self.assertEqual(self.counts["item_acquisition_paths"], 735)
        self.assertEqual(self.counts["monster_hearts"], 46)
        self.assertEqual(self.counts["seed_effects"], 18)
        self.assertEqual(self.counts["seed_reward_rules"], 1)
        self.assertEqual(self.counts["shops"], 47)
        self.assertEqual(self.counts["shop_inventory"], 115)
        self.assertEqual(self.counts["lucky_panel_pools"], 14)
        self.assertEqual(self.counts["lucky_panel_rewards"], 302)
        self.assertEqual(self.counts["stone_tablets"], 20)
        self.assertEqual(self.counts["tablet_fragments"], 71)
        self.assertEqual(self.counts["monsters"], 333)
        self.assertEqual(self.counts["vicious_targets"], 10)
        self.assertEqual(self.counts["vicious_encounters"], 11)
        self.assertEqual(self.counts["achievements"], 61)
        self.assertEqual(self.counts["achievement_aliases"], 1)
        self.assertEqual(self.counts["achievement_requirements"], 29)

    def test_achievement_registry_is_complete_and_checkpoint_scoped(self):
        counts = dict(
            self.connection.execute(
                "SELECT category, COUNT(*) FROM achievements GROUP BY category"
            ).fetchall()
        )
        self.assertEqual(counts, {"actionable": 28, "meta": 1, "story": 32})
        invalid = self.connection.execute(
            """SELECT achievement_id FROM achievements
            WHERE length(trim(locator)) = 0 OR source_id IS NULL"""
        ).fetchall()
        self.assertEqual(invalid, [])
        alias = self.connection.execute(
            """SELECT achievement_id, alias FROM achievement_aliases
            WHERE alias_id = 'ach_alias_field_day_a_questrian'"""
        ).fetchone()
        self.assertEqual(tuple(alias), ("ach_field_day", "A Questrian"))

    def test_achievement_requirements_cover_every_non_story_achievement(self):
        missing = self.connection.execute(
            """SELECT a.achievement_id FROM achievements a
            LEFT JOIN achievement_requirements r USING(achievement_id)
            WHERE a.category != 'story' AND r.requirement_id IS NULL"""
        ).fetchall()
        self.assertEqual(missing, [])
        unresolved = self.connection.execute(
            """SELECT COUNT(*) FROM achievement_requirements
            WHERE target_type = 'unresolved_registry'"""
        ).fetchone()[0]
        self.assertEqual(unresolved, 0)
        hoarder = self.connection.execute(
            """SELECT required_count FROM achievement_requirements
            WHERE achievement_id = 'ach_heroic_hoarder'"""
        ).fetchone()[0]
        self.assertEqual(hoarder, 353)

    def test_achievement_report_uses_only_explicit_player_progress(self):
        report = load_achievement_report(
            self.db_path, ROOT / "player" / "ryan-save-state.json"
        )
        self.assertEqual(report["total"], 61)
        self.assertEqual(report["unlocked_count"], 0)
        self.assertEqual(len(report["achievements"]), 61)

        state_path = Path(self.tempdir.name) / "achievement-state.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["achievements_unlocked"] = [
            "ach_into_the_unknown", "unknown_legacy_name"
        ]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_achievement_report(self.db_path, state_path)
        self.assertEqual(report["unlocked_count"], 1)
        self.assertEqual(report["unknown_state_ids"], ["unknown_legacy_name"])
        self.assertEqual(len(report["achievements"]), 60)

    def test_player_progress_records_and_reopens_achievements(self):
        state_path = Path(self.tempdir.name) / "achievement-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(
            state_path, self.db_path, "achievement-unlocked", ["ach_into_the_unknown"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            state["completion"]["achievements_unlocked"], ["ach_into_the_unknown"]
        )
        update_progress(
            state_path, self.db_path, "achievement-undo", ["ach_into_the_unknown"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["achievements_unlocked"], [])
        with self.assertRaisesRegex(ValueError, "Unknown achievement"):
            update_progress(
                state_path, self.db_path, "achievement-unlocked", ["ach_not_real"]
            )

    def test_every_claim_has_registered_source(self):
        orphans = self.connection.execute(
            """SELECT c.claim_id FROM claims c
            LEFT JOIN sources s ON s.source_id = c.source_id
            WHERE s.source_id IS NULL"""
        ).fetchall()
        self.assertEqual(orphans, [])

    def test_all_hoarder_category_identities_are_complete(self):
        counts = dict(
            self.connection.execute(
                """SELECT c.name, COUNT(*) FROM items i
                JOIN item_categories c USING(category_id)
                WHERE i.heroic_hoarder_required = 1
                GROUP BY c.name"""
            ).fetchall()
        )
        self.assertEqual(
            counts,
            {
                "Accessories": 74,
                "Armour": 69,
                "Head": 33,
                "Shields": 24,
                "Usable Items": 43,
                "Weapons": 110,
            },
        )
        gaps = self.connection.execute(
            """SELECT COUNT(*) FROM items i
            LEFT JOIN item_acquisition_paths a USING(item_id)
            WHERE a.item_id IS NULL"""
        ).fetchone()[0]
        unexplained_gaps = self.connection.execute(
            """SELECT item_id FROM items i
            LEFT JOIN item_acquisition_paths a USING(item_id)
            WHERE a.item_id IS NULL
              AND i.verification_status NOT LIKE 'source_checked_route_gap%'"""
        ).fetchall()
        self.assertEqual(gaps, 0)
        self.assertEqual(unexplained_gaps, [])

    def test_monster_heart_batch_preserves_known_and_unknown_availability(self):
        golem = self.connection.execute(
            """SELECT effect_text, available_from_checkpoint_id, locator
            FROM monster_hearts WHERE heart_id = 'heart_golem'"""
        ).fetchone()
        self.assertEqual(golem[1], "cp_003_ballymolloy")
        self.assertIn("survive a killing blow", golem[0])
        self.assertIn("Golem Heart for Survivability", golem[2])
        unknown = self.connection.execute(
            """SELECT COUNT(*) FROM monster_hearts
            WHERE available_from_checkpoint_id IS NULL"""
        ).fetchone()[0]
        self.assertEqual(unknown, 45)
        missing_provenance = self.connection.execute(
            """SELECT COUNT(*) FROM monster_hearts h
            LEFT JOIN sources s USING(source_id)
            WHERE s.source_id IS NULL OR trim(h.locator) = ''"""
        ).fetchone()[0]
        self.assertEqual(missing_provenance, 0)
        dlc_scoped = self.connection.execute(
            """SELECT name FROM monster_hearts
            WHERE verification_status = 'source_checked_effect_dlc_scope_not_fully_normalized'
            ORDER BY name"""
        ).fetchall()
        self.assertEqual(
            [row[0] for row in dlc_scoped],
            ["Gold Golem Heart", "Metal Slime Heart"],
        )
        availability_unknown = self.connection.execute(
            """SELECT name, availability_notes, verification_status
            FROM monster_hearts
            WHERE name IN ('Dragonlord Heart', 'Malroth Heart', 'Zoma Heart')
            ORDER BY name"""
        ).fetchall()
        self.assertEqual(
            [row[0] for row in availability_unknown],
            ["Dragonlord Heart", "Malroth Heart", "Zoma Heart"],
        )
        self.assertTrue(all(row[1] is None for row in availability_unknown))
        self.assertTrue(all(row[2].endswith("availability_unknown") for row in availability_unknown))

    def test_meowgician_heart_has_direct_finite_vicious_route(self):
        row = self.connection.execute(
            """SELECT i.heroic_hoarder_required, a.method, a.location_text,
                a.available_from_checkpoint_id, a.supply_type, a.finite_total,
                a.is_free, a.verification_status
            FROM items i JOIN item_acquisition_paths a USING(item_id)
            WHERE i.name = 'Meowgician Heart'"""
        ).fetchone()
        self.assertEqual(tuple(row[:7]), (0, "drop", "L'Arca", "cp_005_larca", "finite", 1, 1))
        self.assertIn("repeatability_unproven", row[7])

    def test_early_panel_items_have_direct_free_fixed_alternatives(self):
        rows = self.connection.execute(
            """SELECT item_id, available_from_checkpoint_id, supply_type,
                finite_total, is_free, prerequisite_json
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_pretty_betsy_larca_region_present',
                'acq_prayer_ring_tunnel_to_abbey_past'
            ) ORDER BY item_id"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        by_item = {row["item_id"]: row for row in rows}
        self.assertEqual(by_item["item_pretty_betsy"]["available_from_checkpoint_id"], "cp_005_larca")
        self.assertEqual(
            json.loads(by_item["item_pretty_betsy"]["prerequisite_json"])["access"],
            "land directly by boat",
        )
        self.assertEqual(by_item["item_prayer_ring"]["available_from_checkpoint_id"], "cp_009_alltrades")
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))

    def test_kamikazee_bracer_has_cp011_fixed_free_alternative(self):
        row = self.connection.execute(
            """SELECT method, location_text, time_period,
                available_from_checkpoint_id, supply_type, finite_total,
                is_free, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id = 'acq_kamikazee_bracer_likeness_great_evil_past'"""
        ).fetchone()
        self.assertEqual(tuple(row[:7]), (
            "chest", "Likeness of the Great Evil", "Past",
            "cp_011_la_bravoure", "finite", 1, 1,
        ))
        self.assertIn("container_unknown", row[7])

    def test_missables_have_precise_provenance_and_preserve_unknown_cutoffs(self):
        rows = self.connection.execute(
            """SELECT missable_id, unavailable_after, consequence, locator
            FROM missables ORDER BY missable_id"""
        ).fetchall()
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row[3] and ">" in row[3] for row in rows))
        unknown = {row[0] for row in rows if row[1] is None}
        self.assertEqual(
            unknown,
            {"missable_blue_button"},
        )
        wooden_doll = next(row for row in rows
                           if row[0] == "missable_wooden_doll")
        self.assertIn("Patrick choice", wooden_doll[1])
        vogograd = next(row for row in rows if row[0] == "missable_vogograd_tablet")
        self.assertIn("Pretty Betsy", vogograd[2])
        self.assertNotIn("Seed of Therapeusis", vogograd[2])

        blue_stop = self.connection.execute(
            """SELECT stop_before_advancing FROM checkpoint_obligations
            WHERE obligation_id='obl_emberdale_blue_button_deadline'"""
        ).fetchone()[0]
        self.assertEqual(blue_stop, 0)

    def test_farming_rows_are_checkpoint_gated_and_strategy_attributed(self):
        rows = self.connection.execute(
            """SELECT farming_id, available_from_checkpoint_id,
                encounter_rate_text, strategy, source_id, locator,
                strategy_source_id, strategy_locator
            FROM farming_spots ORDER BY farming_id"""
        ).fetchall()
        self.assertEqual(len(rows), 10)
        self.assertTrue(all(row[1] for row in rows))
        self.assertTrue(all(row[4] and row[5] for row in rows))
        self.assertTrue(all(not row[3] or (row[6] and row[7]) for row in rows))
        self.assertTrue(all(
            row[2] is None or "no numeric encounter rate published" in row[2]
            or "no proficiency-per-time rate is published" in row[2]
            or "no gold-per-time or prize-value rate is published" in row[2]
            for row in rows
        ))
        gold = next(row for row in rows
                    if row[0] == "farm_gold_lucky_panel_pilgrims_rest")
        self.assertEqual(gold[1], "cp_009_alltrades")
        self.assertEqual(gold[4], "rpgsite_lucky_panel")
        self.assertEqual(gold[6], "game8_gold_farming")
        proficiency = next(row for row in rows
                           if row[0] == "farm_vocation_proficiency_highendreigh")
        self.assertEqual(proficiency[1], "cp_013_flying_carpet")
        self.assertEqual(proficiency[4], "game8_proficiency_farming")
        self.assertEqual(proficiency[6], "game8_proficiency_farming")
        seed = next(row for row in rows if row[0] == "farm_super_seeds_almighty")
        self.assertEqual(seed[1], "cp_032_yet_another_world")
        self.assertEqual(seed[4], "game8_boss_almighty_spirits")
        self.assertEqual(seed[6], "game8_party_builds")

    def test_no_finite_monster_heart_reward_is_mislabeled_as_a_farm(self):
        heart_farms = self.connection.execute(
            "SELECT COUNT(*) FROM farming_spots WHERE lower(target) LIKE '%heart%'"
        ).fetchone()[0]
        self.assertEqual(heart_farms, 0)
        heart_drops = self.connection.execute(
            """SELECT DISTINCT a.supply_type
            FROM item_acquisition_paths a
            JOIN items i USING(item_id)
            WHERE i.name LIKE '% Heart' AND a.method='drop'"""
        ).fetchall()
        self.assertEqual({row[0] for row in heart_drops}, {"finite"})

    def test_seed_effects_are_fixed_and_reward_membership_stays_unknown(self):
        rows = self.connection.execute(
            """SELECT item_id, stat_key, increase_amount, locator
            FROM seed_effects ORDER BY item_id"""
        ).fetchall()
        self.assertEqual(len(rows), 18)
        self.assertTrue(all(row[2] > 0 and row[3] for row in rows))
        strength = next(row for row in rows if row[0] == "item_seed_of_strength")
        super_strength = next(
            row for row in rows if row[0] == "item_super_seed_of_strength"
        )
        self.assertEqual((strength[1], strength[2]), ("strength", 2))
        self.assertEqual((super_strength[1], super_strength[2]), ("strength", 20))
        reward = self.connection.execute(
            """SELECT available_from_checkpoint_id, reward_quantity,
                selection_method, eligible_items_json, repeatable
            FROM seed_reward_rules
            WHERE seed_reward_rule_id = 'seed_reward_almighty_spirits_rematch'"""
        ).fetchone()
        self.assertEqual(
            tuple(reward), ("cp_032_yet_another_world", 1, "random", None, 1)
        )

    def test_priority_source_tables_expose_locator_completeness(self):
        for table in ("medal_rewards", "vocations", "vocation_requirements"):
            missing = self.connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE locator IS NULL OR trim(locator) = ''"
            ).fetchone()[0]
            self.assertEqual(missing, 0, table)
        checkpoint_counts = self.connection.execute(
            """SELECT COUNT(*), SUM(locator IS NULL),
                SUM(coverage_status NOT LIKE '%partial%')
            FROM checkpoints"""
        ).fetchone()
        self.assertEqual(tuple(checkpoint_counts), (33, 0, 0))
        verified_checkpoint_locators = self.connection.execute(
            """SELECT sequence_no, locator FROM checkpoints
            ORDER BY sequence_no"""
        ).fetchall()
        self.assertEqual(len(verified_checkpoint_locators), 33)
        self.assertTrue(all(row["locator"] for row in verified_checkpoint_locators))
        self.assertIn(
            "Buccanham Arena",
            verified_checkpoint_locators[-1]["locator"],
        )
        requirement = self.connection.execute(
            """SELECT locator FROM vocation_requirements
            WHERE requirement_id = 'req_gladiator_01'"""
        ).fetchone()[0]
        self.assertIn("Gladiator", requirement)
        self.assertIn("Warrior prerequisite", requirement)

    def test_hoarder_report_preserves_unknown_progress_and_route_gaps(self):
        report = load_hoarder_report(
            self.db_path, ROOT / "player" / "ryan-save-state.json", gaps_only=True
        )
        self.assertEqual(report["total"], 353)
        self.assertEqual(report["obtained_count"], 0)
        self.assertEqual(report["routed_count"], 353)
        self.assertEqual(len(report["items"]), 0)

    def test_item_alias_resolves_without_discarding_name_conflict(self):
        item, routes = load_item_routes(self.db_path, "Stella Fan")
        self.assertEqual(item["name"], "Stellar Fan")
        self.assertTrue(any(route["method"] == "shop" for route in routes))
        conflict = self.connection.execute(
            """SELECT 1 FROM conflicts c
            JOIN claims a ON a.claim_id = c.claim_a_id
            WHERE c.status = 'unresolved'
              AND a.subject_key = 'item:stella_fan'
              AND a.predicate = 'item_display_name'"""
        ).fetchone()
        self.assertIsNotNone(conflict)

    def test_direct_item_pages_resolve_verified_panel_name_variants(self):
        aliases = dict(self.connection.execute(
            """SELECT alias, item_id FROM item_aliases
            WHERE alias IN ('Slime Earrings', 'Magic Vestment', 'Faerie Foil')"""
        ).fetchall())
        self.assertEqual(aliases, {
            "Slime Earrings": "item_slime_earring",
            "Magic Vestment": "item_magic_vetment",
            "Faerie Foil": "item_fairie_foil",
        })
        expected_routes = {
            "item_slime_earring": 2,
            "item_magic_vetment": 3,
            "item_fairie_foil": 2,
        }
        for item_id, expected in expected_routes.items():
            count = self.connection.execute(
                """SELECT COUNT(*) FROM item_acquisition_paths
                WHERE item_id = ? AND method = 'lucky_panel'
                  AND verification_status LIKE '%name_resolution%'""",
                (item_id,),
            ).fetchone()[0]
            self.assertEqual(count, expected)

    def test_direct_item_pages_add_finite_free_alternatives_to_panel_routes(self):
        rows = self.connection.execute(
            """SELECT item_id, time_period, available_from_checkpoint_id,
                supply_type, finite_total, is_free, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_hairband_treasure_larca_past',
                'acq_rabbit_ears_treasure_larca_present',
                'acq_coagulant_treasure_hubble_castle_past'
            ) ORDER BY item_id"""
        ).fetchall()
        self.assertEqual(len(rows), 3)
        by_item = {row["item_id"]: row for row in rows}
        self.assertEqual(by_item["item_hairband"]["available_from_checkpoint_id"], "cp_005_larca")
        self.assertEqual(by_item["item_rabbit_ears"]["time_period"], "Present")
        self.assertEqual(by_item["item_coagulant"]["available_from_checkpoint_id"], "cp_016_hubble")
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))
        self.assertTrue(all("container_unknown" in row["verification_status"] for row in rows))

    def test_late_panel_only_helmets_have_finite_free_alternatives(self):
        rows = self.connection.execute(
            """SELECT acquisition_id, item_id, location_text, time_period,
                available_from_checkpoint_id, supply_type, finite_total, is_free,
                source_id, locator, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_pirates_hat_buccanham_palace_closet',
                'acq_steel_helmet_rucker_castle_past'
            ) ORDER BY acquisition_id"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        by_item = {row["item_id"]: row for row in rows}
        pirate = by_item["item_pirates_hat"]
        self.assertEqual(
            (pirate["location_text"], pirate["time_period"],
             pirate["available_from_checkpoint_id"]),
            ("Buccanham Palace", "Present", "cp_020_buccanham"),
        )
        self.assertIn("closet", pirate["locator"].lower())
        steel = by_item["item_steel_helmet"]
        self.assertEqual(
            (steel["location_text"], steel["time_period"],
             steel["available_from_checkpoint_id"]),
            ("Rucker Castle", "Past", "cp_027_deja_vous_rucker"),
        )
        self.assertIn("container_unknown", steel["verification_status"])
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))
        self.assertTrue(all(row["source_id"] and row["locator"] for row in rows))

    def test_garter_and_slime_earring_have_non_panel_alternatives(self):
        garter = self.connection.execute(
            """SELECT method, location_text, time_period,
                available_from_checkpoint_id, supply_type, finite_total, is_free,
                verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id='acq_garter_greenthumb_region_present'"""
        ).fetchone()
        self.assertEqual(
            tuple(garter[:7]),
            ("other", "Greenthumb Gardens Region", "Present",
             "cp_015_greenthumb", "finite", 1, 1),
        )
        self.assertIn("container_unknown", garter[7])

        drops = self.connection.execute(
            """SELECT location_text, time_period, available_from_checkpoint_id,
                supply_type, finite_total, is_free, source_id, locator,
                verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN (
                'acq_slime_earring_seaslime_drop',
                'acq_slime_earring_slimecicle_drop'
            ) ORDER BY acquisition_id"""
        ).fetchall()
        self.assertEqual(len(drops), 2)
        self.assertEqual({row["location_text"] for row in drops}, {"Falls Hollow", "Coral Cave"})
        self.assertTrue(all(row["supply_type"] == "renewable" for row in drops))
        self.assertTrue(all(row["finite_total"] is None for row in drops))
        self.assertTrue(all(row["is_free"] == 1 for row in drops))
        self.assertTrue(all(row["source_id"] and row["locator"] for row in drops))
        self.assertTrue(all("rate_unknown" in row["verification_status"] for row in drops))

    def test_early_and_midgame_equipment_has_direct_finite_routes(self):
        acquisition_ids = (
            "acq_strength_ring_faraday_castle_past",
            "acq_strength_ring_mountain_path_wilted_present",
            "acq_divine_dagger_burnmont_past",
            "acq_scale_armour_burnmont_past",
            "acq_scale_armour_frobisher_past",
        )
        placeholders = ",".join("?" for _ in acquisition_ids)
        rows = self.connection.execute(
            f"""SELECT acquisition_id, item_id, location_text, time_period,
                available_from_checkpoint_id, supply_type, finite_total, is_free,
                source_id, locator, verification_status
            FROM item_acquisition_paths
            WHERE acquisition_id IN ({placeholders}) ORDER BY acquisition_id""",
            acquisition_ids,
        ).fetchall()
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 for row in rows))
        self.assertTrue(all(row["is_free"] == 1 for row in rows))
        self.assertTrue(all(row["source_id"] and row["locator"] for row in rows))
        gates = {row["acquisition_id"]: row["available_from_checkpoint_id"] for row in rows}
        self.assertEqual(gates["acq_divine_dagger_burnmont_past"], "cp_004_emberdale")
        self.assertEqual(gates["acq_scale_armour_frobisher_past"], "cp_007_frobisher")
        self.assertEqual(
            gates["acq_strength_ring_mountain_path_wilted_present"],
            "cp_015_greenthumb",
        )
        burnmont_scale = next(
            row for row in rows if row["acquisition_id"] == "acq_scale_armour_burnmont_past"
        )
        self.assertEqual(burnmont_scale["verification_status"], "source_checked_exact_chest")

    def test_knuckledusters_identity_and_first_half_fixed_routes_are_normalized(self):
        item = self.connection.execute(
            """SELECT heroic_hoarder_required, source_id, locator
            FROM items WHERE item_id='item_knuckledusters'"""
        ).fetchone()
        self.assertEqual(item[0], 0)
        self.assertEqual(item[1], "game8_knuckledusters")
        self.assertTrue(item[2])
        panel_rows = self.connection.execute(
            """SELECT p.game_version, p.panel_rank, a.source_id, a.locator
            FROM lucky_panel_rewards r
            JOIN lucky_panel_pools p USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            WHERE a.item_id='item_knuckledusters'
            ORDER BY CAST(p.game_version AS INTEGER)"""
        ).fetchall()
        self.assertEqual(
            [(row[0], row[1]) for row in panel_rows],
            [("1", "3"), ("2", "2"), ("3", "1")],
        )
        self.assertTrue(all(row[2] == "rpgsite_lucky_panel" and row[3] for row in panel_rows))

        fixed_ids = (
            "acq_knuckledusters_pilgrims_perdition_past",
            "acq_iron_lance_grotta_sigillo_past",
            "acq_iron_lance_allblades_arena_past",
            "acq_yggdrasil_leaf_burnmont_past",
        )
        placeholders = ",".join("?" for _ in fixed_ids)
        rows = self.connection.execute(
            f"""SELECT acquisition_id, available_from_checkpoint_id,
                supply_type, finite_total, is_free, locator, verification_status
            FROM item_acquisition_paths WHERE acquisition_id IN ({placeholders})""",
            fixed_ids,
        ).fetchall()
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["supply_type"] == "finite" for row in rows))
        self.assertTrue(all(row["finite_total"] == 1 and row["is_free"] == 1 for row in rows))
        self.assertTrue(all(row["locator"] for row in rows))
        self.assertTrue(all("container_unknown" in row["verification_status"] for row in rows))

    def test_tablet_registry_is_complete_and_resolves_achievement(self):
        totals = self.connection.execute(
            """SELECT COUNT(*), SUM(required_fragment_count) FROM stone_tablets"""
        ).fetchone()
        self.assertEqual(tuple(totals), (20, 71))
        ordinals = [
            row[0] for row in self.connection.execute(
                "SELECT source_ordinal FROM tablet_fragments ORDER BY source_ordinal"
            )
        ]
        self.assertEqual(ordinals, list(range(1, 72)))
        requirement = self.connection.execute(
            """SELECT target_type, target_key, required_count
            FROM achievement_requirements
            WHERE achievement_id = 'ach_no_stone_left_unturned'"""
        ).fetchone()
        self.assertEqual(
            tuple(requirement), ("stone_tablet_registry", "all", 20)
        )

    def test_monster_and_vicious_registries_resolve_achievement_targets(self):
        monster_stats = self.connection.execute(
            """SELECT COUNT(*), MIN(source_ordinal), MAX(source_ordinal),
                SUM(rampaging), SUM(english_name IS NOT NULL) FROM monsters"""
        ).fetchone()
        self.assertEqual(tuple(monster_stats), (333, 1, 333, 35, 333))
        take_no_prisoners = self.connection.execute(
            """SELECT target_type, target_key, required_count
            FROM achievement_requirements
            WHERE achievement_id = 'ach_take_no_prisoners'"""
        ).fetchone()
        self.assertEqual(
            tuple(take_no_prisoners), ("monster_registry", "all", 333)
        )
        vanquisher = self.connection.execute(
            """SELECT target_type, target_key, required_count
            FROM achievement_requirements
            WHERE achievement_id = 'ach_vanquisher_of_the_vicious'"""
        ).fetchone()
        self.assertEqual(
            tuple(vanquisher), ("vicious_registry", "defeat_count", 10)
        )

    def test_early_monster_encounters_and_drops_are_checkpoint_scoped(self):
        counts = self.connection.execute(
            "SELECT (SELECT COUNT(*) FROM monster_encounters), "
            "(SELECT COUNT(*) FROM monster_drops)"
        ).fetchone()
        self.assertEqual(tuple(counts), (383, 212))
        early = self.connection.execute(
            """SELECT COUNT(DISTINCT monster_id), MIN(available_from_checkpoint_id),
                SUM(source_id NOT LIKE 'game8_monster_%')
            FROM monster_encounters"""
        ).fetchone()
        self.assertEqual(tuple(early), (254, "cp_001_prologue", 57))
        cactiball_drops = {
            row[0] for row in self.connection.execute(
                "SELECT item_name FROM monster_drops WHERE monster_id='monster_009'"
            )
        }
        self.assertEqual(cactiball_drops, {"Medicinal Herb", "Thorn Whip"})
        late_cleanup = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE source_id IN ('game8_monster_blightcrawler',
                'game8_monster_mad_moai', 'game8_monster_terrorhawk')
              AND available_from_checkpoint_id='cp_026_elemental_cleanup_nottagen'"""
        ).fetchone()
        self.assertEqual(tuple(late_cleanup), (6, 3))
        late_hoarder_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE source_id IN ('game8_monster_delusionist',
                'game8_monster_infernal_serpent',
                'game8_monster_hyperpyrexion', 'game8_monster_alarmour')
              AND available_from_checkpoint_id='cp_026_elemental_cleanup_nottagen'"""
        ).fetchone()
        self.assertEqual(tuple(late_hoarder_routes), (8, 4))
        cleanup_equipment_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE source_id IN ('game8_monster_sculptrice',
                'game8_monster_fright_night', 'game8_monster_lethal_armour',
                'game8_monster_gigantes')
              AND available_from_checkpoint_id='cp_026_elemental_cleanup_nottagen'"""
        ).fetchone()
        self.assertEqual(tuple(cleanup_equipment_routes), (8, 4))
        late_area_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE source_id IN ('game8_monster_merderer', 'game8_monster_seasaur',
                'game8_monster_mermaniac', 'game8_monster_croaked_king',
                'game8_monster_charmour', 'game8_monster_boss_troll',
                'game8_monster_drakulard', 'game8_monster_orc_king')"""
        ).fetchone()
        self.assertEqual(tuple(late_area_routes), (14, 8))
        final_cleanup_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE source_id IN ('game8_monster_bone_baron',
                'game8_monster_manticore', 'game8_monster_juggular',
                'game8_monster_vis_mager', 'game8_monster_hyperanemon',
                'game8_monster_writhing_root', 'game8_monster_metal_heavy',
                'game8_monster_beastly_priest')"""
        ).fetchone()
        self.assertEqual(tuple(final_cleanup_routes), (13, 8))
        rampage_completion_routes = self.connection.execute(
            """SELECT COUNT(*), COUNT(DISTINCT monster_id)
            FROM monster_encounters
            WHERE location_text LIKE 'Rampage Roads (Buccanham Arena;%'
              AND available_from_checkpoint_id='cp_031_testy_road_gold_gate'"""
        ).fetchone()
        self.assertEqual(tuple(rampage_completion_routes), (8, 8))

    def test_cp011_through_cp014_monsters_use_explicit_area_gates(self):
        checkpoints = dict(
            self.connection.execute(
                """SELECT available_from_checkpoint_id, COUNT(*)
                FROM monster_encounters
                WHERE available_from_checkpoint_id IN (
                    'cp_011_la_bravoure', 'cp_013_flying_carpet',
                    'cp_014_sir_mervyn'
                ) GROUP BY available_from_checkpoint_id"""
            ).fetchall()
        )
        self.assertEqual(
            checkpoints,
            {
                "cp_011_la_bravoure": 14,
                "cp_013_flying_carpet": 19,
                "cp_014_sir_mervyn": 4,
            },
        )
        self.assertEqual(
            self.connection.execute(
                """SELECT COUNT(*) FROM monster_encounters
                WHERE source_id='game8_monster_drag_racer'
                  AND location_text='Aeolus Vale Region'"""
            ).fetchone()[0],
            1,
        )

    def test_cp015_through_cp019_monsters_keep_later_routes_later_gated(self):
        checkpoints = dict(
            self.connection.execute(
                """SELECT available_from_checkpoint_id, COUNT(*)
                FROM monster_encounters
                WHERE available_from_checkpoint_id IN (
                    'cp_015_greenthumb', 'cp_016_hubble', 'cp_019_aeolus'
                ) GROUP BY available_from_checkpoint_id"""
            ).fetchall()
        )
        self.assertEqual(
            checkpoints,
            {
                "cp_015_greenthumb": 5,
                "cp_016_hubble": 15,
                "cp_019_aeolus": 16,
            },
        )
        later_routes = dict(
            self.connection.execute(
                """SELECT location_text, available_from_checkpoint_id
                FROM monster_encounters
                WHERE location_text IN ('Buccanham Region', 'Coral Cave',
                    'Heavy Metal-Hole')
                GROUP BY location_text, available_from_checkpoint_id"""
            ).fetchall()
        )
        self.assertEqual(
            set(later_routes.values()),
            {"cp_020_buccanham", "cp_026_elemental_cleanup_nottagen"},
        )

    def test_cp020_through_cp025_monsters_use_explicit_area_gates(self):
        checkpoints = dict(
            self.connection.execute(
                """SELECT available_from_checkpoint_id, COUNT(*)
                FROM monster_encounters
                WHERE available_from_checkpoint_id IN (
                    'cp_020_buccanham', 'cp_021_malign_shrine',
                    'cp_023_fire_spirit', 'cp_025_wind_spirit'
                ) GROUP BY available_from_checkpoint_id"""
            ).fetchall()
        )
        self.assertEqual(
            checkpoints,
            {
                "cp_020_buccanham": 33,
                "cp_021_malign_shrine": 12,
                "cp_023_fire_spirit": 3,
                "cp_025_wind_spirit": 4,
            },
        )

    def test_monster_report_resolves_name_id_and_ordinal(self):
        by_name = load_monster_report(self.db_path, "Cactiball")
        by_id = load_monster_report(self.db_path, "monster_009")
        by_number = load_monster_report(self.db_path, "#9")
        self.assertEqual(by_name["monster"]["monster_id"], "monster_009")
        self.assertEqual(by_id["monster"], by_number["monster"])
        self.assertTrue(by_name["encounters"])
        self.assertEqual(len(by_name["drops"]), 2)
        output = io.StringIO()
        with redirect_stdout(output):
            print_monster_report(by_name)
        self.assertIn("#9 Cactiball", output.getvalue())
        self.assertIn("Find:", output.getvalue())
        self.assertIn("Drops:", output.getvalue())

    def test_checkpoint_monsters_hide_explicitly_completed_entries(self):
        state_path = Path(self.tempdir.name) / "monster-checkpoint.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["monster_entries"] = ["monster_009"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        remaining = load_checkpoint_monsters(
            self.db_path, state_path, "cp_003_ballymolloy"
        )
        self.assertNotIn("monster_009", [row["monster_id"] for row in remaining["monsters"]])
        complete = load_checkpoint_monsters(
            self.db_path, state_path, "cp_003_ballymolloy", include_completed=True
        )
        cactiball = next(row for row in complete["monsters"] if row["monster_id"] == "monster_009")
        self.assertTrue(cactiball["completed"])

    def test_monster_coverage_uses_only_explicit_player_state(self):
        state_path = Path(self.tempdir.name) / "monster-coverage.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["monster_entries"] = ["monster_009", "unknown_monster"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_monster_coverage(self.db_path, state_path)
        self.assertEqual(report["total"], 333)
        self.assertEqual(report["defeated"], 1)
        self.assertEqual(report["routed"], 254)
        self.assertEqual(report["drops"], 184)
        self.assertEqual(report["unknown_state_ids"], ["unknown_monster"])

    def test_player_progress_tracks_tablet_fragment_ids(self):
        state_path = Path(self.tempdir.name) / "tablet-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(
            state_path, self.db_path, "tablet-found", ["tablet_fragment_001"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            state["completion"]["tablet_fragments"], ["tablet_fragment_001"]
        )
        update_progress(
            state_path, self.db_path, "tablet-undo", ["tablet_fragment_001"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["tablet_fragments"], [])

    def test_player_progress_tracks_party_wide_vocation_mastery(self):
        state_path = Path(self.tempdir.name) / "vocation-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(
            state_path, self.db_path, "vocation-mastered", ["Hero", "vocation_warrior"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertIs(state["party"]["members"]["Hero"]["vocation_mastery"]["vocation_warrior"], True)
        update_progress(
            state_path, self.db_path, "vocation-undo", ["Hero", "vocation_warrior"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertNotIn(
            "vocation_warrior", state["party"]["members"]["Hero"]["vocation_mastery"]
        )

    def test_player_progress_tracks_explicit_level_and_current_vocations(self):
        state_path = Path(self.tempdir.name) / "party-details.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(state_path, self.db_path, "party-level", ["Hero", "17"])
        update_progress(state_path, self.db_path, "party-vocations",
                        ["Hero", "vocation_warrior", "vocation_priest"])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        hero = state["party"]["members"]["Hero"]
        self.assertEqual((hero["level"], hero["primary_vocation"], hero["secondary_vocation"]),
                         (17, "vocation_warrior", "vocation_priest"))
        update_progress(state_path, self.db_path, "party-level", ["Hero", "unknown"])
        update_progress(state_path, self.db_path, "party-vocations",
                        ["Hero", "unknown", "unknown"])
        hero = json.loads(state_path.read_text(encoding="utf-8"))["party"]["members"]["Hero"]
        self.assertEqual((hero["level"], hero["primary_vocation"], hero["secondary_vocation"]),
                         (None, None, None))
        with self.assertRaisesRegex(ValueError, "positive integer"):
            update_progress(state_path, self.db_path, "party-level", ["Hero", "0"])
        with self.assertRaisesRegex(ValueError, "unavailable"):
            update_progress(state_path, self.db_path, "party-vocations",
                            ["Ruff", "vocation_fledgling_fisherman", "unknown"])

    def test_player_progress_tracks_monster_ordinals(self):
        state_path = Path(self.tempdir.name) / "monster-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(state_path, self.db_path, "monster-defeated", ["1", "Cactiball"])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            state["completion"]["monster_entries"], ["monster_001", "monster_009"]
        )
        update_progress(state_path, self.db_path, "monster-undo", ["#1", "monster_009"])
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["monster_entries"], [])
        with self.assertRaisesRegex(ValueError, "Ambiguous monster name"):
            update_progress(state_path, self.db_path, "monster-defeated", ["Orgodemir"])

        state_path = Path(self.tempdir.name) / "hoarder-state.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["items_obtained"] = [
            "item_pilchard_crackers", "unknown_item"
        ]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_hoarder_report(self.db_path, state_path)
        self.assertEqual(report["obtained_count"], 1)
        self.assertEqual(report["unknown_state_ids"], ["unknown_item"])
        self.assertNotIn(
            "item_pilchard_crackers", {row["item_id"] for row in report["items"]}
        )

    def test_player_progress_records_and_reopens_hoarder_items(self):
        state_path = Path(self.tempdir.name) / "hoarder-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(
            state_path, self.db_path, "item-obtained", ["item_pilchard_crackers"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            state["completion"]["items_obtained"], ["item_pilchard_crackers"]
        )
        update_progress(
            state_path, self.db_path, "item-undo", ["item_pilchard_crackers"]
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["items_obtained"], [])

    def test_medal_078_conflict_resolves_to_screenshot_corroborated_route(self):
        row = self.connection.execute(
            """SELECT c.status, c.detection_method, c.resolution_claim_id,
                c.rationale
            FROM conflicts c
            WHERE c.claim_a_id = 'claim_medal_078_game8_floor'
              AND c.claim_b_id = 'claim_medal_078_rpgsite_floor'"""
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["status"], "resolved")
        self.assertEqual(row["detection_method"],
                         "manual_screenshot_route_adjudication")
        self.assertEqual(row["resolution_claim_id"],
                         "claim_medal_078_rpgsite_floor")
        self.assertIn("Level 3", row["rationale"])
        medal = self.connection.execute(
            """SELECT detail, source_id, verification_status
            FROM mini_medal_locations WHERE medal_number=78"""
        ).fetchone()
        self.assertEqual(medal["detail"],
                         "Exit south from 3F and open the chest on the outside balcony.")
        self.assertEqual(medal["source_id"], "rpgsite_walkthrough")
        self.assertIn("screenshot", medal["verification_status"])

    def test_phase_two_source_disagreements_are_visible(self):
        pairs = self.connection.execute(
            """SELECT claim_a_id, claim_b_id FROM conflicts
            WHERE claim_a_id LIKE 'claim_elevating_shoes_%'
               OR claim_a_id LIKE 'claim_cautery_sword_%'"""
        ).fetchall()
        self.assertEqual(len(pairs), 2)

        cautery = self.connection.execute(
            """SELECT status, resolution_claim_id, detection_method, rationale
            FROM conflicts WHERE claim_a_id LIKE 'claim_cautery_sword_%'
               OR claim_b_id LIKE 'claim_cautery_sword_%'"""
        ).fetchone()
        self.assertEqual(cautery["status"], "resolved")
        self.assertEqual(cautery["resolution_claim_id"],
                         "claim_cautery_sword_rpgsite_location")
        self.assertEqual(cautery["detection_method"],
                         "manual_direct_item_page_adjudication")
        self.assertIn("dedicated Cautery Sword acquisition page",
                      cautery["rationale"])

        elevating = self.connection.execute(
            """SELECT status, resolution_claim_id, detection_method, rationale
            FROM conflicts WHERE claim_a_id LIKE 'claim_elevating_shoes_%'
               OR claim_b_id LIKE 'claim_elevating_shoes_%'"""
        ).fetchone()
        self.assertEqual(elevating["status"], "resolved")
        self.assertEqual(elevating["resolution_claim_id"],
                         "claim_elevating_shoes_game8_routes")
        self.assertEqual(elevating["detection_method"],
                         "manual_direct_item_acquisition_adjudication")
        self.assertIn("Metal King Slime", elevating["rationale"])
        self.assertIn("rate", elevating["rationale"])

    def test_tempest_shield_locations_are_distinct_acquisition_routes(self):
        routes = self.connection.execute(
            """SELECT location_text, available_from_checkpoint_id, source_id
            FROM item_acquisition_paths
            WHERE item_id='item_tempest_shield' AND method='chest'
            ORDER BY available_from_checkpoint_id"""
        ).fetchall()
        self.assertEqual([tuple(row) for row in routes], [
            ("Sanctum of the Cirrus", "cp_019_aeolus", "game8_tempest_shield"),
            ("Ventus Tower 2F, by the north stairs", "cp_025_wind_spirit",
             "rpgsite_walkthrough"),
        ])
        conflict = self.connection.execute(
            """SELECT 1 FROM conflicts c JOIN claims a ON a.claim_id=c.claim_a_id
            WHERE a.subject_key='item:tempest_shield'"""
        ).fetchone()
        self.assertIsNone(conflict)
        predicates = self.connection.execute(
            """SELECT DISTINCT predicate FROM claims
            WHERE subject_key='item:tempest_shield'
              AND claim_id LIKE 'claim_tempest_shield_%location'"""
        ).fetchall()
        self.assertEqual([row[0] for row in predicates], ["acquisition_location"])

    def test_iron_shield_conflict_and_scale_shield_gap_are_visible(self):
        conflict = self.connection.execute(
            """SELECT status FROM conflicts
            WHERE claim_a_id LIKE 'claim_iron_shield_%'
               OR claim_b_id LIKE 'claim_iron_shield_%'"""
        ).fetchone()
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict["status"], "resolved")
        resolved = self.connection.execute(
            """SELECT resolution_claim_id, detection_method, rationale FROM conflicts
            WHERE claim_a_id LIKE 'claim_iron_shield_%'
               OR claim_b_id LIKE 'claim_iron_shield_%'"""
        ).fetchone()
        self.assertEqual(resolved["resolution_claim_id"],
                         "claim_iron_shield_game8_alltrades_price")
        self.assertEqual(resolved["detection_method"],
                         "manual_direct_location_shop_adjudication")
        self.assertIn("dedicated Alltrades Abbey map shop table", resolved["rationale"])
        scale_claim = self.connection.execute(
            """SELECT value_json FROM claims
            WHERE claim_id = 'claim_scale_shield_game8_lucky_panel_unspecified'"""
        ).fetchone()
        self.assertIsNotNone(scale_claim)
        self.assertEqual(json.loads(scale_claim["value_json"])["rank"], "unknown")
        typed_route = self.connection.execute(
            """SELECT 1 FROM item_acquisition_paths
            WHERE item_id = 'item_scale_shield' AND method = 'lucky_panel'"""
        ).fetchone()
        self.assertIsNone(typed_route)

    def test_ice_shield_treasure_conflict_is_visible(self):
        conflicts = self.connection.execute(
            """SELECT status, resolution_claim_id, detection_method FROM conflicts
            WHERE claim_a_id LIKE 'claim_ice_shield_%'
               OR claim_b_id LIKE 'claim_ice_shield_%'"""
        ).fetchall()
        self.assertEqual(len(conflicts), 2)
        self.assertTrue(all(row["status"] == "resolved" for row in conflicts))
        self.assertEqual(
            {row["resolution_claim_id"] for row in conflicts},
            {"claim_ice_shield_rpgsite_past_chest",
             "claim_ice_shield_game8_hardlypool_map_chest"},
        )
        self.assertTrue(all(row["detection_method"] ==
                            "manual_direct_location_map_adjudication"
                            for row in conflicts))
        _, _, verdict = load_purchase_advice(
            self.db_path, "Ice Shield", "cp_013_flying_carpet"
        )
        self.assertNotIn("acquisition evidence conflict", verdict)

    def test_tempest_shield_multiple_routes_do_not_block_purchase_advice(self):
        conflict = self.connection.execute(
            """SELECT status FROM conflicts
            WHERE claim_a_id LIKE 'claim_tempest_shield_%'
               OR claim_b_id LIKE 'claim_tempest_shield_%'"""
        ).fetchone()
        self.assertIsNone(conflict)
        _, _, verdict = load_purchase_advice(
            self.db_path, "Tempest Shield", "cp_025_wind_spirit"
        )
        self.assertNotIn("acquisition evidence conflict", verdict)

    def test_conflict_detector_opens_stable_fact_conflict(self):
        path = Path(self.tempdir.name) / "conflict.sqlite"
        build_database(path)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        try:
            values = (
                ("test_fact_a", '{"answer": 1}'),
                ("test_fact_b", '{"answer": 2}'),
            )
            for claim_id, value in values:
                connection.execute(
                    """INSERT INTO claims(
                        claim_id, subject_key, predicate, value_json, claim_kind,
                        scope_json, source_id, locator, confidence,
                        verification_status, reconstruction_status
                    ) VALUES (?, 'test:subject', 'version_count', ?, 'fact',
                        '{"game":"DQ7 Reimagined"}', 'game8_hub', 'test row',
                        'low', 'test_only', 'native')""",
                    (claim_id, value),
                )
            self.assertEqual(detect_conflicts(connection), 1)
            self.assertEqual(detect_conflicts(connection), 0)
            row = connection.execute(
                """SELECT claim_a_id, claim_b_id, status, detection_method
                FROM conflicts WHERE claim_a_id = 'test_fact_a'"""
            ).fetchone()
            self.assertEqual(tuple(row), (
                "test_fact_a", "test_fact_b", "unresolved", "automatic_exact_scope"
            ))
        finally:
            connection.close()

    def test_conflict_detector_ignores_recommendations(self):
        path = Path(self.tempdir.name) / "recommendations.sqlite"
        build_database(path)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        try:
            for claim_id, value in (("rec_a", '"A"'), ("rec_b", '"B"')):
                connection.execute(
                    """INSERT INTO claims(
                        claim_id, subject_key, predicate, value_json, claim_kind,
                        scope_json, source_id, locator, confidence,
                        verification_status, reconstruction_status
                    ) VALUES (?, 'test:build', 'best', ?, 'recommendation',
                        '{}', 'game8_hub', 'test row', 'low', 'test_only', 'native')""",
                    (claim_id, value),
                )
            self.assertEqual(detect_conflicts(connection), 0)
        finally:
            connection.close()

    def test_conflict_detector_ignores_unregistered_predicate(self):
        path = Path(self.tempdir.name) / "unregistered-conflict.sqlite"
        build_database(path)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        try:
            for claim_id, value in (("route_a", '"chest"'), ("route_b", '"drop"')):
                connection.execute(
                    """INSERT INTO claims(
                        claim_id, subject_key, predicate, value_json, claim_kind,
                        scope_json, source_id, locator, confidence,
                        verification_status, reconstruction_status
                    ) VALUES (?, 'item:test', 'obtained_from', ?, 'fact', '{}',
                        'game8_hub', 'test row', 'low', 'test_only', 'native')""",
                    (claim_id, value),
                )
            self.assertEqual(detect_conflicts(connection), 0)
        finally:
            connection.close()

    def test_conflict_report_returns_full_provenance(self):
        path = Path(self.tempdir.name) / "conflict-report.sqlite"
        build_database(path)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        try:
            for claim_id, value, source_id in (
                ("report_a", "1", "game8_hub"),
                ("report_b", "2", "rpgsite_walkthrough"),
            ):
                connection.execute(
                    """INSERT INTO claims(
                        claim_id, subject_key, predicate, value_json, claim_kind,
                        scope_json, source_id, locator, confidence,
                        verification_status, reconstruction_status
                    ) VALUES (?, 'test:report', 'total_count', ?, 'fact', '{}',
                        ?, 'test locator', 'low', 'test_only', 'native')""",
                    (claim_id, value, source_id),
                )
            detect_conflicts(connection)
            connection.commit()
        finally:
            connection.close()
        rows = load_conflicts(path)
        row = next(item for item in rows if item["claim_a_id"] == "report_a")
        self.assertEqual(row["source_title_a"], "Dragon Quest 7 Reimagined Walkthrough & Guides Wiki")
        self.assertIn("rpgsite.net", row["source_url_b"])

    def test_vocation_relationships_are_valid(self):
        invalid = self.connection.execute(
            """SELECT r.relationship_id FROM relationships r
            LEFT JOIN entities s ON s.entity_id = r.subject_id
            LEFT JOIN entities o ON o.entity_id = r.object_id
            WHERE s.entity_id IS NULL OR o.entity_id IS NULL"""
        ).fetchall()
        self.assertEqual(invalid, [])

    def test_advanced_requirement_rules(self):
        rows = self.connection.execute(
            """SELECT v.name, vr.rule, vr.required_count, COUNT(*) AS candidates
            FROM vocation_requirements vr
            JOIN vocations vo ON vo.vocation_id = vr.vocation_id
            JOIN entities v ON v.entity_id = vo.vocation_id
            WHERE vo.tier = 'advanced'
            GROUP BY v.name, vr.group_id, vr.rule, vr.required_count
            ORDER BY v.name"""
        ).fetchall()
        actual = {row["name"]: (row["rule"], row["required_count"], row["candidates"]) for row in rows}
        self.assertEqual(actual["Champion"], ("all_of", 2, 2))
        self.assertEqual(actual["Druid"], ("any_n_of", 2, 3))
        self.assertEqual(actual["Hero"], ("any_n_of", 3, 7))

    def test_fts_smoke_query(self):
        rows = search(self.db_path, "alltrades vocation", limit=8)
        titles = {row["title"] for row in rows}
        self.assertIn("Alltrades Abbey power spike", titles)
        self.assertIn("Vocation prerequisite graph", titles)

    def test_fts_query_handles_empty_and_punctuation(self):
        self.assertEqual(search(self.db_path, "\"'!?", limit=8), [])
        rows = search(self.db_path, 'alltrades foo"bar', limit=8)
        self.assertTrue(rows)

    def test_search_does_not_create_missing_database(self):
        missing = Path(self.tempdir.name) / "missing.sqlite"
        with self.assertRaises(FileNotFoundError):
            search(missing, "alltrades")
        self.assertFalse(missing.exists())

    def test_phase_one_rows_have_precise_provenance(self):
        for table in ("mini_medal_locations", "checkpoint_obligations"):
            rows = self.connection.execute(
                f"""SELECT source_id, locator FROM {table}
                WHERE source_id IS NULL OR trim(locator) = ''"""
            ).fetchall()
            self.assertEqual(rows, [], table)

    def test_phase_two_rows_have_precise_provenance(self):
        for table in ("items", "item_acquisition_paths", "shops", "lucky_panel_pools"):
            rows = self.connection.execute(
                f"SELECT rowid FROM {table} WHERE source_id IS NULL OR trim(locator) = ''"
            ).fetchall()
            self.assertEqual(rows, [], table)

    def test_typed_acquisition_details_match_parent_method(self):
        bad_shop = self.connection.execute(
            """SELECT si.acquisition_id FROM shop_inventory si
            JOIN item_acquisition_paths a USING(acquisition_id)
            WHERE a.method != 'shop'"""
        ).fetchall()
        bad_panel = self.connection.execute(
            """SELECT lr.acquisition_id FROM lucky_panel_rewards lr
            JOIN item_acquisition_paths a USING(acquisition_id)
            WHERE a.method != 'lucky_panel'"""
        ).fetchall()
        self.assertEqual(bad_shop, [])
        self.assertEqual(bad_panel, [])
        missing_shop = self.connection.execute(
            """SELECT a.acquisition_id FROM item_acquisition_paths a
            LEFT JOIN shop_inventory si USING(acquisition_id)
            WHERE a.method = 'shop' AND si.acquisition_id IS NULL"""
        ).fetchall()
        missing_panel = self.connection.execute(
            """SELECT a.acquisition_id FROM item_acquisition_paths a
            LEFT JOIN lucky_panel_rewards lr USING(acquisition_id)
            WHERE a.method = 'lucky_panel' AND lr.acquisition_id IS NULL"""
        ).fetchall()
        self.assertEqual(missing_shop, [])
        self.assertEqual(missing_panel, [])

    def test_route_level_supply_does_not_create_item_exclusivity(self):
        rows = self.connection.execute(
            """SELECT method, supply_type FROM item_acquisition_paths
            WHERE item_id = 'item_cottontail_costume'
            ORDER BY acquisition_id"""
        ).fetchall()
        self.assertEqual([tuple(row) for row in rows], [
            ("lucky_panel", "renewable"), ("lucky_panel", "renewable")
        ])

    def test_lucky_panel_treasure_chest_matrices_are_version_scoped(self):
        pools = dict(self.connection.execute(
            """SELECT game_version, COUNT(lr.acquisition_id)
            FROM lucky_panel_pools lp JOIN lucky_panel_rewards lr USING(pool_id)
            WHERE chest_tier = 'treasure_chest' AND game_version IN ('2', '3')
            GROUP BY game_version"""
        ).fetchall())
        self.assertEqual(pools, {"2": 3, "3": 11})
        invented_values = self.connection.execute(
            """SELECT COUNT(*) FROM lucky_panel_rewards lr
            JOIN lucky_panel_pools lp USING(pool_id)
            WHERE lp.chest_tier = 'treasure_chest'
              AND lp.game_version IN ('2', '3')
              AND (lr.slot_count IS NOT NULL OR lr.probability_text IS NOT NULL)"""
        ).fetchone()[0]
        self.assertEqual(invented_values, 0)

    def test_lucky_panel_version_3_rank_1_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v3_rank_1_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 25)
        self.assertIn("Chain Whip", {row["name"] for row in rows})
        self.assertIn("Stellar Fan", {row["name"] for row in rows})
        self.assertTrue(all(
            "Version 3" in row["locator"] and "Rank 1" in row["locator"]
            for row in rows
        ))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_3_rank_2_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.verification_status,
                lr.probability_text, lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v3_rank_2_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 36)
        self.assertIn("Assassin's Dagger", {row["name"] for row in rows})
        self.assertIn("Pillager's Helmet", {row["name"] for row in rows})
        self.assertTrue(all(
            "Version 3" in row["locator"] and "Rank 2" in row["locator"]
            for row in rows
        ))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_3_rank_3_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, lr.probability_text, lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v3_rank_3_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 31)
        self.assertIn("Princess's Robe", {row["name"] for row in rows})
        self.assertIn("Zombiesbane", {row["name"] for row in rows})
        self.assertTrue(all(
            "Version 3" in row["locator"] and "Rank 3" in row["locator"]
            for row in rows
        ))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_3_rank_4_preserves_exclusivity_qualifiers(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.prerequisite_json,
                lr.probability_text, lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v3_rank_4_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 21)
        by_name = {row["name"]: row for row in rows}
        for name in ("Fire Blade", "Metal Goomerang", "Thinking Cap"):
            self.assertIn("Lucky Panel exclusive", by_name[name]["locator"])
            self.assertEqual(
                json.loads(by_name[name]["prerequisite_json"])["source_qualifier"],
                "Lucky Panel exclusive",
            )
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_2_rank_1_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.available_from_checkpoint_id,
                a.unavailable_after_checkpoint_id, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v2_rank_1_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 31)
        self.assertIn("Wizard's Staff", {row["name"] for row in rows})
        self.assertTrue(all(
            "Version 2" in row["locator"] and "Rank 1" in row["locator"]
            for row in rows
        ))
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_010_alltrades_present"
            for row in rows
        ))
        self.assertTrue(all(row["unavailable_after_checkpoint_id"] is None for row in rows))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_2_rank_2_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.available_from_checkpoint_id,
                a.unavailable_after_checkpoint_id, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v2_rank_2_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 31)
        self.assertIn("Scholar's Specs", {row["name"] for row in rows})
        self.assertIn("Stellar Fan", {row["name"] for row in rows})
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_010_alltrades_present"
            for row in rows
        ))
        self.assertTrue(all(row["unavailable_after_checkpoint_id"] is None for row in rows))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_2_rank_3_preserves_qualifiers(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.prerequisite_json,
                a.available_from_checkpoint_id, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v2_rank_3_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 33)
        by_name = {row["name"]: row for row in rows}
        self.assertIn("Lucky Panel or enemy drop", by_name["Staff of Salvation"]["locator"])
        self.assertEqual(
            json.loads(by_name["Staff of Salvation"]["prerequisite_json"])["source_qualifier"],
            "Lucky Panel or enemy drop",
        )
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_010_alltrades_present"
            for row in rows
        ))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_1_rank_1_preserves_published_scope(self):
        rows = self.connection.execute(
            """SELECT i.name, a.time_period, a.available_from_checkpoint_id,
                a.unavailable_after_checkpoint_id, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v1_rank_1_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 23)
        names = {row["name"] for row in rows}
        self.assertIn("Bamboo Spear", names)
        self.assertIn("Wayfarer's Clothes", names)
        self.assertIn("Slime Earring", names)
        self.assertTrue(all(row["time_period"] == "Past" for row in rows))
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_009_alltrades"
            for row in rows
        ))
        self.assertTrue(all(row["unavailable_after_checkpoint_id"] is None for row in rows))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_1_rank_2_preserves_scope_and_exclusivity(self):
        rows = self.connection.execute(
            """SELECT i.name, a.locator, a.prerequisite_json, a.time_period,
                a.available_from_checkpoint_id, a.unavailable_after_checkpoint_id,
                lr.probability_text, lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v1_rank_2_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 32)
        by_name = {row["name"]: row for row in rows}
        self.assertIn("Iron Claws", by_name)
        self.assertIn("Lucky Panel exclusive", by_name["Cottontail Costume"]["locator"])
        self.assertEqual(
            json.loads(by_name["Cottontail Costume"]["prerequisite_json"])["source_qualifier"],
            "Lucky Panel exclusive",
        )
        self.assertIn("Scale Armour", by_name)
        self.assertIn("Slime Earring", by_name)
        self.assertTrue(all(row["time_period"] == "Past" for row in rows))
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_009_alltrades"
            for row in rows
        ))
        self.assertTrue(all(row["unavailable_after_checkpoint_id"] is None for row in rows))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_lucky_panel_version_1_rank_3_preserves_names_and_timing(self):
        rows = self.connection.execute(
            """SELECT i.name, a.time_period, a.available_from_checkpoint_id,
                a.unavailable_after_checkpoint_id, lr.probability_text,
                lp.entry_cost
            FROM lucky_panel_pools lp
            JOIN lucky_panel_rewards lr USING(pool_id)
            JOIN item_acquisition_paths a USING(acquisition_id)
            JOIN items i USING(item_id)
            WHERE lp.pool_id = 'lp_pilgrims_rest_v1_rank_3_standard'
            ORDER BY i.name"""
        ).fetchall()
        self.assertEqual(len(rows), 19)
        names = {row["name"] for row in rows}
        self.assertIn("Stellar Fan", names)
        self.assertIn("Steel Fangs", names)
        self.assertIn("Magic Vetment", names)
        self.assertTrue(all(row["time_period"] == "Past" for row in rows))
        self.assertTrue(all(
            row["available_from_checkpoint_id"] == "cp_009_alltrades"
            for row in rows
        ))
        self.assertTrue(all(row["unavailable_after_checkpoint_id"] is None for row in rows))
        self.assertTrue(all(row["probability_text"] is None for row in rows))
        self.assertTrue(all(row["entry_cost"] is None for row in rows))

    def test_item_report_includes_shop_price_and_alternate_panel_routes(self):
        crackers, cracker_routes = load_item_routes(self.db_path, "Pilchard Crackers")
        self.assertEqual(crackers["heroic_hoarder_required"], 1)
        self.assertEqual(cracker_routes[0]["price"], 5)
        costume, costume_routes = load_item_routes(
            self.db_path, "item_cottontail_costume"
        )
        self.assertEqual(costume["name"], "Cottontail Costume")
        self.assertEqual(len(costume_routes), 2)
        self.assertTrue(all(row["method"] == "lucky_panel" for row in costume_routes))

    def test_purchase_advice_preserves_unknown_and_free_routes(self):
        _, crackers, cracker_verdict = load_purchase_advice(
            self.db_path, "Pilchard Crackers", "cp_001_prologue"
        )
        self.assertEqual(crackers[0]["cost_status"], "paid")
        self.assertTrue(cracker_verdict.startswith("NO VERIFIED FREE ROUTE"))
        _, costume, costume_verdict = load_purchase_advice(
            self.db_path, "Cottontail Costume", "cp_001_prologue"
        )
        self.assertTrue(all(row["cost_status"] == "unknown" for row in costume))
        self.assertTrue(costume_verdict.startswith("UNRESOLVED"))
        _, cautery, cautery_verdict = load_purchase_advice(
            self.db_path, "Cautery Sword", "cp_009_alltrades"
        )
        free_chest = next(row for row in cautery if row["method"] == "chest")
        self.assertEqual(free_chest["timing_status"], "available_now")
        self.assertNotIn("acquisition evidence conflict", cautery_verdict)

    def test_new_equipment_routes_preserve_free_and_unknown_timing(self):
        _, mask_routes, mask_verdict = load_purchase_advice(
            self.db_path, "Iron Mask", "cp_009_alltrades"
        )
        closet = next(row for row in mask_routes if row["method"] == "other")
        self.assertEqual((closet["timing_status"], closet["cost_status"]),
                         ("available_now", "free"))
        self.assertTrue(mask_verdict.startswith("DON'T BUY FOR COMPLETION"))
        _, armour_routes, armour_verdict = load_purchase_advice(
            self.db_path, "Iron Armour", "cp_009_alltrades"
        )
        drops = [row for row in armour_routes if row["method"] == "drop"]
        self.assertTrue(drops)
        self.assertTrue(all(row["timing_status"] == "unknown_gate" for row in drops))
        self.assertTrue(armour_verdict.startswith("UNRESOLVED"))
        _, platinum_routes, platinum_verdict = load_purchase_advice(
            self.db_path, "Platinum Shield", "cp_022_almighty"
        )
        basement = next(row for row in platinum_routes if row["method"] == "chest")
        self.assertEqual((basement["timing_status"], basement["cost_status"]),
                         ("available_now", "free"))
        self.assertTrue(platinum_verdict.startswith("DON'T BUY FOR COMPLETION"))
        _, aeras_routes, aeras_verdict = load_purchase_advice(
            self.db_path, "Aeras Shield", "cp_028_cathedral_of_blight"
        )
        reward = next(row for row in aeras_routes if row["method"] == "reward")
        self.assertEqual((reward["timing_status"], reward["cost_status"]),
                         ("available_now", "free"))
        self.assertTrue(aeras_verdict.startswith("DON'T BUY FOR COMPLETION"))

    def test_sourced_documents_have_locators(self):
        rows = self.connection.execute(
            """SELECT document_id FROM documents
            WHERE source_id IS NOT NULL AND (locator IS NULL OR trim(locator) = '')"""
        ).fetchall()
        self.assertEqual(rows, [])

    def test_ingested_medal_numbers_are_contiguous(self):
        numbers = [
            row[0]
            for row in self.connection.execute(
                "SELECT medal_number FROM mini_medal_locations ORDER BY medal_number"
            )
        ]
        self.assertEqual(numbers, list(range(1, 101)))

    def test_medal_report_respects_later_key_gates(self):
        rows = medals_available_through(self.db_path, "cp_009_alltrades")
        numbers = {row["medal_number"] for row in rows}
        self.assertIn(6, numbers)
        self.assertNotIn(3, numbers)
        self.assertNotIn(5, numbers)
        self.assertNotIn(7, numbers)

    def test_verified_medals_retain_independent_evidence(self):
        verified = self.connection.execute(
            """SELECT medal_number FROM mini_medal_locations
            WHERE verification_status LIKE 'cross_source_checked%'
            ORDER BY medal_number"""
        ).fetchall()
        evidence = self.connection.execute(
            """SELECT DISTINCT medal_number FROM mini_medal_evidence
            WHERE source_id = 'rpgsite_walkthrough'
            ORDER BY medal_number"""
        ).fetchall()
        self.assertEqual(verified, evidence)

    def test_checkpoint_sequences_are_contiguous(self):
        sequences = [
            row[0]
            for row in self.connection.execute(
                "SELECT sequence_no FROM checkpoints ORDER BY sequence_no"
            )
        ]
        self.assertEqual(sequences, list(range(1, len(sequences) + 1)))

    def test_vocation_requirement_ids_are_stable(self):
        groups = {
            row[0]
            for row in self.connection.execute(
                "SELECT DISTINCT group_id FROM vocation_requirements"
            )
        }
        self.assertIn("req_gladiator", groups)
        self.assertIn("req_hero", groups)
        self.assertFalse(any(group.startswith("req_group_") for group in groups))

    def test_player_state_is_valid_json_and_unknown_by_default(self):
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"))
        self.assertIsNone(state["story"]["checkpoint_id"])
        self.assertEqual(state["source_type"], "player_report")

    def test_player_state_update_targets_explicit_file(self):
        source = ROOT / "player" / "ryan-save-state.json"
        state_path = Path(self.tempdir.name) / "player-state.json"
        state_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

        update_state(state_path, "party.members.Hero.level", "12")

        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["party"]["members"]["Hero"]["level"], 12)
        self.assertIsNotNone(state["last_updated"])

    def test_player_state_update_rejects_unknown_path(self):
        source = ROOT / "player" / "ryan-save-state.json"
        state_path = Path(self.tempdir.name) / "player-state-invalid.json"
        state_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

        with self.assertRaises(KeyError):
            update_state(state_path, "party.members.Hero.unknown", "12")

    def test_player_state_update_accepts_json_list_and_rejects_type_change(self):
        source = ROOT / "player" / "ryan-save-state.json"
        state_path = Path(self.tempdir.name) / "player-state-list.json"
        state_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        update_state(state_path, "completion.mini_medals_found", "[1, 2]")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["completion"]["mini_medals_found"], [1, 2])
        with self.assertRaises(TypeError):
            update_state(state_path, "completion.mini_medals_found", "not-a-list")

    def test_checkpoint_report_surfaces_stop_warning_and_medals(self):
        report = load_report(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_001_prologue",
        )
        stops = [row for row in report["obligations"] if row["stop_before_advancing"]]
        self.assertEqual([row["subject"] for row in stops], ["Pearl's Fish Bits"])
        self.assertEqual([row["medal_number"] for row in report["medals"]], [6, 7])
        self.assertFalse(report["player_checkpoint_matches"])

    def test_checkpoint_report_requires_known_checkpoint(self):
        with self.assertRaises(ValueError):
            load_report(
                self.db_path,
                ROOT / "player" / "ryan-save-state.json",
                "cp_missing",
            )

    def test_early_walkthrough_orders_range_and_classifies_medals(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
        )
        self.assertEqual(
            [row["checkpoint"]["sequence_no"] for row in report["blocks"]],
            list(range(1, 10)),
        )
        prologue = report["blocks"][0]
        self.assertEqual([row["subject"] for row in prologue["stops"]], ["Pearl's Fish Bits"])
        self.assertEqual(prologue["medals_now"], [])
        self.assertEqual(
            [row["medal_number"] for row in prologue["medals_later"]], [6, 7]
        )
        alltrades = report["blocks"][-1]
        alltrades_subjects = [row["subject"] for row in alltrades["now"]]
        self.assertEqual(
            alltrades_subjects,
            [
                "Alltrades route Blue Fragments",
                "Proficient Paneller and Platinum Paneller",
                "Lucky Panel Version 1 Cottontail Costume and Elevating Shoes",
                "Pilgrim's Perdition through Dungeon of Descent finite pickups",
                "Alltrades Key and Tunnel to the Abbey fixed loot",
                "Allblades Arena vocation access and fixed pickups",
                "Restored Alltrades Abbey pickups",
                "Thief's Key and immediate backtracking",
            ],
        )
        self.assertIn(6, [row["medal_number"] for row in alltrades["medals_backtrack"]])
        self.assertNotIn(7, [row["medal_number"] for row in alltrades["medals_backtrack"]])
        self.assertTrue(alltrades["guidance"])

    def test_early_walkthrough_hides_collected_medals(self):
        state_path = Path(self.tempdir.name) / "walkthrough-state.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["completion"]["mini_medals_found"] = [6]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_walkthrough(self.db_path, state_path)
        all_medals = [
            row["medal_number"]
            for block in report["blocks"]
            for bucket in ("medals_now", "medals_backtrack", "medals_later")
            for row in block[bucket]
        ]
        self.assertNotIn(6, all_medals)
        self.assertEqual(report["collected_medal_count"], 1)

    def test_walkthrough_generalizes_through_cp033(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_010_alltrades_present",
            "cp_033_arena_achievement_cleanup",
        )
        self.assertEqual(
            [block["checkpoint"]["sequence_no"] for block in report["blocks"]],
            list(range(10, 34)),
        )
        for block in report["blocks"]:
            orders = [row["display_order"] for row in block["stops"] + block["now"]]
            self.assertTrue(all(isinstance(order, int) and order > 0 for order in orders))
            self.assertEqual(len(orders), len(set(orders)))

        flying_carpet = report["blocks"][3]
        self.assertIn(
            5, [row["medal_number"] for row in flying_carpet["medals_backtrack"]]
        )
        self.assertNotIn(
            3, [row["medal_number"] for row in flying_carpet["medals_backtrack"]]
        )

        roamer_return = report["blocks"][2]
        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough({**report, "blocks": [roamer_return]})
        self.assertIn("seed_partial", output.getvalue())
        self.assertIn("partial audit; not a guarantee", output.getvalue())
        self.assertIn("guidance not normalized", output.getvalue())

    def test_postgame_walkthrough_tracks_all_final_medals_and_no_fake_stops(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_030_postgame_another_world",
            "cp_033_arena_achievement_cleanup",
        )
        self.assertEqual(
            [block["checkpoint"]["sequence_no"] for block in report["blocks"]],
            [30, 31, 32, 33],
        )
        self.assertTrue(all(not block["stops"] for block in report["blocks"]))
        medal_numbers = {
            row["medal_number"]
            for block in report["blocks"]
            for bucket in ("medals_now", "medals_backtrack", "medals_later")
            for row in block[bucket]
        }
        self.assertTrue(set(range(95, 101)).issubset(medal_numbers))
        self.assertEqual(len(report["blocks"][2]["now"]), 11)
        self.assertEqual(len(report["blocks"][3]["now"]), 8)

    def test_walkthrough_wrapper_preserves_legacy_entry_point(self):
        self.assertIs(walkthrough_main, early_walkthrough_main)

    def test_walkthrough_rejects_requested_unordered_checkpoint(self):
        unordered_db = Path(self.tempdir.name) / "unordered-walkthrough.sqlite"
        build_database(unordered_db)
        with sqlite3.connect(unordered_db) as connection:
            connection.execute(
                """UPDATE checkpoint_obligations SET display_order = NULL
                WHERE checkpoint_id = 'cp_010_alltrades_present'"""
            )
        with self.assertRaisesRegex(ValueError, "not ordered yet"):
            load_walkthrough(
                unordered_db,
                ROOT / "player" / "ryan-save-state.json",
                "cp_010_alltrades_present",
                "cp_010_alltrades_present",
            )

    def test_cp010_progress_uses_stable_order(self):
        state_path = Path(self.tempdir.name) / "cp010-progress.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(
            state_path, self.db_path, "done", ["cp_010_alltrades_present", "1"]
        )
        report = load_walkthrough(
            self.db_path,
            state_path,
            "cp_010_alltrades_present",
            "cp_010_alltrades_present",
        )
        remaining = [row["display_order"] for row in report["blocks"][0]["now"]]
        self.assertNotIn(1, remaining)
        self.assertTrue(all(order > 1 for order in remaining))

    def test_early_walkthrough_rejects_bad_ranges_and_state(self):
        state_path = ROOT / "player" / "ryan-save-state.json"
        with self.assertRaises(ValueError):
            load_walkthrough(
                self.db_path, state_path, "cp_009_alltrades", "cp_001_prologue"
            )
        with self.assertRaises(ValueError):
            load_walkthrough(self.db_path, state_path, "cp_missing", "cp_009_alltrades")
        bad_state_path = Path(self.tempdir.name) / "walkthrough-bad-state.json"
        state = json.loads(state_path.read_text())
        state["completion"]["mini_medals_found"] = "unknown"
        bad_state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_walkthrough(self.db_path, bad_state_path)

    def test_early_walkthrough_sources_are_opt_in(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_001_prologue",
            "cp_001_prologue",
        )
        terse = io.StringIO()
        with redirect_stdout(terse):
            print_walkthrough(report)
        self.assertIn("medal tracking unknown", terse.getvalue())
        self.assertNotIn("Source:", terse.getvalue())
        self.assertNotIn("Medals NOW:", terse.getvalue())
        self.assertIn("Medals LATER:", terse.getvalue())

        sourced = io.StringIO()
        with redirect_stdout(sourced):
            print_walkthrough(report, include_sources=True)
        self.assertIn("Source:", sourced.getvalue())
        self.assertIn("https://game8.co/", sourced.getvalue())

    def test_checkpoint_advice_filters_orders_and_renders_goals(self):
        advice_db = Path(self.tempdir.name) / "walkthrough-advice.sqlite"
        build_database(advice_db)
        with sqlite3.connect(advice_db) as connection:
            rows = [
                ("advice_test_boss", "boss", "Test Boss", "Guard, then strike.",
                 "completion_safe", 91, 1),
                ("advice_test_gear", "gear", "Hero", "Equip the test sword.",
                 "immediate_power", 91, 1),
                ("advice_test_hidden", "grind", "Slimes", "Unverified loop.",
                 "both", 91, 0),
            ]
            connection.executemany(
                """INSERT INTO checkpoint_advice(
                    advice_id, checkpoint_id, advice_type, subject, advice_text,
                    recommendation_goal, display_order, applicability_json,
                    ready_for_play, source_id, locator, confidence,
                    verification_status
                ) VALUES (?, 'cp_009_alltrades', ?, ?, ?, ?, ?, '{}', ?,
                    'game8_best_equipment', 'Test locator', 'high', 'source_checked')""",
                rows,
            )
        report = load_walkthrough(
            advice_db,
            ROOT / "player" / "ryan-save-state.json",
            "cp_009_alltrades",
            "cp_009_alltrades",
        )
        advice = report["blocks"][0]["advice"]
        fixture_advice = [
            row for row in advice if row["advice_id"].startswith("advice_test_")
        ]
        self.assertEqual(
            [row["advice_type"] for row in fixture_advice], ["gear", "boss"]
        )
        terse = io.StringIO()
        with redirect_stdout(terse):
            print_walkthrough(report)
        self.assertIn("Hero — Equip the test sword. (power)", terse.getvalue())
        self.assertIn("Test Boss — Guard, then strike. (safe)", terse.getvalue())
        self.assertNotIn("Unverified loop", terse.getvalue())
        self.assertNotIn("Source:", terse.getvalue())
        sourced = io.StringIO()
        with redirect_stdout(sourced):
            print_walkthrough(report, include_sources=True)
        self.assertIn("Source:", sourced.getvalue())
        self.assertIn("Test locator", sourced.getvalue())

    def test_threshold_advice_remains_conditional_when_medals_unknown(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_007_frobisher",
            "cp_007_frobisher",
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough(report)
        self.assertIn("If you have 15 medals", output.getvalue())

    def test_checkpoint_advice_requires_object_applicability(self):
        normalized = normalize_checkpoint_advice([
            {"advice_id": "ok", "applicability": {"difficulty": "normal"}}
        ])
        self.assertEqual(
            json.loads(normalized[0]["applicability_json"]),
            {"difficulty": "normal"},
        )
        with self.assertRaises(ValueError):
            normalize_checkpoint_advice([
                {"advice_id": "bad", "applicability": ["normal"]}
            ])

    def test_alltrades_boss_and_vocation_advice_is_chronological(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_009_alltrades",
            "cp_009_alltrades",
        )
        advice = report["blocks"][0]["advice"]
        bosses = [row["subject"] for row in advice if row["advice_type"] == "boss"]
        self.assertEqual(
            bosses,
            [
                "Arena 1: Numpton's Numpties",
                "Arena 2: Bronson and the Bristles",
                "Arena 3: Hans and the Hands",
                "Arena 4: Nava's Knaves",
                "Cardinal Sin",
            ],
        )
        self.assertEqual(
            len([row for row in advice if row["advice_type"] == "vocation"]), 2
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough(report)
        rendered = output.getvalue()
        self.assertLess(rendered.index("Boss:"), rendered.index("NOW:"))
        self.assertLess(rendered.index("Vocations:"), rendered.index("NOW:"))
        self.assertNotIn("CONFLICT: Cautery Sword — precise location description disputed", rendered)
        self.assertNotIn("CONFLICT: Iron Shield — purchase price disputed", rendered)
        self.assertNotIn("Source A:", rendered)
        sourced = io.StringIO()
        with redirect_stdout(sourced):
            print_walkthrough(report, include_sources=True)
        self.assertIn("https://", sourced.getvalue())

    def test_first_ten_hours_cover_all_direct_boss_sequences(self):
        rows = self.connection.execute(
            """SELECT advice_id, checkpoint_id, subject, display_order, source_id,
                locator, verification_status
            FROM checkpoint_advice
            WHERE advice_id IN (
                'advice_cp002_tribulators', 'advice_cp003_golem',
                'advice_cp003_crabble_maeve_sequence',
                'advice_cp007_tinpot_dictator', 'advice_cp007_slaughtomaton',
                'advice_cp008_florin', 'advice_cp008_guardians_roamers')
            ORDER BY checkpoint_id, display_order"""
        ).fetchall()
        self.assertEqual([row["subject"] for row in rows], [
            "Tribulators", "Golem", "Crabble-Rouser and Maeve",
            "Tinpot Dictator", "Slaughtomaton", "Florin",
            "Guardians of the Roamers",
        ])
        self.assertTrue(all(row["source_id"].startswith("game8_") for row in rows))
        self.assertTrue(all(row["locator"] for row in rows))
        self.assertTrue(all(row["verification_status"] == "source_checked"
                            for row in rows))

    def test_cp011_through_cp020_boss_sequences_are_complete(self):
        expected = {
            "cp_011_la_bravoure": ["Skeleton Squire", "Setesh the Punisher"],
            "cp_013_flying_carpet": ["Sunken Spirits", "Gracos", "King Slime",
                                      "Ethereal Serpent"],
            "cp_015_greenthumb": ["Rainiac"],
            "cp_016_hubble": ["The Envoy", "Hybris"],
            "cp_019_aeolus": ["Vaipur", "Cumulus Vex"],
        }
        for checkpoint_id, subjects in expected.items():
            rows = self.connection.execute(
                """SELECT subject, source_id, locator FROM checkpoint_advice
                WHERE checkpoint_id=? AND advice_type='boss'
                ORDER BY display_order, advice_id""", (checkpoint_id,)
            ).fetchall()
            self.assertEqual([row["subject"] for row in rows], subjects)
            self.assertTrue(all(row["source_id"].startswith("game8_boss_")
                                for row in rows))
            self.assertTrue(all(row["locator"] for row in rows))

    def test_late_game_missing_boss_sequences_are_normalized(self):
        expected = {
            "cp_021_malign_shrine": ["The Time Being", "Orgodemir first fight"],
            "cp_026_elemental_cleanup_nottagen": ["Moostapha", "Malign Vine"],
            "cp_027_deja_vous_rucker": ["Lourgh and Disorder"],
            "cp_030_postgame_another_world": ["The Almighty"],
            "cp_032_yet_another_world": [
                "Xenlon", "The Almighty and Four Spirits"
            ],
        }
        for checkpoint_id, subjects in expected.items():
            rows = self.connection.execute(
                """SELECT subject, source_id, locator, verification_status
                FROM checkpoint_advice
                WHERE checkpoint_id=? AND advice_type='boss'
                ORDER BY display_order, advice_id""", (checkpoint_id,)
            ).fetchall()
            self.assertEqual([row["subject"] for row in rows], subjects)
            self.assertTrue(all(row["source_id"].startswith("game8_boss_")
                                for row in rows))
            self.assertTrue(all(row["locator"] for row in rows))
            self.assertTrue(all("no_level_claim" in row["verification_status"]
                                or row["subject"] in {
                                    "Orgodemir first fight",
                                    "The Almighty and Four Spirits",
                                } for row in rows))

    def test_medal_tracking_preserves_unknown_and_inconsistent_states(self):
        self.assertEqual(classify_medal_tracking(None, set()), ("unknown", None))
        partial, partial_warning = classify_medal_tracking(None, {1})
        self.assertEqual(partial, "partial")
        self.assertIn("unknown", partial_warning)
        inconsistent, warning = classify_medal_tracking(2, {1})
        self.assertEqual(inconsistent, "inconsistent")
        self.assertIn("disagrees", warning)
        self.assertEqual(classify_medal_tracking(1, {1}), ("known", None))

    def test_walkthrough_cli_defaults_to_saved_checkpoint_or_cp001(self):
        default_state = ROOT / "player" / "ryan-save-state.json"
        self.assertEqual(
            resolve_checkpoint_range(default_state, None, None, None),
            ("cp_001_prologue", "cp_001_prologue"),
        )
        state_path = Path(self.tempdir.name) / "walkthrough-checkpoint-state.json"
        state = json.loads(default_state.read_text())
        state["story"]["checkpoint_id"] = "cp_004_emberdale"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(
            resolve_checkpoint_range(state_path, None, None, None),
            ("cp_004_emberdale", "cp_004_emberdale"),
        )
        self.assertEqual(
            resolve_checkpoint_range(state_path, "cp_005_larca", None, None),
            ("cp_005_larca", "cp_005_larca"),
        )
        self.assertEqual(
            resolve_checkpoint_range(
                state_path, None, "cp_001_prologue", "cp_009_alltrades"
            ),
            ("cp_001_prologue", "cp_009_alltrades"),
        )
        with self.assertRaises(ValueError):
            resolve_checkpoint_range(
                state_path, "cp_005_larca", "cp_001_prologue", "cp_009_alltrades"
            )
        with self.assertRaises(ValueError):
            resolve_checkpoint_range(state_path, None, "cp_001_prologue", None)

    def test_player_progress_records_only_explicit_changes(self):
        state_path = Path(self.tempdir.name) / "explicit-progress.json"
        source = ROOT / "player" / "ryan-save-state.json"
        state_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        update_progress(state_path, self.db_path, "checkpoint", ["cp_004_emberdale"])
        state = json.loads(state_path.read_text())
        self.assertEqual(state["story"]["checkpoint_id"], "cp_004_emberdale")
        self.assertEqual(state["completion"]["obligations_completed"], [])

        update_progress(state_path, self.db_path, "medal-found", ["1", "2", "1"])
        state = json.loads(state_path.read_text())
        self.assertEqual(state["completion"]["mini_medals_found"], [1, 2])
        update_progress(state_path, self.db_path, "medal-undo", ["1"])
        state = json.loads(state_path.read_text())
        self.assertEqual(state["completion"]["mini_medals_found"], [2])
        self.assertIsNone(state["completion"]["mini_medal_count"])
        update_progress(state_path, self.db_path, "medal-count", ["5"])
        state = json.loads(state_path.read_text())
        self.assertEqual(state["completion"]["mini_medal_count"], 5)
        self.assertEqual(state["completion"]["mini_medals_found"], [2])

    def test_player_progress_done_is_stable_idempotent_and_reversible(self):
        state_path = Path(self.tempdir.name) / "explicit-done.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        update_progress(state_path, self.db_path, "done", ["cp_001_prologue", "1"])
        update_progress(state_path, self.db_path, "done", ["cp_001_prologue", "1"])
        state = json.loads(state_path.read_text())
        self.assertEqual(
            state["completion"]["obligations_completed"],
            ["obl_prologue_initial_finite_sweep"],
        )
        report = load_walkthrough(
            self.db_path, state_path, "cp_001_prologue", "cp_001_prologue"
        )
        self.assertEqual([row["display_order"] for row in report["blocks"][0]["now"]], [2])
        update_progress(state_path, self.db_path, "undo", ["cp_001_prologue", "1"])
        state = json.loads(state_path.read_text())
        self.assertEqual(state["completion"]["obligations_completed"], [])

    def test_player_progress_rejects_invalid_input_without_writing(self):
        state_path = Path(self.tempdir.name) / "explicit-invalid.json"
        state_path.write_text(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        original = state_path.read_text(encoding="utf-8")
        for command, values in (
            ("checkpoint", ["cp_missing"]),
            ("medal-found", ["101"]),
            ("medal-count", ["-1"]),
            ("done", ["cp_001_prologue", "99"]),
        ):
            with self.assertRaises(ValueError):
                update_progress(state_path, self.db_path, command, values)
            self.assertEqual(state_path.read_text(encoding="utf-8"), original)

    def test_walkthrough_distinguishes_cleared_stops_and_unknown_ids(self):
        state_path = Path(self.tempdir.name) / "explicit-stop.json"
        state = json.loads(
            (ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8")
        )
        state["completion"]["obligations_completed"] = [
            "obl_prologue_fish_bits", "obsolete_obligation"
        ]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = load_walkthrough(
            self.db_path, state_path, "cp_001_prologue", "cp_001_prologue"
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough(report)
        self.assertIn("All recorded warnings cleared", output.getvalue())
        self.assertIn("obsolete_obligation", output.getvalue())
        self.assertIn("completed checks hidden: 1", output.getvalue())

    def test_compact_walkthrough_hides_boilerplate_but_keeps_actions_and_safety(self):
        report = load_walkthrough(
            self.db_path,
            ROOT / "player" / "ryan-save-state.json",
            "cp_003_ballymolloy",
            "cp_003_ballymolloy",
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough(report, compact=True)
        rendered = output.getvalue()
        self.assertNotIn("Chronological walkthrough", rendered)
        self.assertNotIn("No verified STOP recorded", rendered)
        self.assertNotIn("Mark complete:", rendered)
        self.assertNotIn("[complete]", rendered)
        self.assertNotIn("Advice gap:", rendered)
        self.assertIn("NOW:", rendered)
        self.assertIn("SAFE:", rendered)

        output = io.StringIO()
        with redirect_stdout(output):
            print_walkthrough(report, compact=True, include_monsters=True)
        self.assertIn("MONSTERS:", output.getvalue())
        self.assertIn("Cactiball", output.getvalue())

    def test_martial_artist_rank_progression_is_complete_and_sourced(self):
        rows = self.connection.execute(
            """SELECT proficiency_rank, skill_name, locator
            FROM vocation_rank_skills WHERE vocation_id='vocation_martial_artist'
            ORDER BY proficiency_rank"""
        ).fetchall()
        self.assertEqual([row[0] for row in rows], list(range(1, 9)))
        self.assertEqual(rows[0][1], "Clap Trap")
        self.assertEqual(rows[-1][1], "Knuckle Sandwich")
        self.assertTrue(all("★" in row[2] for row in rows))
        perk = self.connection.execute(
            """SELECT perk_name FROM vocation_perks
            WHERE vocation_id='vocation_martial_artist' AND perk_type='let_loose'"""
        ).fetchone()
        self.assertEqual(perk[0], "Critical Stance")

    def test_vocation_detail_report_shows_multi_skill_ranks_and_perk(self):
        report = load_vocation_details(self.db_path, "Mage")
        self.assertEqual(report["vocation"]["vocation_id"], "vocation_mage")
        rank_one = [row["skill_name"] for row in report["skills"] if row["proficiency_rank"] == 1]
        self.assertEqual(rank_one, ["Frizz", "Snooze"])
        self.assertEqual(len(report["perks"]), 1)
        output = io.StringIO()
        with redirect_stdout(output):
            print_vocation_details(report)
        self.assertIn("1★ Frizz", output.getvalue())
        self.assertIn("Let Loose:", output.getvalue())

        champion = load_vocation_details(self.db_path, "Champion")
        self.assertEqual(
            [row["prerequisite_name"] for row in champion["requirements"]],
            ["Gladiator", "Paladin"],
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_vocation_details(champion)
        self.assertIn("Unlock: master all — Gladiator, Paladin", output.getvalue())

    def test_all_beginner_vocation_skill_tables_are_complete_and_sourced(self):
        beginner_ids = [
            row[0] for row in self.connection.execute(
                "SELECT vocation_id FROM vocations WHERE tier='beginner'"
            )
        ]
        self.assertEqual(len(beginner_ids), 10)
        for vocation_id in beginner_ids:
            rows = self.connection.execute(
                """SELECT proficiency_rank, locator, source_id
                FROM vocation_rank_skills WHERE vocation_id=?""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(sorted({row[0] for row in rows}), list(range(1, 9)))
            self.assertTrue(all("★" in row[1] for row in rows))
            self.assertTrue(all(row[2].startswith("game8_vocation_") for row in rows))
            perk = self.connection.execute(
                """SELECT locator FROM vocation_perks
                WHERE vocation_id=? AND perk_type='let_loose'""",
                (vocation_id,),
            ).fetchone()
            self.assertIsNotNone(perk)
            self.assertIn("Overview > Type and Loose Ability", perk[0])

        same_rank = self.connection.execute(
            """SELECT skill_name FROM vocation_rank_skills
            WHERE vocation_id='vocation_mage' AND proficiency_rank=1
            ORDER BY skill_name"""
        ).fetchall()
        self.assertEqual([row[0] for row in same_rank], ["Frizz", "Snooze"])

    def test_all_intermediate_vocation_skill_tables_are_complete_and_sourced(self):
        intermediate_ids = [
            row[0] for row in self.connection.execute(
                "SELECT vocation_id FROM vocations WHERE tier='intermediate'"
            )
        ]
        self.assertEqual(len(intermediate_ids), 7)
        for vocation_id in intermediate_ids:
            rows = self.connection.execute(
                """SELECT proficiency_rank, locator, source_id
                FROM vocation_rank_skills WHERE vocation_id=?""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(sorted({row[0] for row in rows}), list(range(1, 9)))
            self.assertTrue(all("★" in row[1] for row in rows))
            self.assertTrue(all(row[2].startswith("game8_vocation_") for row in rows))
            perk = self.connection.execute(
                """SELECT locator FROM vocation_perks
                WHERE vocation_id=? AND perk_type='let_loose'""",
                (vocation_id,),
            ).fetchone()
            self.assertIsNotNone(perk)
            self.assertIn("Overview > Type and Loose Ability", perk[0])

        same_rank = self.connection.execute(
            """SELECT skill_name FROM vocation_rank_skills
            WHERE vocation_id='vocation_sage' AND proficiency_rank=1
            ORDER BY skill_name"""
        ).fetchall()
        self.assertEqual(
            [row[0] for row in same_rank], ["Insulate", "Midheal", "Squelch"]
        )

    def test_all_advanced_vocation_skill_tables_are_complete_and_sourced(self):
        advanced_ids = [
            row[0] for row in self.connection.execute(
                "SELECT vocation_id FROM vocations WHERE tier='advanced'"
            )
        ]
        self.assertEqual(len(advanced_ids), 3)
        for vocation_id in advanced_ids:
            rows = self.connection.execute(
                """SELECT proficiency_rank, locator, source_id
                FROM vocation_rank_skills WHERE vocation_id=?""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(sorted({row[0] for row in rows}), list(range(1, 9)))
            self.assertTrue(all("★" in row[1] for row in rows))
            self.assertTrue(all(row[2].startswith("game8_vocation_") for row in rows))
            perk = self.connection.execute(
                """SELECT locator FROM vocation_perks
                WHERE vocation_id=? AND perk_type='let_loose'""",
                (vocation_id,),
            ).fetchone()
            self.assertIsNotNone(perk)
            self.assertIn("Overview > Type and Loose Ability", perk[0])

        hero_rank_five = self.connection.execute(
            """SELECT skill_name FROM vocation_rank_skills
            WHERE vocation_id='vocation_hero' AND proficiency_rank=5
            ORDER BY skill_name"""
        ).fetchall()
        self.assertEqual([row[0] for row in hero_rank_five], ["Kazing", "Sword Dance"])

    def test_character_exclusive_vocations_match_direct_sources(self):
        expected = {
            "vocation_fledgling_fisherman": ("Hero", list(range(2, 9))),
            "vocation_heir_apparent": ("Kiefer", list(range(2, 9))),
            "vocation_mini_mayoress": ("Maribel", list(range(2, 9))),
            "vocation_wolf_boy": ("Ruff", list(range(4, 9))),
            "vocation_destinys_dancer": ("Aishe", list(range(1, 9))),
            "vocation_chevalier": ("Sir Mervyn", list(range(1, 9))),
        }
        for vocation_id, (character, ranks) in expected.items():
            vocation = self.connection.execute(
                "SELECT exclusive_character FROM vocations WHERE vocation_id=?",
                (vocation_id,),
            ).fetchone()
            self.assertEqual(vocation[0], character)
            rows = self.connection.execute(
                """SELECT proficiency_rank, locator, source_id
                FROM vocation_rank_skills WHERE vocation_id=?""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(sorted({row[0] for row in rows}), ranks)
            self.assertTrue(all("★" in row[1] for row in rows))
            self.assertTrue(all(row[2].startswith("game8_vocation_") for row in rows))
            perk = self.connection.execute(
                """SELECT locator FROM vocation_perks
                WHERE vocation_id=? AND perk_type='let_loose'""",
                (vocation_id,),
            ).fetchone()
            self.assertIsNotNone(perk)
            self.assertIn("Overview > Type and Loose Ability", perk[0])

        destiny_rank_eight = self.connection.execute(
            """SELECT skill_name FROM vocation_rank_skills
            WHERE vocation_id='vocation_destinys_dancer' AND proficiency_rank=8
            ORDER BY skill_name"""
        ).fetchall()
        self.assertEqual(
            [row[0] for row in destiny_rank_eight], ["Death Dance", "Kerplunk Dance"]
        )

    def test_vocation_progression_rules_preserve_setting_and_moonlight_scope(self):
        points = dict(
            self.connection.execute(
                """SELECT event_type, proficiency_points
                FROM vocation_progression_rules
                WHERE proficiency_points IS NOT NULL"""
            ).fetchall()
        )
        self.assertEqual(points, {
            "battle_completion": 7,
            "overworld_instant_defeat": 1,
        })
        settings = {
            row[0] for row in self.connection.execute(
                """SELECT proficiency_setting FROM vocation_progression_rules
                WHERE event_type='difficulty_setting'"""
            )
        }
        self.assertEqual(settings, {"Less", "Normal", "More"})
        seed_rows = self.connection.execute(
            """SELECT rank_delta, affects_both_moonlight_vocations, locator
            FROM vocation_progression_rules
            WHERE event_type='proficiency_seed'
            ORDER BY affects_both_moonlight_vocations"""
        ).fetchall()
        self.assertEqual([(row[0], row[1]) for row in seed_rows], [(1, 0), (1, 1)])
        self.assertTrue(all(row[2].strip() for row in seed_rows))
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM vocation_progression_rules"
            ).fetchone()[0],
            7,
        )

    def test_advanced_vocation_stat_modifiers_are_complete_and_qualitative(self):
        for vocation_id in ("vocation_champion", "vocation_druid", "vocation_hero"):
            rows = self.connection.execute(
                """SELECT stat_key, modifier_direction, modifier_value,
                    proficiency_rank, locator, source_id
                FROM vocation_stat_modifiers WHERE vocation_id=?""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(len(rows), 11)
            self.assertEqual(len({row[0] for row in rows}), 11)
            self.assertTrue(all(row[1] in {"increased", "normal", "decreased"} for row in rows))
            self.assertTrue(all(row[2] is None and row[3] is None for row in rows))
            self.assertTrue(all("Overview > Stat Bonuses >" in row[4] for row in rows))
            self.assertTrue(all(row[5].startswith("game8_vocation_") for row in rows))

        champion_resilience = self.connection.execute(
            """SELECT modifier_direction FROM vocation_stat_modifiers
            WHERE vocation_id='vocation_champion' AND stat_key='resilience'"""
        ).fetchone()[0]
        self.assertEqual(champion_resilience, "normal")

    def test_beginner_and_intermediate_stat_modifiers_are_complete(self):
        vocation_ids = [
            row[0] for row in self.connection.execute(
                """SELECT vocation_id FROM vocations
                WHERE tier IN ('beginner', 'intermediate')"""
            )
        ]
        self.assertEqual(len(vocation_ids), 17)
        for vocation_id in vocation_ids:
            rows = self.connection.execute(
                """SELECT stat_key, modifier_direction, modifier_value,
                    proficiency_rank, locator, source_id
                FROM vocation_stat_modifiers WHERE vocation_id=?""",
                (vocation_id,),
            ).fetchall()
            self.assertEqual(len(rows), 11)
            self.assertEqual(len({row[0] for row in rows}), 11)
            self.assertTrue(all(row[1] in {"increased", "normal", "decreased"} for row in rows))
            self.assertTrue(all(row[2] is None and row[3] is None for row in rows))
            self.assertTrue(all("Overview > Stat Bonuses >" in row[4] for row in rows))
            self.assertTrue(all(row[5].startswith("game8_vocation_") for row in rows))

        shepherd = dict(
            self.connection.execute(
                """SELECT stat_key, modifier_direction FROM vocation_stat_modifiers
                WHERE vocation_id='vocation_shepherd'"""
            ).fetchall()
        )
        self.assertEqual(shepherd["max_hp"], "increased")
        self.assertEqual(shepherd["attack"], "decreased")
        self.assertEqual(shepherd["agility"], "decreased")


if __name__ == "__main__":
    unittest.main()
