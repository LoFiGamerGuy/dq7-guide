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
from checkpoint_report import load_report  # noqa: E402
from conflict_report import load_conflicts  # noqa: E402
from early_walkthrough import (  # noqa: E402
    classify_medal_tracking,
    load_walkthrough,
    print_walkthrough,
    resolve_checkpoint_range,
)
from medal_report import medals_available_through  # noqa: E402
from item_report import load_item_routes, load_purchase_advice  # noqa: E402
from query_kb import search  # noqa: E402
from update_state import update_state  # noqa: E402


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
        self.assertEqual(self.counts["sources"], 66)
        self.assertEqual(self.counts["vocations"], 26)
        self.assertEqual(self.counts["medal_rewards"], 19)
        self.assertEqual(self.counts["missables"], 7)
        self.assertEqual(self.counts["mini_medal_locations"], 100)
        self.assertEqual(self.counts["checkpoint_obligations"], 84)
        self.assertEqual(self.counts["checkpoint_advice"], 20)
        self.assertEqual(self.counts["mini_medal_evidence"], 86)
        self.assertEqual(self.counts["item_categories"], 6)
        self.assertEqual(self.counts["items"], 30)
        self.assertEqual(self.counts["item_acquisition_paths"], 117)
        self.assertEqual(self.counts["shops"], 32)
        self.assertEqual(self.counts["lucky_panel_pools"], 12)

    def test_every_claim_has_registered_source(self):
        orphans = self.connection.execute(
            """SELECT c.claim_id FROM claims c
            LEFT JOIN sources s ON s.source_id = c.source_id
            WHERE s.source_id IS NULL"""
        ).fetchall()
        self.assertEqual(orphans, [])

    def test_seeded_source_disagreement_is_visible(self):
        row = self.connection.execute(
            """SELECT c.status, c.detection_method
            FROM conflicts c
            WHERE c.claim_a_id = 'claim_medal_078_game8_floor'
              AND c.claim_b_id = 'claim_medal_078_rpgsite_floor'"""
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(tuple(row), ("unresolved", "automatic_exact_scope"))

    def test_phase_two_source_disagreements_are_visible(self):
        pairs = self.connection.execute(
            """SELECT claim_a_id, claim_b_id FROM conflicts
            WHERE claim_a_id LIKE 'claim_elevating_shoes_%'
               OR claim_a_id LIKE 'claim_cautery_sword_%'"""
        ).fetchall()
        self.assertEqual(len(pairs), 2)

    def test_iron_shield_conflict_and_scale_shield_gap_are_visible(self):
        conflict = self.connection.execute(
            """SELECT status FROM conflicts
            WHERE claim_a_id LIKE 'claim_iron_shield_%'
               OR claim_b_id LIKE 'claim_iron_shield_%'"""
        ).fetchone()
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict["status"], "unresolved")
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
        conflict = self.connection.execute(
            """SELECT status FROM conflicts
            WHERE claim_a_id LIKE 'claim_ice_shield_%'
               OR claim_b_id LIKE 'claim_ice_shield_%'"""
        ).fetchone()
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict["status"], "unresolved")
        _, _, verdict = load_purchase_advice(
            self.db_path, "Ice Shield", "cp_013_flying_carpet"
        )
        self.assertIn("acquisition evidence conflict", verdict)

    def test_tempest_shield_location_conflict_is_visible(self):
        conflict = self.connection.execute(
            """SELECT status FROM conflicts
            WHERE claim_a_id LIKE 'claim_tempest_shield_%'
               OR claim_b_id LIKE 'claim_tempest_shield_%'"""
        ).fetchone()
        self.assertIsNotNone(conflict)
        _, _, verdict = load_purchase_advice(
            self.db_path, "Tempest Shield", "cp_025_wind_spirit"
        )
        self.assertIn("acquisition evidence conflict", verdict)

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
        self.assertTrue(cautery_verdict.startswith("UNRESOLVED"))

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


if __name__ == "__main__":
    unittest.main()
