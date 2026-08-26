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
- Moonlighting unlock notes;
- the seven named missable / choice-sensitive events from the initial pass;
- all 19 Mini Medal reward thresholds, including the major power spikes;
- early gear power-spike notes;
- confirmed Metal Slime farming locations;
- high-value Monster Heart examples;
- initial chronological checkpoints through the first major vocation breakpoint;
- a 58-page source registry;
- an empty, user-editable player save-state.

Records marked `reconstructed_seed` are based on the earlier task inventory and/or a fresh source check, not a recovered original row.

## Quick start

Requires Python 3.10+; there are no third-party runtime dependencies.

```powershell
python scripts/build_kb.py
python scripts/query_kb.py "alltrades vocation"
python scripts/checkpoint_report.py --checkpoint cp_004_emberdale
python scripts/walkthrough.py
python scripts/walkthrough.py --checkpoint cp_004_emberdale
python scripts/walkthrough.py --from cp_010_alltrades_present --through cp_014_sir_mervyn --sources
python scripts/walkthrough.py --from cp_015_greenthumb --through cp_029_ending_victory_lap
python scripts/medal_report.py --through cp_009_alltrades
python scripts/item_report.py "Pilchard Crackers"
python scripts/item_report.py "Cautery Sword" --at-checkpoint cp_009_alltrades
python scripts/conflict_report.py
python -m unittest discover -s tests -v
```

The build creates `data/dq7_reimagined.sqlite`. Generated databases are reproducible from committed seed JSON and the schema.

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
```

## Key documents

- `AGENTS.md` — durable instructions for Codex and other coding agents.
- `HANDOFF.md` — architecture, decisions, current state, and first-session checklist.
- `INGEST_STATUS.md` — coverage ledger and next concrete targets.
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
