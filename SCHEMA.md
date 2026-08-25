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
