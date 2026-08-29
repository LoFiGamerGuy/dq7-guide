from __future__ import annotations

from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from heart_report import load_heart_report, print_heart_report


class HeartReportTests(unittest.TestCase):
    def test_checkpoint_report_separates_verified_and_unknown_availability(self):
        report = load_heart_report(
            ROOT / "data" / "dq7_reimagined.sqlite",
            checkpoint_id="cp_003_ballymolloy",
        )
        self.assertGreaterEqual(len(report["hearts"]), 12)
        self.assertGreaterEqual(report["verified_available"], 1)
        self.assertEqual(report["unknown_availability"], 5)
        golem = next(row for row in report["hearts"] if row["heart_id"] == "heart_golem")
        self.assertIs(golem["available_now"], True)
        self.assertTrue(golem["source_url"].startswith("https://"))
        self.assertTrue(golem["locator"])
        healslime = next(row for row in report["hearts"]
                         if row["heart_id"] == "heart_healslime")
        self.assertIs(healslime["available_now"], False)
        self.assertEqual(healslime["available_from_checkpoint_id"], "cp_005_larca")
        self.assertEqual(healslime["availability_status"], "route_normalized")
        self.assertIn("Grotta del Sigillo 2F", healslime["availability_notes"])
        self.assertTrue(healslime["availability_source_url"].startswith("https://"))

    def test_lookup_rejects_unknown_instead_of_returning_empty(self):
        with self.assertRaisesRegex(ValueError, "Unknown Monster Heart"):
            load_heart_report(ROOT / "data" / "dq7_reimagined.sqlite", "invented heart")

    def test_unscoped_cli_prints_known_route_gate_without_claiming_current_access(self):
        report = load_heart_report(
            ROOT / "data" / "dq7_reimagined.sqlite", "Grody Gumpdrops Heart"
        )
        output = StringIO()
        with redirect_stdout(output):
            print_heart_report(report, include_sources=True)
        rendered = output.getvalue()
        self.assertIn("route established from Silver Fragment and Another World", rendered)
        self.assertNotIn("availability not yet established", rendered)
        self.assertIn("Earliest normalized item route: Defeat Grody Gumpdrops", rendered)
        self.assertIn("Availability:", rendered)

    def test_troll_heart_exposes_checkpoint_and_distinct_route_provenance(self):
        report = load_heart_report(
            ROOT / "data" / "dq7_reimagined.sqlite", "Troll Heart",
            checkpoint_id="cp_019_aeolus",
        )
        troll = report["hearts"][0]
        self.assertIs(troll["available_now"], True)
        self.assertEqual(troll["available_from_checkpoint_id"], "cp_019_aeolus")
        self.assertIn("field sparkle", troll["availability_notes"])
        self.assertIn("second copy", troll["availability_notes"])
        self.assertEqual(troll["availability_source_title"],
                         "Troll Heart Acquisition and Performance")
        self.assertTrue(troll["availability_source_url"].startswith("https://"))
        self.assertIn("lines 60-67", troll["availability_locator"])
        self.assertEqual(troll["availability_status"], "heart_gate")

    def test_dlc_hearts_require_entitlement_in_cli_report(self):
        db = ROOT / "data" / "dq7_reimagined.sqlite"
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
            state_path.write_text(json.dumps(state), encoding="utf-8")
            row = load_heart_report(
                db, "heart_metal_slime", "cp_003_ballymolloy", state_path
            )["hearts"][0]
            self.assertIsNone(row["available_now"])
            self.assertEqual(row["availability_status"],
                             "requires_dlc_ownership_confirmation")

            state["dlc_entitlements"] = {"Jam-Packed Swag Bag": True}
            state_path.write_text(json.dumps(state), encoding="utf-8")
            row = load_heart_report(
                db, "heart_metal_slime", "cp_003_ballymolloy", state_path
            )["hearts"][0]
            self.assertTrue(row["available_now"])

            state["dlc_entitlements"]["Jam-Packed Swag Bag"] = False
            state_path.write_text(json.dumps(state), encoding="utf-8")
            row = load_heart_report(
                db, "heart_metal_slime", "cp_003_ballymolloy", state_path
            )["hearts"][0]
            self.assertFalse(row["available_now"])
            self.assertEqual(row["dlc_ownership_status"], "not_owned")


if __name__ == "__main__":
    unittest.main()
