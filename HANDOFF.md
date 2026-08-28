# Codex handoff

## Product intent

This is not meant to be a conventional fan wiki. It is a queryable decision aid for a long completionist / min-max run. The target question is:

> Given Ryan's exact story checkpoint and party state, what is the strongest possible party he can have right now without jeopardizing 100% completion?

That requires four layers to work together:

- **chronology:** where the player is and what becomes unavailable next;
- **structured facts:** items, equipment, shops, medals, tablets, vocations, skills, monsters, drops, hearts, achievements, and locations;
- **relationships:** unlocks, prerequisites, obtained-from, needed-for, available-at, and missable-after;
- **player state:** the user's actual levels, vocation mastery, gear, medals, seeds, inventory, achievements, and story position.

## Architecture decision

SQLite is the canonical local store. FTS5 provides lightweight RAG retrieval without requiring a hosted vector service. Seed JSON is committed for review and reproducible builds. A richer embedding index can be added later, but it must remain derivable and must never become the sole copy of provenance.

`scripts/guide_server.py` is the dependency-free local browser entry point. It serves `web/` and exposes read APIs over the generated SQLite database plus allowlisted progress mutations against the selected player-state file. The CLI remains supported and shares the same loaders and validation paths.

The schema deliberately separates:

- `entities` and `relationships` for the normalized graph;
- `claims` for source-scoped facts and recommendations;
- `conflicts` for disagreements;
- `documents` / `document_fts` for retrieval passages;
- domain tables for vocations, medal rewards, missables, farming spots, and checkpoints.

The browser exposes first-class item, vocation, monster, medal, tablet, and achievement registries alongside the walkthrough. Reads are state-aware and paginated; supported writes reuse the validated player-progress layer. Checkpoint selection is explicit, and the responsive UI includes keyboard focus, high-contrast support, loading/retry states, and a default hide-completed mode.

Current reproducible headline counts are 302 sources, 353 items with 501 acquisition paths, 333 monsters with 243 checkpoint-gated encounters and 144 verified drops, all 46 Monster Heart identities/effects, 8 checkpoint-gated farms with separate fact/strategy provenance, 7 sourced missable records (5 exact and 2 unresolved cutoffs), 14 Lucky Panel pools with 91 rewards, 100 Mini Medals, 71 tablet fragments, 61 achievements, and 26 complete vocation skill/perk ladders. `INGEST_STATUS.md` remains the authoritative detailed ledger.

## Source methodology

- **RPG Site**: chronological 100% route and Heroic Hoarder / Lucky Panel completeness backbone.
- **Game8**: vocation structure, character builds, equipment power spikes, farming, Monster Hearts, and system-specific tables.
- **Official / in-game evidence**: highest-priority verification for mechanics, patches, names, and disputed facts.
- **Specialist/community sources**: corroboration or discovery only; record scope and reliability.

See `docs/PROVENANCE_AND_CONFLICT_POLICY.md` before adding claims.

## What the earlier v0.1 task documented

The prior sandbox build was reported to contain:

- 20 high-value RPG Site / Game8 source records;
- all 26 vocation names;
- the complete Intermediate and Advanced prerequisite graph;
- Moonlighting unlock and pairing notes;
- initial missables, starting with Pearl's Fish Bits;
- major Mini Medal reward power spikes;
- early / mid / late gear notes;
- Lucky Panel completion and early-power notes;
- EXP / Metal farming locations;
- fixed seed effects and postgame Super Seed farming;
- high-value Monster Heart effects;
- walkthrough checkpoints through the first major vocation breakpoint;
- player-state storage;
- working FTS5 retrieval.

The original files themselves were not attached to this local task. This `v0.2` package reconstructs that documented surface area and labels it accordingly. See `RECOVERY_MANIFEST.md`.

## First Codex session

1. Run the builder and tests.
2. Inspect the coverage report in `INGEST_STATUS.md`.
3. Start Phase 1 with the RPG Site walkthrough checkpoint graph and the 100 Mini Medal rows.
4. Keep the batch small enough to review; update provenance and status in the same change.
5. Query a known checkpoint such as `alltrades vocation` and confirm results include chronology, unlock rules, Lucky Panel, and missable context.

## Definition of the first useful milestone

The KB is useful during live play when, for every checkpoint through Alltrades Abbey, it can reliably answer:

- What must I collect or do before leaving?
- What is permanently or temporarily missable?
- What equipment is obtainable now, and what should I buy versus obtain elsewhere?
- What is the best legal party setup now?
- Which vocation ranks should each character pursue next?
- Which farm is efficient now, and what is a sensible stopping point?

## Known risks

- Guide pages can change after ingestion; source freshness must be tracked.
- Search snippets can truncate tables or omit context; never treat them as final evidence.
- “Best” recommendations depend on checkpoint, character, difficulty, DLC, and grinding tolerance.
- Past and Present locations often share names; time-period scoping is mandatory.
- Completion requirements and optional collector-only items are not always identical.
- The user's actual save state is currently empty; personalized recommendations must expose this uncertainty.
