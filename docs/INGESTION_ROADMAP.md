# Ingestion roadmap

Each phase has an acceptance gate. Do not mark a phase complete because pages were visited; mark it complete when normalized records, provenance, integrity checks, and representative queries all pass.

## Phase 0 — Handoff foundation (complete)

Deliverables:

- reproducible SQLite + FTS5 build;
- source, claim, graph, conflict, player-state, and domain schemas;
- 20-source registry;
- reconstructed seed for known v0.1 coverage;
- operating policy, status ledger, tests, and kickoff prompt.

Gate: clean build, passing tests, and a useful `alltrades vocation` query.

## Phase 1 — Chronological completion spine

Ingest the RPG Site walkthrough as atomic checkpoints, not copied prose.

Deliverables:

- stable checkpoint IDs from Prologue through postgame;
- entry prerequisites, exit conditions, bosses, Past / Present scope;
- items, fragments, medals, monsters, quests, and achievements attached to checkpoints;
- `stop_before_advancing` rules for time-sensitive content;
- all 100 Mini Medal locations and all 19 rewards.

Acceptance queries:

- “I am leaving Emberdale; what remains?”
- “Which medals are obtainable before Alltrades?”
- “What becomes unavailable if I continue from this checkpoint?”

Gate: every chronological row has a source and locator; medal numbers are unique 1–100; checkpoint ordering has no orphan nodes.

## Phase 2 — Heroic Hoarder and acquisition matrix

Deliverables:

- every item in the in-game list by category;
- all acquisition methods: shop, chest, drop, reward, Lucky Panel, arena, medal exchange, story, DLC;
- earliest checkpoint and alternate later sources;
- exclusive / finite / renewable flags;
- shop inventories with Past / Present and price;
- complete Lucky Panel version / rank / chest matrix.

Acceptance queries:

- “Which Heroic Hoarder items are exclusive to Lucky Panel?”
- “Should I buy this now or can I obtain it free later?”
- “What is the earliest available weapon upgrade for Maribel?”

Gate: every item has at least one acquisition path or an explicit unresolved gap; exclusivity claims have strong evidence.

## Phase 3 — Vocation and skill engine

Deliverables:

- all vocation ranks, skills, spells, stats, perks, and Let Loose abilities;
- complete prerequisite expressions (`all_of`, `any_n_of`);
- Moonlighting legality and unlock checkpoint;
- proficiency farming, seed-of-proficiency sources, and route costs;
- character vocation recommendations preserved as attributed strategies;
- derived shortest mastery paths and role coverage.

Acceptance queries:

- “Shortest route from this character's mastery to Champion?”
- “What can I Moonlight now without delaying Hero?”
- “Which rank unlocks the skill I need for the next boss?”

Gate: each learned skill has vocation, rank, effect, and source; prerequisite graph is cycle-free.

## Phase 4 — Equipment, combat, monsters, and farming

Deliverables:

- weapons, armour, shields, helmets, accessories, usability, stats, and effects;
- monsters, locations, drops, rare / menacing state, experience and gold;
- all Monster Hearts, effects, acquisition, and build roles;
- boss profiles with resistances and strategy evidence;
- EXP, gold, proficiency, seed, heart, and item farms with unlock gates;
- patch / difficulty / DLC assumptions.

Acceptance queries:

- “Strongest equipment obtainable at this checkpoint?”
- “Best farm now for levels plus vocation proficiency?”
- “What Heart helps this boss and where can I obtain it?”

Gate: recommendation output can explain why an option is legal now, where it comes from, and what assumption makes it best.

## Phase 5 — Completion ledger and player-state integration

Deliverables:

- all achievements / trophies and their dependencies;
- tablets, optional islands, monster list, arena, postgame, and DLC scopes;
- player-state migrations and validation;
- state update command or guided workflow;
- derived remaining-work and stop-warning queries.

Acceptance queries:

- “What do I still need for 100%?”
- “Can I safely finish this chapter?”
- “Given my save, what is my strongest safe party now?”

Gate: recommendations are reproducible from committed game data plus the player's state, with unknown state explicitly surfaced.

## Phase 6 — Retrieval quality and maintenance

Deliverables:

- golden question set and expected evidence bundles;
- ranking that favors checkpoint scope, current patch, confidence, and source diversity;
- conflict dashboard and stale-source report;
- incremental refresh tooling;
- optional embeddings, if they demonstrably improve retrieval.

Gate: golden questions return relevant evidence with no unscoped legacy-version leakage and no hidden unresolved conflict.

