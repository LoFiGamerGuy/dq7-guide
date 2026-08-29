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
- a 478-page source registry with browser search and retrieval-freshness metadata;
- all 20 tablets and 71 tablet fragments;
- all 333 Monster List ordinals and all 10 Vicious species;
- all 333 source-verified English Monster List names;
- 476 checkpoint-gated encounters covering all 333 monsters and 227 verified drops;
- all directly published Lucky Panel standard-rank matrices normalized with exact-name gaps retained, plus independently verified free entry;
- all sourced rank skills and Let Loose perks for all 26 vocations;
- verified vocation proficiency earning, Seed, Moonlighting, and difficulty-setting rules, including Normal-setting 1/5/10 point awards and the first two-source numeric mastery ladder;
- verified qualitative stat modifiers for all non-default vocations;
- independently corroborated two-accessory-slot and Monster-Heart slot-use rules;
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

Open `http://127.0.0.1:8765`. The responsive interface provides the dashboard, compact walkthrough, STOP warnings, advice, progress, read-only equipment comparison, detailed conflicts, and searchable registries for sources, items, vocations, monsters, Monster Hearts, Seeds, missables, farms, medals, tablets, and achievements. Its first-use editor records an explicit checkpoint, medal count, party levels, current vocations, and mastery while preserving unknowns. It is mobile- and keyboard-friendly, hides completed steps by default, and saves only validated changes.

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
- `docs/INGESTION_ROADMAP.md` — phased roadmap with acceptance gates.
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
