from __future__ import annotations

import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_kb import build_database  # noqa: E402
from conflict_report import load_conflicts  # noqa: E402
from guide_server import (  # noqa: E402
    _checkpoint_view,
    _equipment_readiness,
    _farms,
    _monster_hearts,
    _vocation_unlock_progress,
)
from vocation_report import load_vocation_details  # noqa: E402


class GoldenRetrievalQualityTests(unittest.TestCase):
    """Golden evidence bundles for the playthrough answer contract."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.temp.name) / "golden.sqlite"
        cls.state = Path(cls.temp.name) / "state.json"
        build_database(cls.db)
        shutil.copy(ROOT / "player" / "ryan-save-state.json", cls.state)
        cls.questions = {
            row["id"]: row for row in json.loads(
                (ROOT / "data" / "golden_questions.json").read_text(encoding="utf-8")
            )
        }
        cls.connection = sqlite3.connect(cls.db)
        cls.connection.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        cls.temp.cleanup()

    def assert_current_version_source(self, source_id: str, locator: str) -> None:
        row = self.connection.execute(
            "SELECT title, url, role, notes FROM sources WHERE source_id=?",
            (source_id,),
        ).fetchone()
        self.assertIsNotNone(row, source_id)
        haystack = " ".join(str(value or "") for value in row).casefold()
        self.assertFalse(any(token in haystack for token in
                             ("playstation 1", "ps1 version", "3ds version", "nintendo 3ds")))
        self.assertTrue(locator and locator.strip(), source_id)

    def test_golden_manifest_covers_answer_contract(self):
        self.assertEqual(set(self.questions), {
            "safe_advance_alltrades", "strongest_legal_gear_alltrades",
            "champion_vocation_path", "available_farm_alltrades",
            "cactiball_heart", "visible_conflicts",
        })

    def test_safe_advance_bundle_is_checkpoint_scoped_and_cited(self):
        question = self.questions["safe_advance_alltrades"]
        report = _checkpoint_view(self.db, self.state, question["checkpoint_id"])
        self.assertEqual(report["id"], question["checkpoint_id"])
        self.assertGreater(report["advancement_readiness"]["open_required_action_count"], 0)
        self.assertEqual(report["advancement_readiness"]["status"], "required_actions_open")
        for action in report["actions"] + report["stop_actions"]:
            self.assert_current_version_source(action["source"]["id"],
                                               action["source"]["locator"])

    def test_strongest_legal_gear_bundle_keeps_legality_and_advice_separate(self):
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["story"]["checkpoint_id"] = "cp_009_alltrades"
        self.state.write_text(json.dumps(state), encoding="utf-8")
        report = _equipment_readiness(self.db, self.state)
        self.assertTrue(report["recommendations"])
        self.assertFalse(report["editor_supported"])
        self.assertGreater(report["compatibility_coverage"]["verified_item_rows"], 0)
        for row in report["recommendations"]:
            self.assertEqual(row["availability_status"], "route_available")
            self.assert_current_version_source(row["source"]["id"],
                                               row["source"]["locator"])
        for rule in report["mechanics"]:
            self.assertNotEqual(rule["source_id"], rule["corroborating_source_id"])

    def test_vocation_path_bundle_has_rules_costs_and_independent_sources(self):
        details = load_vocation_details(self.db, "Champion")
        progress = _vocation_unlock_progress(self.db, self.state,
                                             "vocation_champion")
        self.assertEqual({row["prerequisite_vocation_id"]
                          for row in details["requirements"]},
                         {"vocation_gladiator", "vocation_paladin"})
        profile = details["progression"]
        self.assertEqual(profile["progression_mode"], "full_points")
        self.assertGreater(profile["normalized_total_points"], 0)
        self.assertNotEqual(profile["source_id"], profile["corroborating_source_id"])
        self.assertEqual(progress["cost_status"], "verified")

    def test_farm_bundle_excludes_later_checkpoint_routes(self):
        report = _farms(self.db, {"through_checkpoint": ["cp_009_alltrades"]})
        self.assertTrue(report["farms"])
        cp009_sequence = self.connection.execute(
            "SELECT sequence_no FROM checkpoints WHERE checkpoint_id='cp_009_alltrades'"
        ).fetchone()[0]
        for farm in report["farms"]:
            sequence = self.connection.execute(
                "SELECT sequence_no FROM checkpoints WHERE checkpoint_id=?",
                (farm["available_from_checkpoint_id"],),
            ).fetchone()[0]
            self.assertLessEqual(sequence, cp009_sequence)
            self.assertEqual(farm["availability_status"], "available_by_checkpoint")
            self.assert_current_version_source(farm["source_id"], farm["locator"])

    def test_heart_bundle_preserves_effect_gate_and_unknown_player_state(self):
        report = _monster_hearts(self.db, {"q": ["Cactiball"]}, self.state)
        self.assertEqual(report["total"], 1)
        heart = report["hearts"][0]
        self.assertEqual(heart["available_from_checkpoint_id"], "cp_011_la_bravoure")
        self.assertIn("100%", heart["effect_text"])
        self.assertIsNone(heart["owned"])
        self.assert_current_version_source(heart["source_id"], heart["locator"])

    def test_conflict_bundle_exposes_both_precisely_cited_claims(self):
        conflicts = load_conflicts(self.db, include_resolved=False)
        self.assertTrue(conflicts)
        for row in conflicts:
            self.assertEqual(row["status"], "unresolved")
            for side in ("a", "b"):
                self.assert_current_version_source(row[f"source_id_{side}"],
                                                   row[f"locator_{side}"])
                self.assertTrue(row[f"value_{side}"])


if __name__ == "__main__":
    unittest.main()
