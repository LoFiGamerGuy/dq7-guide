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
        self.assertEqual(self.counts["sources"], 24)
        self.assertEqual(self.counts["vocations"], 26)
        self.assertEqual(self.counts["medal_rewards"], 19)
        self.assertEqual(self.counts["missables"], 7)
        self.assertEqual(self.counts["mini_medal_locations"], 100)
        self.assertEqual(self.counts["checkpoint_obligations"], 45)
        self.assertEqual(self.counts["mini_medal_evidence"], 86)

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
