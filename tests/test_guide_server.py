from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from guide_server import (_access_urls, _checkpoint_view, _equipment_readiness, _evidence_gaps,
                          _load_or_create_pairing_token, _progress,
                          _vocation_unlock_progress, create_server, make_handler)


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

    def post_json(self, path, payload):
        request = Request(self.base + path, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request) as response:
            return response.status, json.load(response)

    def test_equipment_readiness_refuses_unvalidated_editor_and_compares_advice(self):
        state_path = Path(self.temp.name) / "equipment-state.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["story"]["checkpoint_id"] = "cp_009_alltrades"
        state["party"]["members"]["Hero"]["equipment"] = {
            "weapon": "item_cautery_sword"
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")
        report = _equipment_readiness(ROOT / "data" / "dq7_reimagined.sqlite",
                                      state_path)
        self.assertFalse(report["editor_supported"])
        self.assertTrue(any("two-source-agreeing" in gap for gap in report["gaps"]))
        self.assertEqual(len(report["mechanics"]), 2)
        accessory = next(row for row in report["mechanics"]
                         if row["rule_type"] == "slot_count")
        self.assertEqual(accessory["numeric_value"], 2)
        self.assertEqual(accessory["confidence"], "verified")
        coverage = report["compatibility_coverage"]
        self.assertEqual(coverage["status"], "partial_two_source_matrix")
        self.assertEqual(coverage["catalog_item_rows"], 311)
        self.assertEqual(coverage["audited_item_rows"], 311)
        self.assertEqual(coverage["verified_item_rows"], 306)
        self.assertEqual(coverage["conflicted_item_rows"], 3)
        self.assertEqual(coverage["single_source_item_rows"], 2)
        self.assertEqual(coverage["unaudited_item_rows"], 0)
        accessories = next(row for row in coverage["by_category"]
                           if row["category"] == "Accessories")
        self.assertEqual(accessories["catalog_item_rows"], 74)
        self.assertEqual(accessories["verified_item_rows"], 74)
        self.assertEqual(accessories["conflicted_item_rows"], 0)
        self.assertEqual(accessories["unaudited_item_rows"], 0)
        cautery = next(row for row in report["recommendations"]
                       if row["item_name"] == "Cautery Sword")
        self.assertEqual(cautery["character"], "Hero")
        self.assertEqual(cautery["slot"], "weapon")
        self.assertEqual(cautery["comparison_status"], "matches_recommendation")
        self.assertEqual(cautery["ownership_status"], "unknown")
        self.assertEqual(cautery["compatibility_status"], "verified_can_equip")

        status, endpoint = self.get_json("/api/equipment")
        self.assertEqual(status, 200)
        self.assertFalse(endpoint["editor_supported"])
        self.assertEqual(len(endpoint["mechanics"]), 2)

    def test_accessory_api_lists_owned_compatible_options_and_reverses(self):
        self.patch_json("/api/items/item_prayer_ring", {"completed": True})
        status, report = self.get_json("/api/equipment")
        self.assertEqual(status, 200)
        self.assertTrue(report["accessory_editor_supported"])
        hero = next(row for row in report["members"] if row["name"] == "Hero")
        self.assertIn("item_prayer_ring", {row["item_id"] for row in hero["accessory_options"]})

        self.patch_json("/api/equipment/accessories/Hero/accessory_1",
                        {"item_id": "item_prayer_ring"})
        _, report = self.get_json("/api/equipment")
        hero = next(row for row in report["members"] if row["name"] == "Hero")
        self.assertEqual(hero["accessory_slots"]["accessory_1"], "item_prayer_ring")

        self.patch_json("/api/equipment/accessories/Hero/accessory_1", {"item_id": None})
        self.patch_json("/api/items/item_prayer_ring", {"completed": False})
        _, report = self.get_json("/api/equipment")
        hero = next(row for row in report["members"] if row["name"] == "Hero")
        self.assertIsNone(hero["accessory_slots"]["accessory_1"])

    def test_health_checkpoints_dashboard_and_static_assets(self):
        launcher = (ROOT / "start-guide.bat").read_text(encoding="utf-8")
        unix_launcher = (ROOT / "start-guide.sh").read_text(encoding="utf-8")
        self.assertIn("Python 3.10 or newer is required", launcher)
        self.assertIn("sys.version_info", launcher)
        self.assertIn("The guide could not start", launcher)
        self.assertIn("python3 scripts/guide_server.py --open-browser", unix_launcher)
        self.assertIn("sys.version_info", unix_launcher)
        phone_launcher = (ROOT / "start-guide-phone.sh").read_text(encoding="utf-8")
        self.assertIn("guide_server.py --lan --open-browser", phone_launcher)
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
            self.assertIn(b'id="previousCheckpoint"', page)
            self.assertIn(b'id="nextCheckpoint"', page)
            self.assertIn(b'id="advanceCheckpointButton"', page)
            self.assertLess(page.index(b'id="checkpointStop"'), page.index(b'id="advice"'))
            self.assertLess(page.index(b'id="advice"'), page.index(b'id="safeCondition"'))
        with urlopen(self.base + "/app.js") as response:
            app = response.read()
            self.assertNotIn(b'checked disabled', app)
            self.assertNotIn(b'state.domain === "medals" && entry.completed', app)
            self.assertIn(b"Save failed. Change was not recorded.", app)
            self.assertIn(b"saveToggle(event.target", app)

    def test_phone_shell_manifest_service_worker_and_backup(self):
        with urlopen(self.base + "/manifest.webmanifest") as response:
            manifest = json.load(response)
            self.assertEqual(manifest["display"], "standalone")
            self.assertEqual(manifest["start_url"], "/#walkthrough")
            self.assertTrue(manifest["icons"])
        with urlopen(self.base + "/service-worker.js") as response:
            worker = response.read()
            self.assertEqual(response.headers["Service-Worker-Allowed"], "/")
            self.assertIn(b'request.method !== "GET"', worker)
            self.assertIn(b'/api/state-backup', worker)
            self.assertIn(b"DATA_CACHE", worker)
        with urlopen(self.base + "/api/state-backup") as response:
            backup = json.load(response)
            self.assertIn("attachment;", response.headers["Content-Disposition"])
            self.assertEqual(backup["player"], "Ryan")
        with urlopen(self.base + "/app.js") as response:
            app = response.read()
            self.assertIn(b"progress changes are not queued", app)
            self.assertIn(b'navigator.serviceWorker.register("/service-worker.js")', app)

    def test_restore_requires_confirmation_validates_and_keeps_recovery_copy(self):
        _, original = self.get_json("/api/state-backup")
        backup = json.loads(json.dumps(original))
        backup["completion"]["mini_medal_count"] = 17
        with self.assertRaises(HTTPError) as missing_confirmation:
            self.post_json("/api/state-restore", {"state": backup})
        self.assertEqual(missing_confirmation.exception.code, 400)
        status, restored = self.post_json("/api/state-restore", {
            "confirmation": "RESTORE", "state": backup,
        })
        self.assertEqual(status, 200)
        self.assertEqual(self.get_json("/api/progress")[1]["mini_medal_count"], 17)
        recovery = self.state.with_name(restored["recovery_file"])
        self.assertTrue(recovery.is_file())
        self.post_json("/api/state-restore", {
            "confirmation": "RESTORE", "state": original,
        })

    def test_network_urls_keep_normal_mode_private_and_label_phone_mode(self):
        local, phone = _access_urls("127.0.0.1", 8765)
        self.assertEqual(local, "http://127.0.0.1:8765")
        self.assertEqual(phone, [])
        local, phone = _access_urls("0.0.0.0", 8765, "launch-secret")
        self.assertEqual(local, "http://127.0.0.1:8765")
        self.assertTrue(all(url.startswith("http://") and
                            url.endswith(":8765/?pair=launch-secret")
                            for url in phone))

    def test_live_play_mutations_support_server_round_trip_undo(self):
        _, original = self.get_json("/api/state-backup")
        try:
            self.assertEqual(self.patch_json(
                "/api/items/item_pilchard_crackers", {"completed": True}
            )[0], 200)
            self.assertTrue(self.get_json(
                "/api/items/item_pilchard_crackers"
            )[1]["item"]["obtained"])
            self.assertEqual(self.patch_json(
                "/api/items/item_pilchard_crackers", {"completed": False}
            )[0], 200)
            self.assertFalse(self.get_json(
                "/api/items/item_pilchard_crackers"
            )[1]["item"]["obtained"])
        finally:
            self.post_json("/api/state-restore", {
                "confirmation": "RESTORE", "state": original,
            })

    def test_lan_pairing_rejects_unpaired_client_then_sets_session_cookie(self):
        handler = make_handler(ROOT / "data" / "dq7_reimagined.sqlite", self.state,
                               ROOT / "web", "one-launch-token")
        handler._is_loopback = lambda _self: False
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with self.assertRaises(HTTPError) as context:
                urlopen(base + "/api/health")
            self.assertEqual(context.exception.code, 401)
            self.assertIn("Phone not paired", context.exception.read().decode())

            opener = build_opener(HTTPCookieProcessor(CookieJar()))
            with opener.open(base + "/?pair=one-launch-token") as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.geturl(), base + "/")
            with opener.open(base + "/api/health") as response:
                self.assertEqual(json.load(response), {"status": "ok"})

            with self.assertRaises(HTTPError) as context:
                urlopen(base + "/?pair=expired-token")
            self.assertEqual(context.exception.code, 401)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_pairing_identity_persists_privately_and_rotation_revokes_it(self):
        pairing_file = Path(self.temp.name) / "private-config" / "phone-token"
        original = _load_or_create_pairing_token(pairing_file)
        self.assertGreaterEqual(len(original), 24)
        self.assertEqual(_load_or_create_pairing_token(pairing_file), original)
        if sys.platform != "win32":
            self.assertEqual(pairing_file.stat().st_mode & 0o777, 0o600)
            self.assertEqual(pairing_file.parent.stat().st_mode & 0o777, 0o700)
        replacement = _load_or_create_pairing_token(pairing_file, rotate=True)
        self.assertNotEqual(replacement, original)
        self.assertEqual(pairing_file.read_text(encoding="ascii").strip(), replacement)

        pairing_file.unlink()
        pairing_file.symlink_to(Path(self.temp.name) / "elsewhere")
        with self.assertRaisesRegex(ValueError, "must not be a symlink"):
            _load_or_create_pairing_token(pairing_file)

    def test_evidence_gap_audit_flags_single_and_no_source_rows(self):
        audit = _evidence_gaps(ROOT / "data" / "dq7_reimagined.sqlite")
        self.assertEqual(audit["total"], 5)
        self.assertEqual(audit["single_source"], 2)
        self.assertEqual(audit["unsupported"], 1)
        self.assertEqual(audit["corroborated_but_unresolved"], 2)
        self.assertEqual(audit["unresolved_conflicts"], sum(
            row["count"] for row in audit["unresolved_conflicts_by_predicate"]
        ))
        self.assertGreater(audit["unresolved_conflicts"], 0)
        self.assertEqual(audit["source_freshness"]["total"], sum(
            audit["source_freshness"][key]
            for key in ("within_180_days", "over_180_days", "unknown")
        ))
        by_id = {row["gap_id"]: row for row in audit["gaps"]}
        self.assertEqual(by_id["gap_reproducible_farm_rates"]["sources"], [])
        self.assertEqual(by_id["gap_shell_shield_identity"]["source_count"], 1)
        self.assertIn(by_id["gap_shell_shield_identity"]["freshness_status"],
                      ("current_retrieval", "stale", "unknown"))
        self.assertIn("retrieval_age_days",
                      by_id["gap_shell_shield_identity"]["sources"][0])
        stellar = by_id["gap_stellar_fan_ui_name"]
        self.assertEqual(stellar["verification_tier"], "corroborated_but_unresolved")
        self.assertIn("English", stellar["acceptance_condition"])
        status, endpoint = self.get_json("/api/evidence-gaps")
        self.assertEqual(status, 200)
        self.assertEqual(endpoint["gaps"], audit["gaps"])

    def test_progress_audits_every_completion_ledger_without_false_zeroes(self):
        state_path = Path(self.temp.name) / "ledger-state.json"
        shutil.copy(ROOT / "player" / "ryan-save-state.json", state_path)
        progress = _progress(ROOT / "data" / "dq7_reimagined.sqlite", state_path)
        expected = {"medals", "items", "monsters", "tablets", "hearts",
                    "missables", "vocations", "achievements"}
        self.assertEqual(set(progress["ledger_audit"]), expected)
        self.assertTrue(all(progress["ledger_audit"][key]["status"] == "unknown"
                            for key in expected))
        self.assertTrue(all(progress[key]["display"] == "Unknown"
                            for key in expected))

        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["completion"]["monster_hearts_owned"] = []
        state["completion"]["items_obtained"] = ["item_cypress_stick", "stale_item"]
        state["completion"]["missables_missed"] = ["missable_wooden_doll"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        progress = _progress(ROOT / "data" / "dq7_reimagined.sqlite", state_path)
        self.assertEqual(progress["ledger_audit"]["hearts"]["known_count"], 0)
        self.assertEqual(progress["ledger_audit"]["hearts"]["status"], "partial")
        self.assertEqual(progress["ledger_audit"]["items"]["known_count"], 1)
        self.assertEqual(progress["ledger_audit"]["items"]["unknown_state_ids"],
                         ["stale_item"])
        self.assertEqual(progress["ledger_audit"]["missables"]["status"], "missed")

    def test_checkpoint_and_domain_endpoints(self):
        _, checkpoint = self.get_json("/api/checkpoints/cp_001_prologue")
        self.assertEqual(checkpoint["id"], "cp_001_prologue")
        self.assertIn("actions", checkpoint)
        self.assertEqual(checkpoint["stop_actions"][0]["title"], "Pearl's Fish Bits")
        self.assertNotEqual(checkpoint["actions"][0]["title"], "Step 1")
        self.assertTrue(checkpoint["actions"][0]["is_next"])
        later = [row for row in checkpoint["medals"] if row["timing"] == "later"]
        self.assertEqual([row["number"] for row in later], [6, 7])
        self.assertEqual(checkpoint["advancement_readiness"]["status"],
                         "blocked_by_stop")
        self.assertFalse(checkpoint["advancement_readiness"]["can_confirm_and_save_next"])
        _, shrine = self.get_json("/api/checkpoints/cp_002_estard_shrine")
        self.assertEqual(len(shrine["tablet_fragments"]), 4)
        self.assertTrue(all(row["source"]["url"] and row["source"]["locator"]
                            for row in shrine["tablet_fragments"]))
        self.assertTrue(shrine["checkpoint_items"])
        self.assertTrue(all(row["routes"] for row in shrine["checkpoint_items"]))
        self.assertTrue(all(route["source"]["locator"]
                            for row in shrine["checkpoint_items"]
                            for route in row["routes"]))
        due = [row for row in shrine["checkpoint_achievements"]
               if row["timing"] == "due_here"]
        self.assertEqual([row["id"] for row in due], ["ach_into_the_unknown"])
        _, prologue_achievements = self.get_json("/api/checkpoints/cp_001_prologue")
        self.assertTrue(prologue_achievements["checkpoint_achievements"])
        self.assertTrue(all(row["timing"] == "tracking_starts"
                            for row in prologue_achievements["checkpoint_achievements"]))
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
        self.assertTrue(conflicts[0]["required_evidence"])
        self.assertFalse(any("tempest shield" in row["subject"]
                             for row in conflicts))
        _, tempest_item = self.get_json("/api/items/Tempest%20Shield")
        tempest_chests = {row["location_text"] for row in tempest_item["routes"]
                          if row["method"] == "chest"}
        self.assertEqual(tempest_chests, {
            "Sanctum of the Cirrus", "Ventus Tower 2F, by the north stairs"
        })
        self.assertFalse(any("moonlighting" in row["subject"] for row in conflicts))
        stellar = next(row for row in conflicts if "stella fan" in row["subject"])
        self.assertIn("English in-game Item List", stellar["required_evidence"])
        self.assertIn("full fan name legible", stellar["required_evidence"])
        self.assertEqual(stellar["status"], "unresolved")
        _, stella_item = self.get_json("/api/items/Stella%20Fan")
        _, stellar_item = self.get_json("/api/items/Stellar%20Fan")
        self.assertEqual(stella_item["item"]["item_id"],
                         stellar_item["item"]["item_id"])
        self.assertEqual(stellar_item["item"]["name"], "Stellar Fan")
        _, all_conflicts = self.get_json("/api/conflicts?include_resolved=1")
        moonlighting = next(row for row in all_conflicts
                            if "moonlighting" in row["subject"])
        self.assertEqual(moonlighting["status"], "resolved")
        self.assertIn("process-stage", moonlighting["rationale"])
        iron = next(row for row in all_conflicts
                    if row["resolution_claim_id"] ==
                    "claim_iron_shield_game8_alltrades_price")
        self.assertEqual(iron["status"], "resolved")
        self.assertEqual(sum(claim["is_resolution"] for claim in iron["claims"]), 1)
        self.assertIn(iron["resolution_claim_id"],
                      {claim["id"] for claim in iron["claims"]})
        self.assertIsNone(iron["required_evidence"])
        self.assertIn("dedicated Alltrades Abbey map shop table", iron["rationale"])
        self.assertTrue(all(
            sum(claim["is_resolution"] for claim in row["claims"]) == 1
            for row in all_conflicts if row["status"] == "resolved"
        ))
        cautery = next(row for row in all_conflicts
                       if row["resolution_claim_id"] ==
                       "claim_cautery_sword_rpgsite_location")
        self.assertEqual(cautery["status"], "resolved")
        self.assertIn("dedicated Cautery Sword acquisition page",
                      cautery["rationale"])
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
        self.assertEqual(moon["venue_status"], "resolved_process_stages")
        self.assertEqual(len(moon["unlock_claims"]), 3)
        self.assertEqual(moon["unlock"]["value"]["trigger_location"],
                         "Shrine of Mysteries")
        self.assertEqual(moon["unlock"]["value"]["activation_location"],
                         "Alltrades Abbey")
        self.assertEqual(moon["mechanics"]["value"]["unknown_restrictions"],
                         ["Complete legal pairing restrictions"])
        self.assertFalse(moon["skill_retention"]["value"]["retained_after_switching"])
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
        self.assertEqual(hearts["ownership_tracking"], "unknown")
        self.assertIsNone(hearts["owned_count"])
        heart_id = hearts["hearts"][0]["heart_id"]
        _, heart = self.get_json("/api/monster-hearts/" + heart_id)
        self.assertEqual(heart["heart_id"], heart_id)
        self.assertTrue(heart["effect_text"])
        self.assertTrue(heart["source_url"])
        self.assertTrue(heart["locator"])
        self.assertIsNone(heart["owned"])
        self.assertEqual(heart["ownership_status"], "unknown")
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

    def test_monster_heart_api_starts_explicit_ledger_and_reverses(self):
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["completion"].pop("monster_hearts_owned", None)
        self.state.write_text(json.dumps(state), encoding="utf-8")
        status, result = self.patch_json(
            "/api/monster-hearts/heart_slime", {"completed": True}
        )
        self.assertEqual(status, 200)
        self.assertIn("Recorded Monster Heart", result["message"])
        _, heart = self.get_json("/api/monster-hearts/heart_slime")
        self.assertTrue(heart["owned"])
        self.assertEqual(heart["ownership_status"], "owned")
        _, registry = self.get_json("/api/monster-hearts")
        self.assertEqual(registry["ownership_tracking"], "explicit")
        self.assertEqual(registry["owned_count"], 1)
        self.patch_json("/api/monster-hearts/heart_slime", {"completed": False})
        _, heart = self.get_json("/api/monster-hearts/heart_slime")
        self.assertFalse(heart["owned"])
        self.assertEqual(heart["ownership_status"], "not_owned")
        with self.assertRaises(HTTPError) as error:
            self.patch_json("/api/monster-hearts/heart_fake", {"completed": True})
        self.assertEqual(error.exception.code, 404)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        state["completion"].pop("monster_hearts_owned", None)
        self.state.write_text(json.dumps(state), encoding="utf-8")
        _, missables = self.get_json("/api/missables?q=window&limit=3")
        self.assertGreater(missables["total"], 0)
        missable_id = missables["missables"][0]["missable_id"]
        _, missable = self.get_json("/api/missables/" + missable_id)
        self.assertIn(missable["window_status"], ("verified", "unresolved"))
        self.assertTrue(missable["source_url"])
        if missable["window_status"] == "unresolved":
            self.assertTrue(missable["provenance_gap"])
        _, blue_button = self.get_json("/api/missables/missable_blue_button")
        self.assertEqual(blue_button["window_status"], "unresolved")
        self.assertFalse(blue_button["stop_warning_eligible"])
        self.assertEqual(blue_button["available_from_checkpoint_id"],
                         "cp_004_emberdale")
        self.assertTrue(blue_button["window_gap_reason"])
        _, wooden_doll = self.get_json("/api/missables/missable_wooden_doll")
        self.assertEqual(wooden_doll["window_status"], "verified")
        self.assertTrue(wooden_doll["stop_warning_eligible"])
        self.assertIsNone(wooden_doll["window_gap_reason"])
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

    def test_stop_obligation_can_be_cleared_from_walkthrough(self):
        _, checkpoint = self.get_json("/api/checkpoints/cp_001_prologue")
        stop_id = checkpoint["stop_actions"][0]["id"]
        self.patch_json("/api/progress", {
            "kind": "action", "id": stop_id, "completed": True,
        })
        _, cleared = self.get_json("/api/checkpoints/cp_001_prologue")
        self.assertEqual(cleared["stop_actions"], [])
        self.assertEqual(cleared["stop_warnings"], [])
        self.patch_json("/api/progress", {
            "kind": "action", "id": stop_id, "completed": False,
        })
        _, reopened = self.get_json("/api/checkpoints/cp_001_prologue")
        self.assertEqual(reopened["stop_actions"][0]["id"], stop_id)

    def test_checkpoint_tablet_progress_stays_synchronized_with_registry(self):
        _, checkpoint = self.get_json("/api/checkpoints/cp_002_estard_shrine")
        fragment_id = checkpoint["tablet_fragments"][0]["id"]
        self.patch_json("/api/tablets/" + fragment_id, {"completed": True})
        _, updated_checkpoint = self.get_json("/api/checkpoints/cp_002_estard_shrine")
        fragment = next(row for row in updated_checkpoint["tablet_fragments"]
                        if row["id"] == fragment_id)
        self.assertTrue(fragment["found"])
        _, registry = self.get_json("/api/tablets")
        registry_fragment = next(row for row in registry["fragments"]
                                 if row["fragment_id"] == fragment_id)
        self.assertTrue(registry_fragment["found"])
        self.patch_json("/api/tablets/" + fragment_id, {"completed": False})

    def test_checkpoint_monster_and_item_progress_share_registry_ledgers(self):
        _, checkpoint = self.get_json("/api/checkpoints/cp_003_ballymolloy")
        monster_id = checkpoint["monsters"][0]["id"]
        item_id = checkpoint["checkpoint_items"][0]["id"]
        self.patch_json("/api/progress", {
            "kind": "monster", "id": monster_id, "completed": True,
        })
        self.patch_json("/api/items/" + item_id, {"completed": True})
        _, refreshed = self.get_json("/api/checkpoints/cp_003_ballymolloy")
        self.assertNotIn(monster_id, {row["id"] for row in refreshed["monsters"]})
        self.assertTrue(next(row for row in refreshed["checkpoint_items"]
                             if row["id"] == item_id)["obtained"])
        _, monster_registry = self.get_json("/api/monsters?q=" + monster_id)
        self.assertTrue(monster_registry["monsters"][0]["defeated"])
        _, item_registry = self.get_json("/api/items?q=" + item_id)
        self.assertTrue(item_registry["items"][0]["obtained"])
        self.patch_json("/api/progress", {
            "kind": "monster", "id": monster_id, "completed": False,
        })
        self.patch_json("/api/items/" + item_id, {"completed": False})

    def test_checkpoint_achievement_progress_shares_registry_ledger(self):
        _, checkpoint = self.get_json("/api/checkpoints/cp_002_estard_shrine")
        achievement = next(row for row in checkpoint["checkpoint_achievements"]
                           if row["timing"] == "due_here")
        self.patch_json("/api/achievements/" + achievement["id"],
                        {"completed": True})
        _, refreshed = self.get_json("/api/checkpoints/cp_002_estard_shrine")
        due = next(row for row in refreshed["checkpoint_achievements"]
                   if row["id"] == achievement["id"])
        self.assertTrue(due["unlocked"])
        _, registry = self.get_json("/api/achievements?q=" + achievement["id"])
        self.assertTrue(registry["achievements"][0]["unlocked"])
        self.patch_json("/api/achievements/" + achievement["id"],
                        {"completed": False})

    def test_checkpoint_missable_completion_clears_only_linked_verified_stop(self):
        _, prologue = self.get_json("/api/checkpoints/cp_001_prologue")
        fish = next(row for row in prologue["checkpoint_missables"]
                    if row["missable_id"] == "missable_fish_bits")
        self.assertTrue(fish["stop_warning_eligible"])
        self.patch_json("/api/missables/missable_fish_bits", {"completed": True})
        _, cleared = self.get_json("/api/checkpoints/cp_001_prologue")
        self.assertEqual(cleared["stop_actions"], [])
        self.assertEqual(cleared["checkpoint_missables"][0]["progress_status"],
                         "completed")
        _, registry = self.get_json("/api/missables/missable_fish_bits")
        self.assertEqual(registry["progress_status"], "completed")
        _, emberdale = self.get_json("/api/checkpoints/cp_004_emberdale")
        blue = next(row for row in emberdale["checkpoint_missables"]
                    if row["missable_id"] == "missable_blue_button")
        self.assertEqual(blue["window_status"], "unresolved")
        self.assertFalse(blue["stop_warning_eligible"])
        self.patch_json("/api/missables/missable_fish_bits", {"completed": False})
        _, reopened = self.get_json("/api/checkpoints/cp_001_prologue")
        self.assertTrue(reopened["stop_actions"])

    def test_parallel_browser_writes_do_not_lose_progress(self):
        _, items = self.get_json("/api/items?limit=12")
        item_ids = [row["item_id"] for row in items["items"]]

        def mark(item_id):
            return self.patch_json("/api/items/" + item_id, {"completed": True})[0]

        try:
            with ThreadPoolExecutor(max_workers=8) as executor:
                statuses = list(executor.map(mark, item_ids))
            self.assertEqual(statuses, [200] * len(item_ids))
            saved = json.loads(self.state.read_text(encoding="utf-8"))
            self.assertTrue(set(item_ids).issubset(saved["completion"]["items_obtained"]))
            leftovers = list(self.state.parent.glob(f".{self.state.name}.*.tmp"))
            self.assertEqual(leftovers, [])
        finally:
            for item_id in item_ids:
                self.patch_json("/api/items/" + item_id, {"completed": False})

    def test_advancement_readiness_requires_explicit_actions_and_manual_confirmation(self):
        state_path = Path(self.temp.name) / "advancement-state.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["story"]["checkpoint_id"] = "cp_001_prologue"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        initial = _checkpoint_view(ROOT / "data" / "dq7_reimagined.sqlite",
                                   state_path, "cp_001_prologue")
        required_ids = [row["id"] for row in initial["stop_actions"]]
        required_ids += [row["id"] for row in initial["actions"] if row["required"]]
        state["completion"]["obligations_completed"] = required_ids
        state_path.write_text(json.dumps(state), encoding="utf-8")
        ready = _checkpoint_view(ROOT / "data" / "dq7_reimagined.sqlite",
                                 state_path, "cp_001_prologue")
        self.assertEqual(ready["advancement_readiness"]["status"],
                         "manual_confirmation")
        self.assertTrue(ready["advancement_readiness"]["can_confirm_and_save_next"])
        self.assertTrue(ready["advancement_readiness"]["safe_condition_requires_player_confirmation"])
        self.assertEqual(ready["advancement_readiness"]["next_checkpoint"]["id"],
                         "cp_002_estard_shrine")
        preview = _checkpoint_view(ROOT / "data" / "dq7_reimagined.sqlite",
                                   state_path, "cp_002_estard_shrine")
        self.assertFalse(preview["advancement_readiness"]["saved_checkpoint_match"])
        self.assertFalse(preview["advancement_readiness"]["can_confirm_and_save_next"])

    def test_vocation_unlock_progress_uses_only_explicit_mastery(self):
        state_path = Path(self.temp.name) / "unlock-progress-state.json"
        state = json.loads((ROOT / "player" / "ryan-save-state.json").read_text())
        state["party"]["members"]["Hero"]["vocation_mastery"] = {
            "vocation_warrior": True,
            "vocation_martial_artist": True,
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")
        gladiator = _vocation_unlock_progress(
            ROOT / "data" / "dq7_reimagined.sqlite", state_path,
            "vocation_gladiator")
        hero = next(row for row in gladiator["party_progress"]
                    if row["party_member"] == "Hero")
        maribel = next(row for row in gladiator["party_progress"]
                       if row["party_member"] == "Maribel")
        self.assertEqual(hero["status"], "satisfied")
        self.assertEqual(hero["groups"][0]["needed_if_unknowns_are_unmastered"], 0)
        self.assertEqual(maribel["status"], "unknown")
        self.assertEqual(maribel["groups"][0]["needed_if_unknowns_are_unmastered"], 2)
        self.assertEqual(gladiator["cost_status"], "verified")
        self.assertEqual(gladiator["cost_profile"]["normalized_total_points"], 570)
        self.assertIn("arithmetic sum", gladiator["cost_note"])

        champion = _vocation_unlock_progress(
            ROOT / "data" / "dq7_reimagined.sqlite", state_path,
            "vocation_champion")
        hero_plan = next(row for row in champion["recursive_plans"]
                         if row["character"] == "Hero")
        next_ids = {row["vocation_id"] for row in hero_plan["next_options"]}
        self.assertIn("vocation_gladiator", next_ids)
        gladiator_option = next(row for row in hero_plan["next_options"]
                                if row["vocation_id"] == "vocation_gladiator")
        self.assertEqual(gladiator_option["progression"]["normalized_total_points"], 570)
        self.assertIn("vocation_priest", next_ids)
        self.assertNotIn("vocation_paladin", next_ids)
        champion_group = hero_plan["target"]["groups"][0]
        self.assertEqual(champion_group["rule"], "all_of")
        self.assertTrue(champion_group["source"]["url"])
        self.assertEqual(champion_group["candidates"][0]["tier"], "intermediate")

        druid = _vocation_unlock_progress(
            ROOT / "data" / "dq7_reimagined.sqlite", state_path,
            "vocation_druid")
        self.assertEqual(druid["groups"][0]["rule"], "any_n_of")
        self.assertEqual(druid["groups"][0]["required_count"], 2)
        self.assertEqual(len(druid["groups"][0]["candidates"]), 3)
        recursive_druid = next(row for row in druid["recursive_plans"]
                               if row["character"] == "Hero")
        self.assertEqual(recursive_druid["choice_policy"],
                         "All legal next options are shown; any_n_of branches are not ranked or silently selected.")

    def test_every_checkpoint_is_browser_ready_with_sourced_advice(self):
        _, checkpoints = self.get_json("/api/checkpoints")
        self.assertEqual(len(checkpoints), 33)
        for checkpoint in checkpoints:
            status, detail = self.get_json("/api/checkpoints/" + checkpoint["id"])
            self.assertEqual(status, 200)
            self.assertTrue(detail["actions"], checkpoint["id"])
            self.assertTrue(detail["safe_condition"], checkpoint["id"])
            for advice in detail["advice"]:
                self.assertTrue(advice["source"]["url"], advice["id"])
                self.assertTrue(advice["source"]["locator"], advice["id"])

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

        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/api/items/item_missing")
        self.assertEqual(caught.exception.code, 404)

        unknown = Request(
            self.base + "/api/progress",
            data=json.dumps({"kind": "monster", "id": "monster_missing",
                             "completed": True}).encode(),
            headers={"Content-Type": "application/json"}, method="PATCH",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(unknown)
        self.assertEqual(caught.exception.code, 404)

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

        for completed in (True, False):
            self.patch_json("/api/progress", {
                "kind": "medal", "id": 1, "completed": completed,
            })
        saved = json.loads(self.state.read_text())
        self.assertNotIn(1, saved["completion"]["mini_medals_found"])

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
        self.assertIn("dependency_progress", achievements["achievements"][0])
        _, achievement_detail = self.get_json("/api/achievements/" + achievement_id)
        self.assertIn(achievement_detail["dependency_progress"]["status"],
                      {"unknown", "partial", "target_met", "complete"})
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
