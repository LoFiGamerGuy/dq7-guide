import unittest
from http.cookiejar import CookieJar
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, build_opener, urlopen


ROOT = Path(__file__).resolve().parents[1]


class _MobileContractParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.play_bar_depth = 0
        self.play_bar_buttons = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if values.get("id") == "playBar":
            self.play_bar_depth = 1
        elif self.play_bar_depth:
            self.play_bar_depth += 1
            if tag == "button":
                self.play_bar_buttons.append(values.get("id") or values.get("data-mobile-view"))

    def handle_endtag(self, tag):
        if self.play_bar_depth:
            self.play_bar_depth -= 1


class MobileUiContractTests(unittest.TestCase):
    def test_dlc_hearts_show_ownership_warning_before_availability_detail(self):
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        warning = js.index("DLC ownership unconfirmed")
        detail = js.index("Earliest verified gate", warning)
        self.assertLess(warning, detail)
        self.assertIn('detail.dlc_ownership_status === "unknown"', js)
        self.assertIn("not shown as currently obtainable", js)
        self.assertIn('data-dlc-entitlement=', js)
        self.assertIn("Owned / installed", js)
        self.assertIn("Not owned", js)
        self.assertIn("Not reported", js)
        self.assertIn("/dlc-entitlements/", js)

    def test_verified_seed_pool_and_achievement_conflicts_are_visible(self):
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("Verified eligible pool", js)
        self.assertIn("Selection weights unknown", js)
        self.assertIn("Counter rule conflict — do not assume", js)
        self.assertIn("Resolved counter rule · independently corroborated", js)
        self.assertIn("The losing interpretation remains visible below", js)
        self.assertNotIn("Bank 300,000 gold at once before spending it", js)
        self.assertIn("requirement_verification_status", js)

    def test_phone_companion_controls_and_safe_area_support_are_present(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("viewport-fit=cover", html)
        self.assertIn('id="playBar"', html)
        self.assertIn('id="mobilePrevious"', html)
        self.assertIn('id="mobileCurrent"', html)
        self.assertIn('id="mobileNext"', html)
        self.assertIn('id="mobilePower"', html)
        self.assertIn("safe-area-inset-bottom", css)
        self.assertIn("prefers-color-scheme: dark", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn('$("#mobilePrevious")', js)
        self.assertIn('$("#mobileNext")', js)
        self.assertIn('$("#mobileCurrent")', js)
        self.assertIn('$("#mobilePower")', js)
        self.assertIn('scrollToPlaySection("power")', js)
        self.assertIn('"Preview · not saved"', js)
        self.assertIn('savedCheckpoint ? "Set current" : "Start here"', js)
        self.assertIn('setCurrent.disabled = isSavedCurrent', js)
        self.assertIn('const viewedCheckpoint = state.checkpoint?.id', js)
        self.assertIn('viewedCheckpoint && state.checkpoints.some', js)
        self.assertIn('data-play-jump="power"', html)
        self.assertIn("function scrollToPlayPriority()", js)
        self.assertIn('power: $("#powerPlan .next-power") || $("#powerAdvice")', js)
        self.assertNotIn('power: $(\'[aria-labelledby="advice-strongest_now"]\')', js)
        self.assertIn('id="powerPlan"', html)
        self.assertIn("Next power move", js)
        self.assertIn("strongest.slice(1)", js)
        self.assertIn('class="power-more"', js)
        self.assertIn("More strongest-now advice", js)
        self.assertIn("Next vocation payoff", js)
        self.assertIn("Prepare for", js)
        self.assertIn("Single-source boss recommendation", js)
        self.assertIn("Two-source boss recommendation", js)
        self.assertIn(", not required</span>", js)
        self.assertIn('const rankEvidence', js)
        self.assertIn("missing rank stays unknown", js)
        self.assertIn('class="boss-prep"', js)
        self.assertIn('class="battle-plan"', js)
        self.assertIn("Saved roles · sourced tactics · no ranking", js)
        self.assertIn("Core 2-source · extras 1-source", js)
        self.assertIn("2-source · link audit", js)
        self.assertIn("Evidence audit pending", js)
        self.assertIn("Core 2-source · extras 1-source", js)
        self.assertIn('class="evidence-strength"', js)
        self.assertIn('corroborated_but_unresolved: "2+ sources · still unresolved"', js)
        self.assertIn('guide_text_conflict: "Direct UI needed to resolve conflict"', js)
        self.assertIn("Open question · ${escapeHtml(gapStatus(gap))}", js)
        self.assertIn("<b>Needed:</b>", js)
        self.assertIn("Consensus resolution · separate claim", js)
        self.assertIn("c.resolution_is_external", js)
        self.assertIn("Independent matching publishers:", js)
        self.assertIn("c.resolution_evidence", js)
        self.assertIn("Party roles", js)
        self.assertIn("Fight plan", js)
        self.assertIn("Skill prep", js)
        self.assertIn("bossTactics.slice(0, 2)", js)
        self.assertIn("later fights", js)
        self.assertIn(".battle-plan-more", css)
        self.assertIn('row.state_status === "skill_available" ? "READY"', js)
        self.assertIn('"2-source tactic" : "1-source tactic"', js)
        self.assertIn("rank 1-source", js)
        self.assertIn(".battle-plan-list", css)
        self.assertIn("function renderPowerPlan", js)
        self.assertIn("Optional grind ceiling", js)
        self.assertIn('class="play-brief"', js)
        self.assertIn("At a glance", js)
        self.assertIn('briefRow("POWER"', js)
        self.assertIn('briefRow("SAFE"', js)
        self.assertIn('briefRow("GRIND"', js)
        self.assertIn('briefRow("LEAVE"', js)
        self.assertIn("Skip — none recommended", js)
        self.assertIn(".play-brief", css)
        self.assertIn("Other farms available by now", js)
        self.assertIn('mp_absorption_percent: "MP absorption"', js)
        self.assertIn('agility_bonus: "Agi"', js)
        self.assertIn('fire_damage_reduction_percent: "fire reduction"', js)
        self.assertIn('block_chance_percent: "block"', js)
        self.assertIn("<b>Battle use:</b>", js)
        self.assertIn('id="quickSetupForm"', html)
        self.assertIn("function quickSetupPayload", js)
        self.assertIn('recordCommand("party-setup"', js)
        self.assertIn("Party plan personalized.", js)
        self.assertIn('aria-describedby="quickSetupHint"', html)
        self.assertIn('id="quickSetupError"', html)
        self.assertIn('aria-label="${escapeHtml(member.name)} level"', js)
        self.assertIn('error.focus()', js)
        self.assertIn("Nothing was recorded.", js)
        self.assertIn("submit.disabled = true", js)
        self.assertIn("Known values are prefilled", html)
        self.assertIn('id="checkpointFinder"', html)
        self.assertIn('id="checkpointFinderInput"', html)
        self.assertIn("function renderCheckpointFinder", js)
        self.assertIn("row.entry_condition", js)
        self.assertIn('data-preview-checkpoint=', js)
        self.assertIn("Not saved as current.", js)
        self.assertIn('data-save-found-checkpoint=', js)
        self.assertIn("as your current checkpoint?", js)
        self.assertIn('finder.hidden = Boolean(saved)', js)
        self.assertIn("checkpoint-finder-results", css)
        self.assertIn("(max-width: 900px) and (pointer: coarse)", css)
        self.assertIn("grid-template-columns: 1.65rem minmax(0, 1fr)", css)
        self.assertIn(".checkpoint-picker .select-label { min-width: 0", css)

    def test_mobile_restore_and_long_details_are_keyboard_and_overflow_safe(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="chooseRestoreButton"', html)
        self.assertIn('role="alertdialog"', html)
        self.assertIn('aria-labelledby="restoreTitle"', html)
        self.assertIn('$("#confirmRestoreButton").focus()', js)
        self.assertIn("function cancelRestore()", js)
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn("scrollIntoView", js)

    def test_item_quantity_controls_preserve_unknowns_and_large_touch_targets(self):
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("Copies: unknown · may be zero", js)
        self.assertNotIn("Copies: unknown · not zero", js)
        self.assertIn('inputmode="numeric" min="0" max="99"', js)
        self.assertIn("Clear to unknown", js)
        self.assertIn("Routes never change this value", js)
        self.assertIn("item-quantity", js)
        self.assertIn("previousObtained", js)
        self.assertIn("currently Rabbit Tail and Meteorite Bracer qualify", js)
        self.assertIn("Monster Heart duplicates remain unsupported", js)
        self.assertIn(".callout [data-item-quantity-input]", css)
        self.assertIn("[data-item-quantity-clear] { min-height: 2.75rem", css)

    def test_active_play_writes_are_guarded_reversible_and_context_preserving(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="undoSnackbar"', html)
        self.assertIn('id="undoButton"', html)
        self.assertIn(".undo-snackbar", css)
        self.assertIn("async function oneMutation", js)
        self.assertIn("async function refreshPreservingPlayContext", js)
        self.assertIn('window.confirm("Mark this STOP cleared?")', js)
        self.assertIn('window.confirm("Advance the saved checkpoint?")', js)
        self.assertIn("Required work clear · tap Advance when ready.", js)
        self.assertIn("function focusPlayPriority()", js)
        self.assertIn('classList.toggle("advance-ready"', js)
        self.assertIn('aria-describedby="safeCondition advanceReason"', html)
        self.assertIn('id="advanceStatus" class="tag" role="status"', html)
        self.assertIn('showUndo("Accessory saved."', js)
        self.assertIn('showUndo("Checkpoint saved."', js)
        self.assertIn('data-power-item-owned=', js)
        self.assertIn("Ownership tracking only · does not equip", js)
        self.assertIn("does not equip it", js)
        self.assertIn('showUndo("Item marked owned."', js)
        self.assertNotIn("Mark equipped", js)
        self.assertIn('data-power-equip-item=', js)
        self.assertIn('/equipment/slots/', js)
        self.assertIn('showUndo("Equipment saved."', js)
        self.assertIn("Validated equipment tracking enabled", js)
        self.assertIn("<b>Get now:</b>", js)
        self.assertIn("<b>Verified:</b>", js)
        self.assertIn("Sourced loadout checks", js)
        self.assertIn("Grouped by character · source order · not a complete or ranked loadout.", js)
        self.assertIn("availableGear.reduce((groups, row)", js)
        self.assertIn('class="gear-slot"', js)
        self.assertIn(".gear-character", css)
        self.assertIn(".gear-item-heading", css)
        self.assertIn("all-element reduction", js)
        self.assertIn("row.obtainable_routes?.[0]", js)
        self.assertIn("+${extraRoutes} routes", js)
        self.assertIn('data-power-vocation-mastered=', js)
        self.assertIn('showUndo("Vocation mastery recorded."', js)
        self.assertIn("Branch choice preserved · payoffs shown, options not ranked.", js)
        self.assertIn("Let Loose:", js)
        self.assertIn("option.power_payoff?.earliest_skill", js)
        self.assertIn("member?.standard_slots?.[slot]", js)
        self.assertIn("Replace the currently recorded ${slot}?", js)
        self.assertIn('id="quickMasteryForm"', html)
        self.assertIn('renderQuickMastery(Boolean(c.power_plan?.vocation_tracking_available))', js)
        self.assertIn('$("#quickMastery").hidden = !available', js)
        self.assertIn("Only record this after", html)
        self.assertIn("Record ${vocationName} mastered for ${character}?", js)
        self.assertIn('showUndo("Vocation mastery recorded."', js)
        self.assertIn("!mastered.has(row.vocation_id)", js)
        self.assertIn('window.confirm("Remove this recorded mastery?")', js)
        self.assertIn('"Vocation mastery removed."', js)
        self.assertIn("state.usingCachedData || state.hostReachable === false", js)
        self.assertIn('window.addEventListener("online", () => loadAll()', js)
        self.assertNotIn('window.addEventListener("online", () => { state.usingCachedData = false', js)

    def test_narrow_and_landscape_dom_contract_has_no_duplicate_controls(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        parser = _MobileContractParser()
        parser.feed(html)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertEqual(parser.play_bar_buttons,
                         ["dashboard", "mobilePrevious", "mobileCurrent",
                          "mobileNext", "mobilePower"])
        self.assertIn("@media (max-width: 900px) and (pointer: coarse)", css)
        self.assertIn("bottom: calc(4.35rem + env(safe-area-inset-bottom))", css)
        self.assertIn("repeat(2, minmax(0, 1fr))", css)
        self.assertIn(".section-heading .heading-actions { width: 100%; }", css)
        self.assertNotIn("#walkthrough > .section-heading { position: sticky", css)
        self.assertIn(".play-jumps { display: grid; grid-template-columns: repeat(3, 1fr); position: sticky; top: calc(3.8rem", css)
        self.assertIn('heading.textContent = "Clear before advancing"', js)
        self.assertNotIn('heading.textContent = "STOP', js)

    def test_play_view_prioritizes_stop_next_and_collapses_secondary_ledgers(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertLess(html.index('id="checkpointStop"'), html.index('id="actions"'))
        self.assertLess(html.index('id="actions"'), html.index('id="checkpointTablets"'))
        self.assertEqual(html.count('class="panel secondary-ledger"'), 6)
        self.assertNotIn('class="panel secondary-ledger" open', html)
        self.assertIn("ledger.open = !mobileLayout()", js)
        self.assertIn('$("#hideCompleted")', js)

    def test_next_power_move_precedes_party_and_battle_detail(self):
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        render_start = js.index('target.innerHTML = `${nextPowerSection}<p class="power-party"')
        self.assertGreater(render_start, js.index('const nextPowerSection ='))
        self.assertIn('class="next-power" aria-labelledby="nextPowerHeading"', js)
        self.assertIn('power: $("#powerPlan .next-power") || $("#powerAdvice")', js)
        self.assertIn(".next-power {", css)
        self.assertLess(js.index('id="checkpointStop"') if 'id="checkpointStop"' in js else 0,
                        js.index('const nextPowerSection ='))

    def test_long_checkpoint_actions_show_next_three_before_later_work(self):
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("function renderCheckpointActions", js)
        self.assertIn("visible.slice(0, 3)", js)
        self.assertIn("Later in this checkpoint", js)
        self.assertIn('renderCheckpointActions($("#actions")', js)
        self.assertIn(".later-actions > summary", css)

    def test_phone_setup_diagnoses_security_and_exposes_recovery(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        manifest = (ROOT / "web" / "manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn('data-view="phone-setup"', html)
        self.assertIn('id="phoneSetupStatus"', html)
        self.assertIn("Local HTTP is online-to-host only", html)
        self.assertIn('href="/api/state-backup"', html)
        self.assertIn("window.isSecureContext", js)
        self.assertIn("Unavailable on this LAN HTTP address", js)
        self.assertIn("Shell only · paired data requires host", js)
        self.assertIn("Unpaired host-local data available", js)
        self.assertIn("Disabled — never queued", js)
        self.assertIn('"display": "standalone"', manifest)

    def test_real_host_failure_has_phone_recovery_even_when_browser_reports_online(self):
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("hostReachable: null", js)
        self.assertIn("state.hostReachable = false", js)
        failure_guard = js.index("if (response.status >= 500)")
        reachable = js.index("state.hostReachable = true", failure_guard)
        self.assertLess(failure_guard, reachable)
        self.assertIn("state.usingCachedData = false", js[failure_guard:reachable])
        self.assertIn("renderConnectionState(false)", js[failure_guard:reachable])
        self.assertIn("navigator.onLine && state.hostReachable !== false", js)
        self.assertIn('data-reconnect', js)
        self.assertIn('visibilitychange', js)
        self.assertIn('state.hostReachable === false || state.usingCachedData', js)
        self.assertIn('state.usingCachedData = isCached', js)
        self.assertIn('addEventListener("controllerchange"', js)
        self.assertIn('registration => registration.update()', js)
        self.assertIn(".play-jumps", css)

    def test_phone_launcher_opts_in_to_lan_mode(self):
        launcher = (ROOT / "start-guide-phone.sh").read_text(encoding="utf-8")
        windows_launcher = (ROOT / "start-guide-phone.bat").read_text(encoding="utf-8")
        server = (ROOT / "scripts" / "guide_server.py").read_text(encoding="utf-8")
        self.assertIn("--lan --open-browser", launcher)
        self.assertIn("--lan --open-browser", windows_launcher)
        self.assertIn("sys.version_info.minor in range(10, 100)", windows_launcher)
        self.assertNotIn("sys.version_info ^<", windows_launcher)
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('"X-DQ7-Pair": pairingToken', app)
        self.assertIn('parser.add_argument("--lan"', server)
        self.assertIn('args.host = "0.0.0.0"', server)

    def test_steam_deck_manager_is_explicit_reversible_and_repo_contained(self):
        manager = ROOT / "manage-steam-deck-guide.sh"
        template = ROOT / "steam-deck" / "DQ7 Guide.desktop.in"
        gaming_wrapper = ROOT / "steam-deck" / "run-dq7-guide-gaming-mode.sh"
        script = manager.read_text(encoding="utf-8")
        desktop = template.read_text(encoding="utf-8")
        subprocess.run(["sh", "-n", str(manager)], check=True)
        result = subprocess.run(["sh", str(manager), "status"], check=True,
                                capture_output=True, text=True)
        self.assertRegex(result.stdout, r"(running|stopped)")
        self.assertIn("nohup python3 -u scripts/guide_server.py --lan", script)
        self.assertIn('--pairing-file "$pairing_file"', script)
        self.assertIn("rotate)", script)
        self.assertIn("logs)", script)
        self.assertIn("doctor)", script)
        self.assertIn("install-shortcut", script)
        self.assertIn("remove-shortcut", script)
        self.assertNotIn("sudo", script)
        self.assertNotIn("systemctl", script)
        self.assertIn("@REPO@/manage-steam-deck-guide.sh", desktop)
        self.assertIn('manage-steam-deck-guide.sh" foreground',
                      gaming_wrapper.read_text(encoding="utf-8"))
        subprocess.run(["sh", "-n", str(gaming_wrapper)], check=True)
        self.assertIn('href="/api/state-backup"',
                      (ROOT / "web" / "index.html").read_text(encoding="utf-8"))

    def test_heart_routes_show_finite_supply_and_evidence_strength(self):
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function heartRouteSafety(route)", js)
        self.assertIn('route.supply_type === "finite"', js)
        self.assertIn("route.finite_total ?? route.quantity", js)
        self.assertIn("Finite pickup", js)
        self.assertIn("No repeatable Heart route established", js)
        self.assertIn("function heartRouteEvidence(route)", js)
        self.assertIn("Two-source route", js)

    def test_steam_deck_manager_full_isolated_lifecycle(self):
        manager = ROOT / "manage-steam-deck-guide.sh"
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory)
            runtime = isolated / "runtime"
            state = isolated / "player.json"
            shutil.copy(ROOT / "player" / "ryan-save-state.json", state)
            original_state = state.read_bytes()
            env = os.environ.copy()
            env.update({
                "DQ7_GUIDE_RUNTIME_DIR": str(runtime),
                "DQ7_GUIDE_STATE_FILE": str(state),
                "DQ7_GUIDE_PORT": "0",
                "DQ7_GUIDE_FORCE_PAIRING": "1",
            })

            def manage(command):
                return subprocess.run(
                    ["sh", str(manager), command], cwd=ROOT, env=env,
                    check=True, capture_output=True, text=True, timeout=15,
                ).stdout

            def phone_url(output):
                return next(line.split(": ", 1)[1] for line in output.splitlines()
                            if line.startswith("DQ7 guide (phone):"))

            try:
                first_output = manage("start")
                first_url = phone_url(first_output)
                first_clean = first_url.split("/?pair=", 1)[0]
                with self.assertRaises(HTTPError) as context:
                    urlopen(first_clean + "/api/health")
                self.assertEqual(context.exception.code, 401)
                opener = build_opener(HTTPCookieProcessor(CookieJar()))
                with opener.open(first_url) as response:
                    self.assertEqual(response.status, 200)
                with opener.open(first_clean + "/api/health") as response:
                    self.assertEqual(json.load(response), {"status": "ok"})
                self.assertIn("running", manage("status"))
                token_before = (runtime / "phone-pairing-token").read_text()
                if os.name != "nt":
                    self.assertEqual(runtime.stat().st_mode & 0o777, 0o700)
                    self.assertEqual((runtime / "server.log").stat().st_mode & 0o777,
                                     0o600)

                restarted = manage("restart")
                restart_url = phone_url(restarted)
                restart_clean = restart_url.split("/?pair=", 1)[0]
                self.assertEqual((runtime / "phone-pairing-token").read_text(), token_before)
                with opener.open(restart_clean + "/api/health") as response:
                    self.assertEqual(json.load(response), {"status": "ok"})

                rotated = manage("rotate")
                rotated_url = phone_url(rotated)
                rotated_clean = rotated_url.split("/?pair=", 1)[0]
                self.assertNotEqual((runtime / "phone-pairing-token").read_text(),
                                    token_before)
                with self.assertRaises(HTTPError) as context:
                    opener.open(rotated_clean + "/api/health")
                self.assertEqual(context.exception.code, 401)
                rotated_opener = build_opener(HTTPCookieProcessor(CookieJar()))
                with rotated_opener.open(rotated_url) as response:
                    self.assertEqual(response.status, 200)
                self.assertIn("stopped", manage("stop"))
                self.assertIn("stopped", manage("status"))

                gaming_log = isolated / "gaming-mode.log"
                with gaming_log.open("w+", encoding="utf-8") as output:
                    gaming = subprocess.Popen(
                        [str(ROOT / "steam-deck" / "run-dq7-guide-gaming-mode.sh")],
                        cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT,
                        text=True,
                    )
                    try:
                        deadline = time.monotonic() + 5
                        gaming_url = None
                        while time.monotonic() < deadline:
                            output.flush()
                            contents = gaming_log.read_text(encoding="utf-8")
                            urls = [line.split(": ", 1)[1] for line in contents.splitlines()
                                    if line.startswith("DQ7 guide (phone):")]
                            if urls:
                                gaming_url = urls[0]
                                break
                            if gaming.poll() is not None:
                                self.fail(f"Gaming Mode wrapper exited early: {contents}")
                            time.sleep(0.05)
                        self.assertIsNotNone(gaming_url)
                        gaming_clean = gaming_url.split("/?pair=", 1)[0]
                        with rotated_opener.open(gaming_clean + "/api/health") as response:
                            self.assertEqual(json.load(response), {"status": "ok"})
                    finally:
                        gaming.terminate()
                        self.assertEqual(gaming.wait(timeout=5), 0)
                with self.assertRaises((URLError, ConnectionResetError)):
                    urlopen(gaming_clean + "/api/health", timeout=0.5)

                runtime.mkdir(exist_ok=True)
                (runtime / "server.pid").write_text(f"{os.getpid()}\n")
                self.assertIn("not running", manage("stop"))
                self.assertFalse((runtime / "server.pid").exists())
                self.assertEqual(state.read_bytes(), original_state)
            finally:
                subprocess.run(["sh", str(manager), "stop"], cwd=ROOT, env=env,
                               capture_output=True, text=True, timeout=15)
        self.assertIn("player/*.before-restore-*.json",
                      (ROOT / ".gitignore").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
