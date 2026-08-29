from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from guide_server import create_server  # noqa: E402


class FirstUseEarlyGameE2ETests(unittest.TestCase):
    """Exercise the first-use and early-game workflow over the real HTTP API."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name) / "state.json"
        shutil.copy(ROOT / "player" / "ryan-save-state.json", self.state)
        self.server = create_server(
            "127.0.0.1", 0, ROOT / "data" / "dq7_reimagined.sqlite",
            self.state, ROOT / "web",
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def get(self, path):
        with urlopen(self.base + path) as response:
            return json.load(response)

    def patch(self, path, payload):
        request = Request(self.base + path, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="PATCH")
        with urlopen(request) as response:
            self.assertEqual(response.status, 200)

    def test_first_ten_hours_guidance_and_every_early_ledger_roll_back(self):
        dashboard = self.get("/api/dashboard")
        self.assertEqual(dashboard["checkpoint"]["id"], "cp_001_prologue")
        self.assertFalse(dashboard["checkpoint"]["is_saved"])
        prologue = self.get("/api/checkpoints/cp_001_prologue")
        self.assertTrue(prologue["stop_actions"])
        self.assertTrue(all(row["source"]["locator"] for row in prologue["stop_actions"]))

        self.patch("/api/checkpoints/cp_003_ballymolloy", {"selected": True})
        checkpoint = self.get("/api/checkpoints/cp_003_ballymolloy")
        self.assertTrue(checkpoint["actions"])
        self.assertTrue(checkpoint["medals"])
        self.assertTrue(checkpoint["tablet_fragments"])
        self.assertTrue(checkpoint["checkpoint_items"])
        self.assertTrue(checkpoint["monsters"])

        action = checkpoint["actions"][0]["id"]
        medal = next(row["number"] for row in checkpoint["medals"]
                     if row["timing"] != "later")
        tablet = checkpoint["tablet_fragments"][0]["id"]
        item = checkpoint["checkpoint_items"][0]["id"]
        monster = checkpoint["monsters"][0]["id"]
        mutations = [
            ("/api/progress", {"kind": "action", "id": action}),
            ("/api/progress", {"kind": "medal", "id": medal}),
            (f"/api/tablets/{tablet}", {}),
            (f"/api/items/{item}", {}),
            ("/api/progress", {"kind": "monster", "id": monster}),
            ("/api/monster-hearts/heart_slime", {}),
            ("/api/vocations/vocation_warrior", {"character": "Hero"}),
        ]
        for path, payload in mutations:
            self.patch(path, {**payload, "completed": True})

        saved = json.loads(self.state.read_text(encoding="utf-8"))
        completion = saved["completion"]
        self.assertIn(action, completion["obligations_completed"])
        self.assertIn(medal, completion["mini_medals_found"])
        self.assertIn(tablet, completion["tablet_fragments"])
        self.assertIn(item, completion["items_obtained"])
        self.assertIn(monster, completion["monster_entries"])
        self.assertIn("heart_slime", completion["monster_hearts_owned"])
        self.assertTrue(saved["party"]["members"]["Hero"]["vocation_mastery"]
                        ["vocation_warrior"])

        heart = self.get("/api/monster-hearts/heart_slime")
        vocation = self.get("/api/vocations/vocation_warrior")
        self.assertTrue(heart["owned"])
        self.assertEqual(heart["available_from_checkpoint_id"], "cp_003_ballymolloy")
        self.assertEqual(vocation["unlock_progress"]["cost_status"], "verified")

        farms = self.get("/api/farms?through_checkpoint=cp_009_alltrades")
        self.assertTrue(farms["farms"])
        self.assertTrue(all(row["availability_status"] == "available_by_checkpoint"
                            for row in farms["farms"]))

        for path, payload in reversed(mutations):
            self.patch(path, {**payload, "completed": False})
        rolled_back = json.loads(self.state.read_text(encoding="utf-8"))
        completion = rolled_back["completion"]
        self.assertNotIn(action, completion["obligations_completed"])
        self.assertNotIn(medal, completion["mini_medals_found"])
        self.assertNotIn(tablet, completion["tablet_fragments"])
        self.assertNotIn(item, completion["items_obtained"])
        self.assertNotIn(monster, completion["monster_entries"])
        self.assertNotIn("heart_slime", completion["monster_hearts_owned"])
        self.assertNotIn("vocation_warrior",
                         rolled_back["party"]["members"]["Hero"]["vocation_mastery"])


if __name__ == "__main__":
    unittest.main()
