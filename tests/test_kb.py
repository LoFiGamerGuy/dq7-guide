from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_kb import build_database, detect_conflicts  # noqa: E402
from checkpoint_report import load_report  # noqa: E402
from conflict_report import load_conflicts  # noqa: E402
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
        self.assertEqual(self.counts["sources"], 41)
        self.assertEqual(self.counts["vocations"], 26)
        self.assertEqual(self.counts["medal_rewards"], 19)
        self.assertEqual(self.counts["missables"], 7)
        self.assertEqual(self.counts["mini_medal_locations"], 100)
        self.assertEqual(self.counts["checkpoint_obligations"], 57)
        self.assertEqual(self.counts["mini_medal_evidence"], 86)
        self.assertEqual(self.counts["item_categories"], 6)
        self.assertEqual(self.counts["items"], 16)
        self.assertEqual(self.counts["item_acquisition_paths"], 67)
        self.assertEqual(self.counts["shops"], 19)
        self.assertEqual(self.counts["lucky_panel_pools"], 10)

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
        self.assertTrue(cautery_verdict.startswith("DON'T BUY FOR COMPLETION"))

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


if __name__ == "__main__":
    unittest.main()
