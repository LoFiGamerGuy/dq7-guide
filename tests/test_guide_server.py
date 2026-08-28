from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from guide_server import create_server


class GuideServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.state = Path(cls.temp.name) / "state.json"
        shutil.copy(ROOT / "player" / "ryan-save-state.json", cls.state)
        cls.server = create_server(
            "127.0.0.1", 0, ROOT / "data" / "dq7_reimagined.sqlite",
            cls.state, ROOT / "web",
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp.cleanup()

    def get_json(self, path):
        with urlopen(self.base + path) as response:
            return response.status, json.load(response)

    def patch_json(self, path, payload):
        request = Request(self.base + path, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="PATCH")
        with urlopen(request) as response:
            return response.status, json.load(response)

    def test_health_checkpoints_dashboard_and_static_assets(self):
        self.assertEqual(self.get_json("/api/health"), (200, {"status": "ok"}))
        status, checkpoints = self.get_json("/api/checkpoints")
        self.assertEqual(status, 200)
        self.assertEqual(checkpoints[0]["id"], "cp_001_prologue")
        status, dashboard = self.get_json("/api/dashboard")
        self.assertEqual(status, 200)
        self.assertIn("progress", dashboard)
        with urlopen(self.base + "/") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"Run Guide", response.read())

    def test_checkpoint_and_domain_endpoints(self):
        _, checkpoint = self.get_json("/api/checkpoints/cp_001_prologue")
        self.assertEqual(checkpoint["id"], "cp_001_prologue")
        self.assertIn("actions", checkpoint)
        _, ballymolloy = self.get_json("/api/checkpoints/cp_003_ballymolloy")
        slime = next(row for row in ballymolloy["monsters"] if row["id"] == "monster_002")
        self.assertEqual(slime["drop"], "Medicinal Herb")
        self.assertTrue(any(source["id"] == "game8_monster_slime"
                            for source in ballymolloy["sources"]))
        _, progress = self.get_json("/api/progress")
        self.assertIn("achievements", progress)
        _, hoarder = self.get_json("/api/hoarder?gaps=1")
        self.assertEqual(hoarder["total"], 353)
        _, monsters = self.get_json("/api/monsters/coverage")
        self.assertEqual(monsters["total"], 333)
        _, medals = self.get_json("/api/medals")
        self.assertEqual(medals["total"], 100)
        _, tablets = self.get_json("/api/tablets")
        self.assertEqual(tablets["tablet_count"], 20)
        _, vocations = self.get_json("/api/vocations")
        self.assertEqual(len(vocations["vocations"]), 26)
        _, vocation = self.get_json("/api/vocations/vocation_warrior")
        self.assertEqual(vocation["vocation"]["name"], "Warrior")
        self.assertTrue(vocation["skills"])
        self.assertIn("source_url", vocation["skills"][0])
        self.assertIn("locator", vocation["skills"][0])
        _, items = self.get_json("/api/items")
        item_id = items["items"][0]["item_id"]
        _, item = self.get_json("/api/items/" + item_id)
        self.assertEqual(item["item"]["item_id"], item_id)
        if item["routes"]:
            self.assertIn("source_url", item["routes"][0])
            self.assertIn("locator", item["routes"][0])
        _, monster = self.get_json("/api/monsters/monster_001")
        self.assertEqual(monster["monster"]["monster_id"], "monster_001")
        self.assertIn("encounters", monster)
        self.assertIn("drops", monster)

    def test_progress_post_reuses_validated_mutation_and_rejects_unknown_command(self):
        body = json.dumps({"command": "checkpoint", "values": ["cp_001_prologue"]}).encode()
        request = Request(self.base + "/api/progress", data=body,
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request) as response:
            payload = json.load(response)
        self.assertIn("Checkpoint set", payload["message"])
        saved = json.loads(self.state.read_text())
        self.assertEqual(saved["story"]["checkpoint_id"], "cp_001_prologue")

        bad = Request(self.base + "/api/progress",
                      data=json.dumps({"command": "raw-write", "values": ["x"]}).encode(),
                      headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(HTTPError) as caught:
            urlopen(bad)
        self.assertEqual(caught.exception.code, 400)

    def test_browser_contract_patch_records_and_reopens_one_action(self):
        _, checkpoint = self.get_json("/api/checkpoints/cp_001_prologue")
        action = checkpoint["actions"][0]
        for completed in (True, False):
            request = Request(
                self.base + "/api/progress",
                data=json.dumps({"kind": "action", "id": action["id"],
                                 "completed": completed}).encode(),
                headers={"Content-Type": "application/json"}, method="PATCH",
            )
            with urlopen(request) as response:
                self.assertEqual(response.status, 200)
        saved = json.loads(self.state.read_text())
        self.assertNotIn(action["id"], saved["completion"]["obligations_completed"])

    def test_state_aware_search_pagination_and_resource_patch_mappings(self):
        _, items = self.get_json("/api/items?q=shield&limit=2&offset=0")
        self.assertLessEqual(len(items["items"]), 2)
        self.assertTrue(all("obtained" in row for row in items["items"]))
        item_id = items["items"][0]["item_id"]
        for completed in (True, False):
            self.assertEqual(self.patch_json("/api/items/" + item_id,
                                             {"completed": completed})[0], 200)

        _, tablets = self.get_json("/api/tablets")
        fragment_id = tablets["fragments"][0]["fragment_id"]
        for completed in (True, False):
            self.patch_json("/api/tablets/" + fragment_id, {"completed": completed})

        _, achievements = self.get_json("/api/achievements?limit=1")
        achievement_id = achievements["achievements"][0]["achievement_id"]
        self.assertIn("unlocked", achievements["achievements"][0])
        for completed in (True, False):
            self.patch_json("/api/achievements/" + achievement_id,
                            {"completed": completed})

        _, vocations = self.get_json("/api/vocations?q=Warrior&limit=1")
        vocation_id = vocations["vocations"][0]["vocation_id"]
        self.assertIn("mastered_by", vocations["vocations"][0])
        for completed in (True, False):
            self.patch_json("/api/vocations/" + vocation_id,
                            {"character": "Hero", "completed": completed})

        self.patch_json("/api/checkpoints/cp_002_estard_shrine", {"selected": True})
        saved = json.loads(self.state.read_text())
        self.assertEqual(saved["story"]["checkpoint_id"], "cp_002_estard_shrine")
        self.assertNotIn(item_id, saved["completion"]["items_obtained"])
        self.assertNotIn(fragment_id, saved["completion"]["tablet_fragments"])
        self.assertNotIn(achievement_id, saved["completion"]["achievements_unlocked"])


if __name__ == "__main__":
    unittest.main()
