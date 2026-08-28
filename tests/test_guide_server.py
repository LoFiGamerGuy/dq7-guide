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
            page = response.read()
            self.assertIn(b"Run Guide", page)
            self.assertLess(page.index(b'id="checkpointStop"'), page.index(b'id="advice"'))
            self.assertLess(page.index(b'id="advice"'), page.index(b'id="safeCondition"'))

    def test_checkpoint_and_domain_endpoints(self):
        _, checkpoint = self.get_json("/api/checkpoints/cp_001_prologue")
        self.assertEqual(checkpoint["id"], "cp_001_prologue")
        self.assertIn("actions", checkpoint)
        _, ballymolloy = self.get_json("/api/checkpoints/cp_003_ballymolloy")
        slime = next(row for row in ballymolloy["monsters"] if row["id"] == "monster_002")
        self.assertEqual(slime["drop"], "Medicinal Herb")
        self.assertTrue(any(source["id"] == "game8_monster_slime"
                            for source in ballymolloy["sources"]))
        _, alltrades = self.get_json("/api/checkpoints/cp_009_alltrades")
        groups = {row["decision_group"] for row in alltrades["advice"]}
        self.assertEqual(groups, {"completion_safe", "strongest_now", "optional_grind"})
        self.assertTrue(all(row["goal"] in ("completion_safe", "immediate_power", "both")
                            for row in alltrades["advice"]))
        _, alltrades_present = self.get_json("/api/checkpoints/cp_010_alltrades_present")
        panel = next(row for row in alltrades_present["advice"]
                     if row["id"] == "advice_cp010_steel_helmet_panel")
        self.assertIn("gate", panel["applicability"])
        self.assertEqual(panel["tradeoff"], panel["applicability"]["tradeoff"])
        self.assertTrue(panel["source"]["url"])
        self.assertTrue(panel["source"]["locator"])
        self.assertEqual(panel["verification_status"], "source_checked")
        _, conflicts = self.get_json("/api/conflicts")
        self.assertGreater(len(conflicts), 0)
        self.assertEqual(conflicts[0]["status"], "unresolved")
        self.assertEqual(len(conflicts[0]["claims"]), 2)
        for claim in conflicts[0]["claims"]:
            self.assertIn("scope", claim)
            self.assertIn("locator", claim)
            self.assertTrue(claim["source"]["url"])
            self.assertIn("retrieved_at", claim["source"])
        _, sources = self.get_json("/api/sources?q=walkthrough&publisher=Game8&limit=2")
        self.assertGreater(sources["total"], 0)
        self.assertLessEqual(len(sources["sources"]), 2)
        self.assertIn("Game8", sources["publishers"])
        source_id = sources["sources"][0]["source_id"]
        _, source = self.get_json("/api/sources/" + source_id)
        self.assertEqual(source["source_id"], source_id)
        self.assertIn(source["retrieval_band"], ("within_180_days", "over_180_days", "unknown"))
        self.assertIn(source["update_date_status"], ("known", "unknown"))
        self.assertTrue(source["url"])
        _, boss_sources = self.get_json("/api/sources?role=boss_strategy&limit=200")
        self.assertGreater(boss_sources["total"], 0)
        self.assertTrue(all(row["role"] == "boss_strategy" for row in boss_sources["sources"]))
        band = source["retrieval_band"]
        _, dated_sources = self.get_json("/api/sources?retrieval_band=" + band + "&limit=200")
        self.assertTrue(all(row["retrieval_band"] == band for row in dated_sources["sources"]))
        _, seeds = self.get_json("/api/seeds?variant=super&limit=20")
        self.assertEqual(seeds["total"], 9)
        self.assertTrue(all(row["variant"] == "super" for row in seeds["seeds"]))
        seed_id = seeds["seeds"][0]["seed_id"]
        _, seed = self.get_json("/api/seeds/" + seed_id)
        self.assertEqual(seed["seed_id"], seed_id)
        self.assertGreater(seed["increase_amount"], 0)
        self.assertTrue(seed["locator"])
        _, rewards = self.get_json("/api/seeds?variant=reward")
        self.assertEqual(rewards["total"], 1)
        reward = rewards["seeds"][0]
        self.assertEqual(reward["eligible_pool_status"], "unknown")
        self.assertIsNone(reward["eligible_items"])
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
        moon = vocation["moonlighting"]
        self.assertEqual(moon["unlock"]["value"]["earliest_checkpoint_id"], "cp_012_roamer_return")
        self.assertEqual(moon["venue_status"], "conflicting_sources")
        self.assertEqual(len(moon["unlock_claims"]), 2)
        self.assertIn("Exact proficiency-point split per battle",
                      moon["mechanics"]["value"]["unknown_restrictions"])
        _, moon_endpoint = self.get_json("/api/moonlighting")
        self.assertEqual(moon_endpoint["mechanics"]["value"]["simultaneous_vocations"], 2)
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
        _, hearts = self.get_json("/api/monster-hearts?q=critical&limit=2")
        self.assertGreater(hearts["total"], 0)
        self.assertLessEqual(len(hearts["hearts"]), 2)
        heart_id = hearts["hearts"][0]["heart_id"]
        _, heart = self.get_json("/api/monster-hearts/" + heart_id)
        self.assertEqual(heart["heart_id"], heart_id)
        self.assertTrue(heart["effect_text"])
        self.assertTrue(heart["source_url"])
        self.assertTrue(heart["locator"])
        _, slime_heart = self.get_json("/api/monster-hearts/heart_slime")
        self.assertEqual(slime_heart["available_from_checkpoint_id"], "cp_003_ballymolloy")
        self.assertEqual(slime_heart["availability_status"], "route_normalized")
        self.assertTrue(slime_heart["routes"])
        self.assertTrue(slime_heart["routes"][0]["locator"])
        _, hammerhood_heart = self.get_json("/api/monster-hearts/heart_hammerhood")
        drop = next(route for route in hammerhood_heart["routes"] if route["method"] == "drop")
        self.assertEqual(drop["drop_rate_status"], "unknown")
        self.assertIsNone(drop["drop_rate"])
        self.assertEqual(drop["dlc_scope_status"], "unknown")
        _, missables = self.get_json("/api/missables?q=window&limit=3")
        self.assertGreater(missables["total"], 0)
        missable_id = missables["missables"][0]["missable_id"]
        _, missable = self.get_json("/api/missables/" + missable_id)
        self.assertIn(missable["window_status"], ("verified", "unresolved"))
        self.assertTrue(missable["source_url"])
        if missable["window_status"] == "unresolved":
            self.assertTrue(missable["provenance_gap"])
        _, farms = self.get_json("/api/farms?q=metal&limit=2")
        self.assertGreater(farms["total"], 0)
        self.assertLessEqual(len(farms["farms"]), 2)
        farm_id = farms["farms"][0]["farming_id"]
        _, farm = self.get_json("/api/farms/" + farm_id)
        self.assertEqual(farm["farming_id"], farm_id)
        self.assertEqual(farm["rate_status"], "numeric_unpublished")
        self.assertEqual(farm["strategy_kind"], "attributed_strategy")
        self.assertTrue(farm["source_url"])
        self.assertTrue(farm["locator"])
        _, proficiency_farms = self.get_json("/api/farms?q=vocational%20proficiency")
        self.assertEqual(proficiency_farms["total"], 1)
        proficiency_farm = proficiency_farms["farms"][0]
        self.assertEqual(proficiency_farm["farm_type"], "proficiency")
        self.assertEqual(proficiency_farm["available_from_checkpoint_id"], "cp_013_flying_carpet")
        self.assertEqual(proficiency_farm["rate_status"], "numeric_unpublished")
        self.assertTrue(proficiency_farm["strategy_source_url"])
        _, gold_farms = self.get_json("/api/farms?q=gold%20via%20lucky%20panel")
        self.assertEqual(gold_farms["total"], 1)
        gold_farm = gold_farms["farms"][0]
        self.assertEqual(gold_farm["farm_type"], "gold")
        self.assertEqual(gold_farm["available_from_checkpoint_id"], "cp_009_alltrades")
        self.assertEqual(gold_farm["rate_status"], "numeric_unpublished")
        self.assertEqual(gold_farm["source_id"], "rpgsite_lucky_panel")
        self.assertEqual(gold_farm["strategy_source_id"], "game8_gold_farming")
        self.assertFalse(farm["provenance_gap"])
        self.assertTrue(farm["available_from_checkpoint_id"])
        self.assertTrue(farm["encounter_rate_text"])
        self.assertTrue(farm["strategy_source_url"])
        self.assertTrue(farm["strategy_locator"])

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
        status, dashboard = self.get_json("/api/dashboard")
        self.assertEqual(status, 200)
        self.assertTrue(dashboard["checkpoint"]["is_saved"])
        self.assertEqual(dashboard["checkpoint"]["name"], "Estard Castle and Shrine of Mysteries")
        for command, values in (("medal-count", [7]),
                                ("vocation-mastered", ["Hero", vocation_id]),
                                ("party-level", ["Hero", 17]),
                                ("party-vocations", ["Hero", "vocation_warrior", "vocation_priest"])):
            request = Request(self.base + "/api/progress",
                              data=json.dumps({"command": command, "values": values}).encode(),
                              headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request) as response:
                self.assertEqual(response.status, 200)
        _, progress = self.get_json("/api/progress")
        self.assertEqual(progress["saved_checkpoint"], "cp_002_estard_shrine")
        self.assertEqual(progress["mini_medal_count"], 7)
        hero = next(member for member in progress["party"] if member["name"] == "Hero")
        self.assertIn(vocation_id, hero["mastered_vocations"])
        self.assertEqual((hero["level"], hero["primary_vocation"], hero["secondary_vocation"]),
                         (17, "vocation_warrior", "vocation_priest"))
        _, cp007 = self.get_json("/api/checkpoints/cp_007_frobisher")
        medal_advice = next(row for row in cp007["advice"]
                            if row["id"] == "advice_cp007_windcheater_spike")
        self.assertEqual(medal_advice["saved_state_applicability"]["status"], "unmet")
        self.assertIn("7/15", medal_advice["saved_state_applicability"]["reason"])
        _, cp010 = self.get_json("/api/checkpoints/cp_010_alltrades_present")
        priest_advice = next(row for row in cp010["advice"]
                             if row["id"] == "advice_cp010_priest_emergency_role")
        self.assertEqual(priest_advice["saved_state_applicability"]["status"], "satisfied")
        self.assertIn("Hero current", priest_advice["saved_state_applicability"]["reason"])
        ungated = next(row for row in cp010["advice"]
                       if row["id"] == "advice_cp010_steel_helmet_panel")
        self.assertEqual(ungated["saved_state_applicability"]["status"], "unknown")
        self.patch_json("/api/vocations/" + vocation_id,
                        {"character": "Hero", "completed": False})
        saved = json.loads(self.state.read_text())
        self.assertEqual(saved["story"]["checkpoint_id"], "cp_002_estard_shrine")
        self.assertNotIn(item_id, saved["completion"]["items_obtained"])
        self.assertNotIn(fragment_id, saved["completion"]["tablet_fragments"])
        self.assertNotIn(achievement_id, saved["completion"]["achievements_unlocked"])


if __name__ == "__main__":
    unittest.main()
