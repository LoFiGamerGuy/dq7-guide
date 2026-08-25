from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_kb import build_database  # noqa: E402
from query_kb import search  # noqa: E402


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
        self.assertEqual(self.counts["sources"], 20)
        self.assertEqual(self.counts["vocations"], 26)
        self.assertEqual(self.counts["medal_rewards"], 19)
        self.assertEqual(self.counts["missables"], 7)

    def test_every_claim_has_registered_source(self):
        orphans = self.connection.execute(
            """SELECT c.claim_id FROM claims c
            LEFT JOIN sources s ON s.source_id = c.source_id
            WHERE s.source_id IS NULL"""
        ).fetchall()
        self.assertEqual(orphans, [])

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

    def test_player_state_is_valid_json_and_unknown_by_default(self):
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text(encoding="utf-8"))
        self.assertIsNone(state["story"]["checkpoint_id"])
        self.assertEqual(state["source_type"], "player_report")


if __name__ == "__main__":
    unittest.main()

