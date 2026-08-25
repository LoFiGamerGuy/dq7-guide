# AGENTS.md

## Mission

Maintain this repository as the durable source of truth for Ryan's **Dragon Quest VII Reimagined** completionist / min-max playthrough. Optimize for two simultaneous goals:

1. protect 100% completion and warn before irreversible or time-sensitive actions;
2. identify the strongest party, equipment, vocation plan, and efficient farms available at the player's exact checkpoint.

Do not collapse “completion-safe” and “maximum immediate power” into one recommendation when they differ. State the tradeoff.

## Read first

Before changing data or architecture, read:

1. `README.md`
2. `HANDOFF.md`
3. `INGEST_STATUS.md`
4. `docs/PROVENANCE_AND_CONFLICT_POLICY.md`
5. `docs/INGESTION_ROADMAP.md`
6. `player/ryan-save-state.json`

## Non-negotiable data rules

- Every externally sourced claim must resolve to a `source_id` and a precise locator when the page permits it.
- Preserve source wording as a short excerpt only when necessary to adjudicate a conflict. Prefer normalized facts and original summaries.
- Never silently merge conflicting facts. Record both claims in `claims`, connect a `conflicts` row, and leave resolution explicit.
- Separate observable facts from recommendations. A guide's “best” build is an attributed recommendation, not canonical truth.
- Separate game version, platform, patch, region, and time period (`Past` / `Present`) whenever they can change the answer.
- Do not use legacy PS1 or 3DS facts as Reimagined facts without explicit verification and a version tag.
- Treat facts from search snippets or the reconstructed seed as provisional until checked against the page or in-game evidence.
- Keep player-specific state out of shared fact tables. Update only `player/ryan-save-state.json` (or a future player-state database) when Ryan reports progress.
- Never invent a medal number, tablet location, shop inventory, drop rate, skill rank, or missable window.

## Working method

For each ingestion batch:

1. Register or refresh the source in `data/seed/sources.json`.
2. Extract atomic claims with stable IDs, scope, locator, and confidence.
3. Normalize entities and relationships without deleting source-specific nuance.
4. Run conflict detection against existing claims for the same subject / predicate / scope.
5. Add or update checkpoint gates (`available_from`, `unavailable_after`, prerequisites).
6. Rebuild the database and run the tests.
7. Update `INGEST_STATUS.md` with counts, coverage, unresolved conflicts, and the next batch.
8. Commit a meaningful checkpoint when working in a Git repository.

Prefer small, reviewable ingestion batches over a single opaque scrape.

## Answer contract

When answering a playthrough question, retrieve all of the following before synthesizing:

- current player checkpoint and party state;
- open missables and upcoming points of no return;
- collectible / achievement obligations at or before the checkpoint;
- equipment and shops currently accessible;
- vocation prerequisites and current mastery;
- relevant farming opportunities;
- conflicts, confidence, and source freshness.

Lead with a stop warning if advancing could lose content. Otherwise provide, in order: immediate actions, recommended party / gear / vocations, optional grind ceiling, and the safe advancement condition. Cite sources by title and URL.

## Quality gates

Before considering a batch complete:

- `python scripts/build_kb.py` succeeds from a clean generated database;
- `python -m unittest discover -s tests -v` passes;
- every seeded claim references a registered source;
- every relationship references known entities;
- unresolved conflicts are visible, never overwritten;
- generated artifacts are reproducible from committed files;
- no full guide copy or large copyrighted passage was added.

## Change boundaries

- Preserve existing IDs once published; use aliases for corrected names.
- Migrate schema forward; do not discard user progress.
- Do not modify Ryan's state based on inference. Record `unknown` and ask when it materially affects advice.
- Do not commit credentials, cookies, downloaded HTML containing personal data, or proprietary access tokens.

