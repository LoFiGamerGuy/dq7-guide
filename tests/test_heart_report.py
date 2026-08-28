from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from heart_report import load_heart_report


class HeartReportTests(unittest.TestCase):
    def test_checkpoint_report_separates_verified_and_unknown_availability(self):
        report = load_heart_report(
            ROOT / "data" / "dq7_reimagined.sqlite",
            checkpoint_id="cp_003_ballymolloy",
        )
        self.assertGreaterEqual(len(report["hearts"]), 12)
        self.assertGreaterEqual(report["verified_available"], 1)
        self.assertGreater(report["unknown_availability"], 0)
        golem = next(row for row in report["hearts"] if row["heart_id"] == "heart_golem")
        self.assertIs(golem["available_now"], True)
        self.assertTrue(golem["source_url"].startswith("https://"))
        self.assertTrue(golem["locator"])

    def test_lookup_rejects_unknown_instead_of_returning_empty(self):
        with self.assertRaisesRegex(ValueError, "Unknown Monster Heart"):
            load_heart_report(ROOT / "data" / "dq7_reimagined.sqlite", "invented heart")


if __name__ == "__main__":
    unittest.main()
