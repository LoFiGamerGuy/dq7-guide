# KB schema

## Source
`id, publisher, title, url, retrieved, priority, roles`

## Fact
`category, subject, predicate, object, details, source_id, confidence`

## Relation
`subject, predicate, object, source_id`

Examples:
- `Champion --requires_mastery--> Gladiator`
- `55 Mini Medals --unlocks_reward--> Miracle Sword`
- `Recruit Aishe + story progress --enables_event--> Moonlighting activation at Alltrades Abbey`

## RAG chunk
`id, title, original synthesized text, source_ids, tags`

## Player state
Current checkpoint, party levels, active/mastered vocations, equipment, Mini Medals,
achievement progress, item-collection notes, seed inventory, notable items, and preferences.

## Phase 1 chronology

- `checkpoints` stores ordered story regions and safe-exit summaries.
- `checkpoint_obligations` stores atomic completion actions, stop flags, availability windows, and precise provenance.
- `mini_medal_locations` uses the Game8 list/album number as its canonical 1–100 index and stores checkpoint gates, key requirements, and source locators.
- `mini_medal_evidence` preserves independent source locators and source-specific ordinals used to corroborate a normalized medal location.

RPG Site's parenthetical medal numbers represent walkthrough acquisition order. They must be preserved as source-specific chronology rather than written into `mini_medal_locations.medal_number`.
