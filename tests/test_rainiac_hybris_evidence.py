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

    def test_early_gear_advice_links_verified_item_facts(self):
        for advice_id in ("advice_cp009_maribel_practical_gear", "advice_cp009_snooze_stick_sealed_use", "advice_cp010_steel_helmet_panel"):
            row = self.advice[advice_id]
            linked = [self.claims[claim_id] for claim_id in row["applicability"]["evidence_claim_ids"]]
            self.assertGreaterEqual(len({self.sources[claim["source_id"]]["publisher"] for claim in linked}), 2)
            self.assertTrue(all(claim["claim_kind"] == "fact" and claim["confidence"] == "verified" for claim in linked))
        self.assertFalse(self.advice["advice_cp009_maribel_practical_gear"]["applicability"]["full_build_available"])
        self.assertIn("conditional", self.advice["advice_cp010_steel_helmet_panel"]["verification_status"])

    def test_magic_shield_phone_row_uses_verified_equipped_effects(self):
        row = self.advice["advice_cp008_magic_shield_spike"]
        linked = [self.claims[claim_id] for claim_id in row["applicability"]["evidence_claim_ids"]]
        self.assertGreaterEqual(len({self.sources[claim["source_id"]]["publisher"] for claim in linked}), 4)
        self.assertTrue(all(claim["confidence"] == "verified" for claim in linked))
        self.assertIn("5% less elemental damage", row["advice_text"])
        self.assertNotIn("use it in battle", row["advice_text"].lower())
        self.assertIn("no_battle_use_claim", row["verification_status"])


if __name__ == "__main__":
    unittest.main()
