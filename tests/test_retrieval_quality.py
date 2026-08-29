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
from heart_report import load_heart_report  # noqa: E402
from guide_server import (  # noqa: E402
    _checkpoint_view,
    _equipment_readiness,
    _farms,
    _monster_hearts,
    _vocation_unlock_progress,
)
from player_progress import update_progress  # noqa: E402
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
            "cactiball_heart", "visible_conflicts", "duplicate_accessory_power",
            "achievement_counter_rules",
        })
        strongest = self.questions["strongest_legal_gear_alltrades"]
        self.assertTrue(strongest["requires_exhaustive_candidate_universe"])
        self.assertTrue(strongest["forbids_invented_weighting"])

    def test_retrieval_audit_count_tracks_golden_manifest(self):
        audit = (ROOT / "docs" / "RETRIEVAL_QUALITY.md").read_text(encoding="utf-8")
        self.assertIn(f"defines {len(self.questions)} representative playthrough questions", audit)
        self.assertIn("duplicate-accessory power", audit)
        self.assertIn("achievement-counter\nrules", audit)

    def test_achievement_counter_bundle_preserves_resolution_and_consensus(self):
        question = self.questions["achievement_counter_rules"]
        self.assertTrue(question["requires_source_diversity"])

        gold_claims = self.connection.execute(
            """SELECT c.value_json, c.locator, c.confidence, s.source_id, s.publisher
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key='achievement:massively_minted'
              AND c.predicate='achievement_counter_condition'"""
        ).fetchall()
        lifetime = [row for row in gold_claims
                    if json.loads(row["value_json"]) == "lifetime total gold acquired"]
        self.assertGreaterEqual(len({row["publisher"] for row in lifetime}), 2)
        for row in gold_claims:
            self.assert_current_version_source(row["source_id"], row["locator"])

        conflict = self.connection.execute(
            """SELECT status, resolution_claim_id FROM conflicts
            WHERE conflict_key LIKE
              'achievement:massively_minted|achievement_counter_condition|%'"""
        ).fetchone()
        self.assertEqual(conflict["status"], "resolved")
        resolution_value = self.connection.execute(
            "SELECT value_json FROM claims WHERE claim_id=?",
            (conflict["resolution_claim_id"],),
        ).fetchone()[0]
        self.assertEqual(json.loads(resolution_value), "lifetime total gold acquired")

        roster_claims = self.connection.execute(
            """SELECT c.value_json, c.locator, s.source_id, s.publisher
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key='achievement:metal_mangler'
              AND c.predicate='achievement_counter_members'"""
        ).fetchall()
        self.assertGreaterEqual(len({row["publisher"] for row in roster_claims}), 2)
        rosters = {row["value_json"] for row in roster_claims}
        self.assertEqual(len(rosters), 1)
        self.assertEqual(set(json.loads(rosters.pop())), {
            "Metal Slime", "Liquid Metal Slime", "Metal King Slime",
            "Platinum King",
        })
        for row in roster_claims:
            self.assert_current_version_source(row["source_id"], row["locator"])

        quick_units = self.connection.execute(
            """SELECT c.value_json, c.locator, s.source_id, s.publisher
            FROM claims c JOIN sources s USING(source_id)
            WHERE c.subject_key='achievement:straight_to_the_point'
              AND c.predicate='achievement_counter_unit'"""
        ).fetchall()
        self.assertEqual(len({row["publisher"] for row in quick_units}), 2)
        self.assertEqual({json.loads(row["value_json"]) for row in quick_units},
                         {"successful field-attack instant-kill events"})
        for row in quick_units:
            self.assert_current_version_source(row["source_id"], row["locator"])
        unsupported_overlap = self.connection.execute(
            """SELECT COUNT(*) FROM claims
            WHERE subject_key='achievement:straight_to_the_point'
              AND predicate IN ('field_day_overlap', 'monster_counter_overlap',
                                'counter_persistence')"""
        ).fetchone()[0]
        self.assertEqual(unsupported_overlap, 0)

    def test_duplicate_accessory_bundle_requires_evidence_and_exact_quantity(self):
        question = self.questions["duplicate_accessory_power"]
        with tempfile.TemporaryDirectory() as temp:
            state_path = Path(temp) / "state.json"
            shutil.copy(ROOT / "player" / "ryan-save-state.json", state_path)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["story"]["checkpoint_id"] = question["checkpoint_id"]
            state_path.write_text(json.dumps(state), encoding="utf-8")
            before = _equipment_readiness(self.db, state_path)
            row = next(row for row in before["recommendations"]
                       if row["advice_id"] == "advice_cp030_aishe_double_meteorite")
            self.assertEqual(row["required_quantity"], 2)
            self.assertEqual(row["quantity_fit"], "unknown")
            self.assertEqual(row["evidence"]["tier"], "two_source")
            self.assertEqual(row["evidence"]["source_count"], 2)
            self.assertIn("exact owned quantity", row["equip_block_reason"])

            update_progress(state_path, self.db, "item-quantity",
                            ["item_meteorite_bracer", "2"])
            for slot in ("accessory_1", "accessory_2"):
                update_progress(state_path, self.db, "accessory-set",
                                ["Aishe", slot, "item_meteorite_bracer"])
            after = _equipment_readiness(self.db, state_path)
            row = next(row for row in after["recommendations"]
                       if row["advice_id"] == "advice_cp030_aishe_double_meteorite")
            self.assertEqual(row["quantity_fit"], "met")
            self.assertEqual(row["comparison_status"], "matches_recommendation")
            self.assertIsNone(row["equip_block_reason"])
            self.assertEqual(row["slot"], "accessory_1+accessory_2")

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
        question = self.questions["strongest_legal_gear_alltrades"]
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["story"]["checkpoint_id"] = question["checkpoint_id"]
        self.state.write_text(json.dumps(state), encoding="utf-8")
        report = _equipment_readiness(self.db, self.state)
        self.assertTrue(report["recommendations"])
        self.assertTrue(report["editor_supported"])
        self.assertTrue(report["non_accessory_editor_supported"])
        self.assertEqual(report["compatibility_coverage"]["verified_item_rows"], 311)
        self.assertEqual(report["compatibility_coverage"]["status"],
                         "complete_two_source_compatibility_matrix")
        self.assertEqual(len(report["mechanics"]), 6)
        analysis = report["strength_analysis"]
        self.assertEqual(analysis["overall_conclusion"],
                         "global_strongest_not_proven")
        self.assertFalse(analysis["attributed_recommendations_maximality_proven"])
        category_by_slot = {
            "weapon": "itemcat_weapons", "shield": "itemcat_shields",
            "helmet": "itemcat_head", "armour": "itemcat_armour",
            "accessory": "itemcat_accessories",
        }
        checkpoint_sequence = self.connection.execute(
            "SELECT sequence_no FROM checkpoints WHERE checkpoint_id=?",
            (question["checkpoint_id"],),
        ).fetchone()[0]
        for slot in analysis["slots"]:
            expected = {row[0] for row in self.connection.execute(
                """SELECT DISTINCT i.item_id
                FROM items i
                JOIN equipment_compatibility ec USING(item_id)
                JOIN item_acquisition_paths a USING(item_id)
                JOIN checkpoints start
                  ON start.checkpoint_id=a.available_from_checkpoint_id
                LEFT JOIN checkpoints expiry
                  ON expiry.checkpoint_id=a.unavailable_after_checkpoint_id
                WHERE i.category_id=? AND ec.character_name=? AND ec.can_equip=1
                  AND start.sequence_no<=?
                  AND (expiry.sequence_no IS NULL OR expiry.sequence_no>=?)""",
                (category_by_slot[slot["slot"]], slot["character"],
                 checkpoint_sequence, checkpoint_sequence),
            )}
            actual = {row["item_id"] for row in slot["candidate_universe"]}
            self.assertEqual(actual, expected, (slot["character"], slot["slot"]))
            self.assertEqual(slot["candidate_count"], len(expected))
            if slot["dimension_leaders"]:
                self.assertTrue(slot["dimension_coverage_complete"])
                self.assertEqual(slot["profiled_candidate_count"],
                                 slot["candidate_count"])
            else:
                self.assertEqual(slot["conclusion_status"],
                                 "insufficient_complete_profiles")
        self.assertTrue(any(slot["candidate_count"] >
                            slot["profiled_candidate_count"]
                            for slot in analysis["slots"]))
        self.assertNotIn("weighted", json.dumps(analysis).casefold())
        self.assertNotIn("score", json.dumps(analysis).casefold())
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

    def test_all_heart_gates_match_cli_and_api_with_route_provenance(self):
        parity_state = Path(self.temp.name) / "heart-parity-state.json"
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["story"]["checkpoint_id"] = "cp_020_buccanham"
        parity_state.write_text(json.dumps(state), encoding="utf-8")
        cli_rows = {row["heart_id"]: row for row in load_heart_report(
            self.db, checkpoint_id="cp_020_buccanham", state_path=parity_state
        )["hearts"]}
        api_rows = {row["heart_id"]: row for row in _monster_hearts(
            self.db, {}, parity_state
        )["hearts"]}
        self.assertEqual(set(cli_rows), set(api_rows))
        for heart_id, cli_row in cli_rows.items():
            with self.subTest(heart_id=heart_id):
                api_row = api_rows[heart_id]
                for key in ("available_from_checkpoint_id", "available_checkpoint",
                            "availability_status", "available_now",
                            "dlc_ownership_status"):
                    self.assertEqual(cli_row[key], api_row[key])
                if api_row["availability_status"] == "route_normalized":
                    self.assertTrue(api_row["availability_source_url"].startswith("https://"))
                    self.assertTrue(api_row["availability_locator"])
                    self.assertIn("Earliest normalized item route:",
                                  api_row["availability_notes"])

    def test_conflict_bundle_exposes_both_precisely_cited_claims(self):
        conflicts = load_conflicts(self.db, include_resolved=True)
        self.assertTrue(conflicts)
        for row in conflicts:
            self.assertIn(row["status"], {"resolved", "unresolved"})
            for side in ("a", "b"):
                self.assert_current_version_source(row[f"source_id_{side}"],
                                                   row[f"locator_{side}"])
                self.assertTrue(row[f"value_{side}"])


if __name__ == "__main__":
    unittest.main()
