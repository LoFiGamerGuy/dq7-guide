# Provenance and conflict policy

## Core principle

The database stores **claims with evidence**, not context-free truth. A normalized fact may be promoted to the graph only when its scope and provenance remain traceable.

## Source classes

Use the following evidence classes:

1. `official` — publisher, developer, patch notes, official manual, or official support material.
2. `in_game_observation` — screenshot, save-tested observation, menu entry, or controlled reproduction, including platform and patch.
3. `specialist_guide` — focused, authored guide with clear scope and update date.
4. `guide_wiki` — maintained guide database or walkthrough hub.
5. `community` — forum, video, Steam guide, spreadsheet, or community post.
6. `reconstructed_seed` — record recovered only from the prior task inventory or cached summary.

Source class is not a substitute for relevance. A directly observed current-version fact can outweigh an old official description; an editorial build recommendation cannot prove a mechanic.

## Claim requirements

Every claim must include:

- stable `claim_id`;
- `subject`, `predicate`, and value;
- `source_id` and locator (heading, table row, item number, or timestamp);
- game / edition, platform if relevant, patch if known, and Past / Present scope if relevant;
- `claim_kind`: `fact`, `recommendation`, `strategy`, `estimate`, or `unknown`;
- retrieval or observation date;
- confidence and verification status.

Confidence levels:

- `verified` — confirmed by direct current-version evidence or two independent, compatible high-quality sources.
- `high` — one strong, directly relevant source with no known conflict.
- `medium` — plausible source, but incomplete scope or only indirect corroboration.
- `low` — snippet-only, community-only, reconstructed, stale, or otherwise unverified.

Do not convert confidence into fake precision. If a page says “more common,” do not invent a rate.

## Conflict detection

Potential conflict keys are:

`normalized subject + predicate + game version + platform + patch + time period + checkpoint range`

Different values for the same key require a `conflicts` record unless the values are compatible alternatives or one is explicitly a recommendation.

Common false conflicts to check first:

- Past versus Present;
- pre-patch versus current patch;
- base game versus DLC;
- acquisition route versus exclusive acquisition route;
- earliest availability versus eventual availability;
- fact versus subjective recommendation;
- character-specific versus party-wide advice;
- minimum completion versus collector preference.

## Resolution order

Resolve mechanics and item facts using:

1. controlled in-game observation on the current patch;
2. current official material;
3. agreement between independent specialist sources;
4. the most current directly relevant guide;
5. unresolved, with both claims retained.

For recommendations, do not force a single winner. Preserve each recommendation, list its assumptions, and synthesize by objective (speed, safety, earliest power, no grinding, full optimization, etc.).

Every resolution must contain a short rationale and must not delete the losing claim.

## Freshness

- Record both publication / update date and retrieval date when available.
- Mark dynamic web pages for refresh before large ingestion passes.
- Re-check any claim used in an irreversible warning if it is stale, low-confidence, or contested.
- Patch-sensitive claims must name the patch or explicitly say `patch_unknown`.

## Copyright and retention

- Do not store complete walkthroughs or large copied sections.
- Store atomic facts, normalized tables, original summaries, and only short excerpts needed for evidence or conflict resolution.
- Keep canonical URLs and precise locators so the user can consult the source.
- Raw HTML caches, if temporarily needed, belong outside version control and should be deleted after normalized extraction unless lawfully reusable.

## Player reports

Ryan's direct report is authoritative for **his save state**, not automatically for global game mechanics. Record reported state with a timestamp and `source_type: player_report`. If a report appears inconsistent, preserve it and flag it for confirmation rather than silently changing it.

