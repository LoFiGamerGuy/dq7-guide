import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RainiacHybrisEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = json.loads((ROOT / "data/seed/seed_data.json").read_text(encoding="utf-8"))
        cls.sources = {
            row["source_id"]: row
            for row in json.loads((ROOT / "data/seed/sources.json").read_text(encoding="utf-8"))
        }
        cls.claims = {row["id"]: row for row in cls.seed["claims"]}
        cls.advice = {row["advice_id"]: row for row in cls.seed["checkpoint_advice"]}

    def test_verified_cores_have_two_publishers(self):
        for advice_id in ("advice_cp015_rainiac", "advice_cp016_hybris"):
            row = self.advice[advice_id]
            linked = [self.claims[claim_id] for claim_id in row["applicability"]["evidence_claim_ids"]]
            publishers = {self.sources[claim["source_id"]]["publisher"] for claim in linked}
            self.assertGreaterEqual(len(publishers), 2)
            self.assertTrue(all(claim["confidence"] == "verified" for claim in linked))

    def test_exact_extras_remain_single_source(self):
        for claim_id in (
            "claim_rainiac_buff_elements_game8",
            "claim_rainiac_control_gamewith",
            "claim_hybris_buffs_game8",
            "claim_hybris_elemental_mitigation_gamewith",
        ):
            self.assertIn("single_independent_source", self.claims[claim_id]["verification_status"])
        for advice_id in ("advice_cp015_rainiac", "advice_cp016_hybris"):
            row = self.advice[advice_id]
            self.assertIn("no_level_weakness_claim", row["verification_status"])

    def test_early_vocation_advice_has_two_source_gates(self):
        for advice_id in (
            "advice_cp009_vocations_prerequisite_progress",
            "advice_cp012_activate_moonlighting",
        ):
            row = self.advice[advice_id]
            linked = [self.claims[claim_id] for claim_id in row["applicability"]["evidence_claim_ids"]]
            publishers = {self.sources[claim["source_id"]]["publisher"] for claim in linked}
            self.assertGreaterEqual(len(publishers), 2)
            self.assertTrue(all(claim["confidence"] == "verified" for claim in linked))
        moonlighting = self.advice["advice_cp012_activate_moonlighting"]["applicability"]
        self.assertEqual(moonlighting["trigger_location"], "Shrine of Mysteries")
        self.assertEqual(moonlighting["activation_location"], "Alltrades Abbey")


if __name__ == "__main__":
    unittest.main()
