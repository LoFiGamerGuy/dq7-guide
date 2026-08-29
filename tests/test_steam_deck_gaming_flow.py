import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SteamDeckGamingFlowContractTests(unittest.TestCase):
    def test_wrapper_is_foreground_repo_contained_and_executable(self):
        wrapper = ROOT / "steam-deck" / "run-dq7-guide-gaming-mode.sh"
        manager = (ROOT / "manage-steam-deck-guide.sh").read_text(encoding="utf-8")
        text = wrapper.read_text(encoding="utf-8")
        self.assertTrue(os.access(wrapper, os.X_OK))
        self.assertIn('exec "$repo_dir/manage-steam-deck-guide.sh" foreground', text)
        self.assertIn('foreground_server()', manager)
        self.assertIn('--pairing-file "$pairing_file"', manager)
        self.assertIn('--state "$state_file"', manager)
        foreground = manager[manager.index("foreground_server()"):manager.index("command_name=")]
        self.assertNotIn("--open-browser", foreground)

    def test_docs_preserve_pair_launch_switch_stop_and_recovery_order(self):
        guide = (ROOT / "docs" / "STEAM_DECK_GAMING_MODE.md").read_text(encoding="utf-8")
        ordered = [
            "manage-steam-deck-guide.sh start",
            "bookmark it",
            "run-dq7-guide-gaming-mode.sh",
            "launch **DQ7 Phone Guide**",
            "Launch Dragon Quest VII",
            "Open the saved guide bookmark",
            "**Stop**",
        ]
        positions = [guide.index(fragment) for fragment in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("No root service, login item, or autostart", guide)
        self.assertIn("cannot\nguarantee", guide)
        self.assertIn("**Backup:** Dashboard, Phone Setup, and Progress", guide)
        self.assertIn("**Restore:** Progress requires", guide)
        self.assertIn("timestamped copy", guide)


if __name__ == "__main__":
    unittest.main()
