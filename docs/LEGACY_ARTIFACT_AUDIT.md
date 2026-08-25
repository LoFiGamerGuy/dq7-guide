# Legacy artifact audit

The repository contains an older v0.1 representation alongside the canonical v0.2 seed/build path. The canonical path is:

`data/seed/*.json` → `scripts/build_kb.py` → `data/dq7_reimagined.sqlite`

Ryan's only canonical player file is `player/ryan-save-state.json`.

## Safe duplicate removal

The tracked `temp/dq7_reimagined_kb_v0_2/` tree was byte-compared with its corresponding canonical files. Every non-database file matched, its database matched the previously committed canonical database, and no repository workflow referenced it. It was removed as a redundant handoff copy.

## v0.1 files retained pending migration

Do not delete the following as a group until the provisional facts below have been verified or explicitly retired:

- `source_registry.json`
- `knowledge/`
- `graph/relations.json`
- `rag/chunks.jsonl`
- `kb.sqlite`
- `player/player_state.json`

The old player file is empty and non-authoritative, but remains grouped with the legacy cleanup to make that cleanup reviewable.

The four source pages that existed only in the legacy registry—the Game8 trophy guide, starting-vocations guide, seed-farming guide, and skills tier list—were refreshed and registered canonically while preserving their published legacy IDs.

Fixed Seed and Super Seed effects, Klepto Clobber farming, and the Lucky Panel Pretty Betsy daily limit have now been migrated as medium-confidence indexed-source claims with locators. Potentially useful provisional facts still awaiting adjudication include Easy Going and Ruff's Whistle farming notes, six detailed equipment loadouts, eight Monster Heart effects, and a Moonlighting pairing matrix. These lack current precise locators and must not be promoted silently.

Once those facts are adjudicated, remove the v0.1 files in one explicit cleanup commit and add a guard ensuring scripts do not reference `player/player_state.json` or root `kb.sqlite`.
