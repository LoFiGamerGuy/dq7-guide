# Dragon Quest VII Reimagined Completionist / Min-Max KB

This repository is a local, provenance-first knowledge base for a completionist and deliberately overpowered playthrough of **Dragon Quest VII Reimagined**. It combines:

- a structured SQLite database for facts and relationships;
- FTS5 search for RAG-style retrieval;
- a player-state file kept separate from shared game knowledge;
- source and conflict records so disagreements are visible;
- synthesized guidance that can answer “what is strongest and safe to do now?”
- a terse Prologue-through-Alltrades checklist with attributed gear and boss advice;

## Current status

Version `0.3.0-phase1` extends the reconstructed handoff with normalized chronology, automatic conflict detection for registered single-valued predicates, and checkpoint reporting. The original downloadable sandbox files were not exposed to the local Codex task, so this package does **not** claim byte-for-byte recovery. `RECOVERY_MANIFEST.md` lists what was recovered from the prior task and what still needs source-level re-ingestion.

The seed includes:

- all 26 vocation names;
- complete Beginner → Intermediate and Intermediate → Advanced prerequisites;
- sourced Moonlighting unlock/mechanics with the Shrine trigger and Alltrades activation stages independently corroborated;
- the seven named missable / choice-sensitive events from the initial pass;
- all 61 achievements with explicit player tracking;
- the complete 353-item, six-category Heroic Hoarder identity registry;
- all 19 Mini Medal reward thresholds, including the major power spikes;
- early gear power-spike notes;
- confirmed Metal Slime farming locations;
- 18 fixed Seed/Super Seed effects and one repeatable postgame reward rule with its unpublished pool left unknown;
- all 46 Monster Heart identities and sourced effects, with 41 shared-item routes plus explicit acquisition evidence for the five DLC/non-Heroic identities;
- ordered chronological checkpoints through the final postgame cleanup, all 33 with direct RPG Site section-range locators while guide-content coverage remains partial;
- a 604-page source registry with browser search and retrieval-freshness metadata;
- all 20 tablets and 71 tablet fragments;
- all 333 Monster List ordinals and all 10 Vicious species;
- all 333 source-verified English Monster List names;
- 476 checkpoint-gated encounters covering all 333 monsters and 227 verified drops;
- all directly published Lucky Panel standard-rank matrices normalized with exact-name gaps retained, plus independently verified free entry;
- all sourced rank skills and Let Loose perks for all 26 vocations;
- verified vocation proficiency earning, Seed, Moonlighting, and difficulty-setting rules, including Normal-setting 1/5/10 point awards and two-source progression profiles for all 26 vocations;
- verified qualitative stat modifiers for all non-default vocations;
- independently corroborated one-each weapon/shield/head/torso, two-accessory-slot, and Monster-Heart slot-use rules;
- independently corroborated Magic Shield Defence, Magical Might, Magical Mending, and elemental-reduction values;
- two-source Mighty Pip control advice with source-checked rank-2 Leg Sweep and Dazzle gates and Dazzle resistance disclosed;
- two-source early-gear profiles for Cautery Sword, Snooze Stick, White Shield, Iron Mask, Windcheater, and Sledgehammer;
- an empty, user-editable player save-state.

Records marked `reconstructed_seed` are based on the earlier task inventory and/or a fresh source check, not a recovered original row.

## Quick start

Requires Python 3.10+; there are no third-party runtime dependencies.

### Interactive web guide

On Windows, double-click `start-guide.bat`. On macOS/Linux run
`./start-guide.sh`. Or run:

```powershell
python scripts/guide_server.py --open-browser
```

Open `http://127.0.0.1:8765`. The responsive interface provides the dashboard, compact walkthrough, STOP warnings, concise strongest-now and completion-safe power plans, reversible verified equipment and vocation tracking, detailed conflicts, and searchable registries for sources, items, vocations, monsters, Monster Hearts, Seeds, missables, farms, medals, tablets, and achievements. Its first-use editor records an explicit checkpoint, medal count, party levels, current vocations, and mastery while preserving unknowns. It is mobile- and keyboard-friendly, hides completed steps by default, and saves only validated changes.

### Use on a phone while playing on Steam Deck

1. In Steam Deck Desktop Mode, put the Deck and phone on the same trusted Wi-Fi.
2. Open this folder in Konsole and run `./manage-steam-deck-guide.sh start`.
3. Open the printed `DQ7 guide (phone)` address on the phone and bookmark it.

That is the full normal setup. The server keeps running after Konsole closes while
the same Desktop Mode session remains active.

For day-to-day Steam Deck use, the optional manager keeps phone mode running after
its terminal closes (while the Desktop Mode user session stays alive):

```sh
./manage-steam-deck-guide.sh start
./manage-steam-deck-guide.sh status
./manage-steam-deck-guide.sh restart
./manage-steam-deck-guide.sh rotate
./manage-steam-deck-guide.sh logs
./manage-steam-deck-guide.sh doctor
./manage-steam-deck-guide.sh stop
```

`start` prints the private pairing URL; `status` shows it again. Normal restarts
retain the bookmarked credential. Use `rotate` to issue a new URL and revoke the
old one. To deliberately add a Desktop Mode
shortcut, run `./manage-steam-deck-guide.sh install-shortcut`; undo it with
`remove-shortcut`. This creates only `DQ7 Phone Guide.desktop` in the current
user's Desktop folder. It installs no service, autostart entry, package, or root
change. Runtime PID/log/credential files stay in the ignored `.guide-runtime/`
folder; the manager does not write its credential into a system configuration path.
`logs` shows recent server errors and may include the private pairing URL. `doctor`
checks Python, the database, process status, and prints the shortest connection fixes.

#### Use beside DQ7 in Gaming Mode

First pair and bookmark the phone once with the Desktop manager above. Then perform
one manual Steam setup:

1. In Desktop Mode choose **Games → Add a Non-Steam Game → Browse**.
2. Select `steam-deck/run-dq7-guide-gaming-mode.sh` in this repository.
3. Rename the library entry to **DQ7 Phone Guide**, then return to Gaming Mode.

For each play session, launch **DQ7 Phone Guide**, leave it running, launch or switch
to Dragon Quest VII, and use the existing phone bookmark. Use Steam's **Stop Game**
on the guide shortcut when finished. The server is owned by that foreground shortcut,
so stopping it ends sharing. Desktop and Gaming Mode reuse the same pairing identity;
no Steam configuration is edited programmatically and no service is installed.
See `docs/STEAM_DECK_GAMING_MODE.md` for the exact one-time and per-session flow,
including stop, backup, recovery, and re-pair troubleshooting.

SteamOS multitasking behavior can change between updates. If it suspends or stops the
guide when DQ7 launches, use DQ7 and the background manager together in Desktop Mode.
A changed Deck Wi-Fi address also requires opening the newly printed Desktop URL once.

For a visible one-session launcher instead, run `./start-guide-phone.sh`; keep its
Konsole open and press `Ctrl+C` to stop. On Windows, use `start-guide-phone.bat`.

SteamOS can stop or disconnect ordinary user processes when the Deck suspends,
reboots, changes network, or switches sessions (including a Desktop/Gaming Mode
transition). Background mode is dependable for switching between windows/apps in
the same Desktop Mode session, not a promise of persistence across those events.
Run `status`, then `restart` if necessary. The existing bookmark remains valid
unless you deliberately used `rotate`.

Phone mode is an explicit opt-in. The background manager stores one random pairing
identity in ignored repo-local runtime data. The one-session launcher stores its
identity in the user's private configuration directory. Both reuse their identity
so the phone bookmark keeps working. Only browsers opened through that
address receive access. To revoke every paired phone, stop the guide and run
`./start-guide-phone.sh --rotate-pairing`, then replace the old bookmark. Keep the
printed address private and do not use public Wi-Fi. The
ordinary launchers remain private to the computer. If the phone cannot
connect, allow Python through the Steam Deck firewall for the private/local network,
disable phone VPN or cellular fallback temporarily, and confirm both devices are on
the same Wi-Fi. No cloud account, internet service, QR provider, or third-party Python
package is involved. If the Deck's Wi-Fi address changes, open the newly printed URL;
the private pairing identity itself remains the same. A QR code is intentionally not generated: robust QR encoding is
not available in Python's standard library, and sending the private pairing address
to a third-party QR service would weaken this local-only design.

The normal phone URL uses local HTTP, so the Deck host must remain running and
reachable. Browsers only enable installable/offline service workers on localhost or
a secure HTTPS origin; when served that way, visited guide/API pages can reopen from
cache. Cached pages are always read-only: offline progress edits are rejected and
never queued, preventing hidden divergence from the canonical player file. The
Progress view can download a JSON backup and restore one with an explicit
confirmation; the host preserves the pre-restore state as a recovery file.
The in-app **Phone Setup** screen shows the current address, connection/write
status, secure-origin/offline-cache availability, launcher steps, and recovery
links. Treat browser “Add to Home Screen” on ordinary LAN HTTP as a bookmark only;
the guide does not claim offline installation in that mode.
The Dashboard and Phone Setup screens both expose one-tap progress backup; restore
stays under Progress to prevent an accidental replacement during play.

The Sources view also provides a dated audit of the remaining single-source,
unsupported, and corroborated-but-unresolved evidence gaps.

```powershell
python scripts/build_kb.py
python scripts/query_kb.py "alltrades vocation"
python scripts/checkpoint_report.py --checkpoint cp_004_emberdale
python scripts/walkthrough.py
python scripts/walkthrough.py --checkpoint cp_004_emberdale
python scripts/walkthrough.py --checkpoint cp_004_emberdale --compact
python scripts/walkthrough.py --checkpoint cp_004_emberdale --compact --monsters
python scripts/walkthrough.py --from cp_010_alltrades_present --through cp_014_sir_mervyn --sources
python scripts/walkthrough.py --from cp_015_greenthumb --through cp_029_ending_victory_lap
python scripts/walkthrough.py --from cp_030_postgame_another_world --through cp_033_arena_achievement_cleanup
python scripts/medal_report.py --through cp_009_alltrades
python scripts/item_report.py "Pilchard Crackers"
python scripts/item_report.py "Cautery Sword" --at-checkpoint cp_009_alltrades
python scripts/hoarder_report.py --gaps
python scripts/achievement_report.py
python scripts/achievement_report.py --all --sources
python scripts/vocation_report.py
python scripts/vocation_report.py --vocation "Martial Artist"
python scripts/monster_report.py "Cactiball"
python scripts/monster_report.py 9 --sources
python scripts/monster_report.py --checkpoint cp_003_ballymolloy
python scripts/monster_report.py --coverage
python scripts/heart_report.py --checkpoint cp_003_ballymolloy --sources
python scripts/conflict_report.py
python -m unittest tests.test_retrieval_quality -v
python -m unittest tests.test_first_use_e2e -v
python -m unittest discover -s tests -v
```

The build creates `data/dq7_reimagined.sqlite`. Generated databases are reproducible from committed seed JSON and the schema.

## Play alongside the guide

Show only the current checkpoint's essential warnings and actions:

```powershell
python scripts/walkthrough.py --compact
```

After identifying your current checkpoint, save it once; subsequent compact runs open there automatically:

```powershell
python scripts/player_progress.py checkpoint cp_003_ballymolloy
python scripts/player_progress.py done cp_003_ballymolloy 1
```

Use the exact step number printed by the walkthrough. The guide hides completed steps without inferring any unreported progress.

Update Ryan's state only from a player report:

```powershell
python scripts/update_state.py party.members.Hero.level 12
python scripts/update_state.py story.checkpoint_id cp_004_emberdale
```

The updater targets `player/ryan-save-state.json`, rejects unknown paths, and accepts `--state` for testing or an explicitly selected alternate player file.

Record play progress without inferring earlier completion:

```powershell
python scripts/player_progress.py checkpoint cp_004_emberdale
python scripts/player_progress.py done cp_004_emberdale 3
python scripts/player_progress.py medal-found 10 11
python scripts/player_progress.py medal-count 12
python scripts/player_progress.py achievement-unlocked ach_into_the_unknown
python scripts/player_progress.py item-obtained item_pilchard_crackers
python scripts/player_progress.py tablet-found tablet_fragment_001
python scripts/player_progress.py vocation-mastered Hero vocation_warrior
python scripts/player_progress.py monster-defeated 9
python scripts/player_progress.py heart-obtained heart_slime
```

## Key documents

- `AGENTS.md` — durable instructions for Codex and other coding agents.
- `HANDOFF.md` — architecture, decisions, current state, and first-session checklist.
- `INGEST_STATUS.md` — coverage ledger and next concrete targets.
- `docs/PRODUCT_READINESS.md` — verified interactive surface and intentional gaps.
- `docs/PHONE_COMPANION_READINESS.md` — cold-start, recovery, and SteamOS residual audit.
- `docs/STEAM_DECK_GAMING_MODE.md` — one-time pairing and Gaming Mode session steps.
- `docs/INGESTION_ROADMAP.md` — phased roadmap with acceptance gates.
- `docs/RETRIEVAL_QUALITY.md` — golden question/evidence audit and boundaries.
- `docs/PROVENANCE_AND_CONFLICT_POLICY.md` — evidence, citation, confidence, and conflict rules.
- `CODEX_KICKOFF_PROMPT.md` — ready-to-paste prompt for the first local Codex session.
- `RECOVERY_MANIFEST.md` — exact reconstruction disclosure.

## Repository layout

```text
data/
  schema.sql                 SQLite schema and FTS triggers
  seed/                      Human-reviewable source data
docs/                        Operating and ingestion policy
player/ryan-save-state.json  Mutable run state, separate from shared facts
scripts/build_kb.py          Reproducible database builder
scripts/query_kb.py          Search and provenance display
sources/README.md            Copyright-safe source cache policy
tests/                       Integrity and smoke tests
```

Phase 1 chronology is normalized in `mini_medal_locations` and `checkpoint_obligations`; source-specific medal ordering must not be silently merged with the canonical Game8 list numbering.

## Source strategy

RPG Site is the chronological completion backbone. Game8 is the structured optimization layer. Official or direct in-game evidence should verify disputed mechanics. Editorial recommendations remain attributed recommendations rather than being promoted to universal fact.

Do not mirror full copyrighted guides. Store normalized facts, short excerpts only when needed, original synthesis, and a source URL / locator for every claim.
