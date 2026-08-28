# Static frontend API contract

The files in this directory are dependency-free and may be served by any static server. They expect JSON endpoints under `/api`. Unknown player progress must be returned as `null`, not inferred as zero.

## Reads

### `GET /api/dashboard`

```json
{"checkpoint":{"id":"cp_004_emberdale","sequence_label":"04 / 33"},"stop_warnings":[],"progress":{"medals":"12 / 100","items":"20 / 353","monsters":"18 / 333"},"next_actions":[{"id":"obl_id","title":"Short title","action":"Terse instruction","completed":false}]}
```

### `GET /api/checkpoints`

Returns ordered checkpoint summaries:

```json
[{"id":"cp_001_prologue","sequence":1,"name":"Prologue / Pilchard Bay"}]
```

### `GET /api/checkpoints/{checkpoint_id}`

```json
{
  "id":"cp_004_emberdale","name":"Emberdale and Burnmount","time_period":"Past","region":"Emberdale",
  "stop_warnings":["Finish the listed finite sweep before advancing."],
  "actions":[{"id":"obl_id","title":"Finite sweep","action":"Collect …","completed":false,"required":true}],
  "advice":[{"id":"advice_id","type":"boss","subject":"Glowering Inferno","text":"Use …","goal":"immediate_power","decision_group":"strongest_now"}],
  "medals":[{"number":10,"location":"Burnmount","detail":"Chest …","found":false}],
  "monsters":[{"id":"monster_010","ordinal":10,"name":"Example","location":"Burnmount","drop":null,"defeated":false}],
  "safe_condition":"All required actions complete.",
  "sources":[{"id":"source_id","title":"Source title","url":"https://example.com","locator":"Heading > row"}]
}
```

Advice `goal` remains the source recommendation classification: `completion_safe`, `immediate_power`, or `both`. `decision_group` is presentation-only: grind advice becomes `optional_grind`; other `completion_safe`/`both` advice becomes `completion_safe`; remaining advice becomes `strongest_now`. The browser keeps STOP first and the safe advancement condition last. Stop warnings must contain only verified irreversible/time-sensitive warnings.

### `GET /api/progress`

Each counter may be a string, `{ "display": "x / y" }`, or `null`. `open_work` is ordered by current relevance.

```json
{"actions":{"display":"12 open"},"medals":null,"items":{"display":"20 / 353"},"monsters":null,"vocations":null,"achievements":null,"open_work":[{"title":"Mini Medals","detail":"Count unknown"}]}
```

### `GET /api/conflicts`

```json
[{"id":"conflict_id","subject":"item:tempest shield","predicate":"precise location","status":"unresolved","detection_method":"manual","rationale":null,"claims":[{"id":"claim_a","value":{"location":"A"},"scope":{"game":"DQ7 Reimagined"},"confidence":"high","verification_status":"source_checked","locator":"Heading > row","source":{"title":"Guide A","url":"https://example.com/a","updated_at":"2026-02-19","retrieved_at":"2026-08-25"}},{"id":"claim_b","value":{"location":"B"},"scope":{"game":"DQ7 Reimagined"},"confidence":"high","verification_status":"source_checked","locator":"Heading > row","source":{"title":"Guide B","url":"https://example.com/b","updated_at":null,"retrieved_at":"2026-08-25"}}]}]
```

The conflict view presents both claims symmetrically with their independent scopes, confidence, verification status, source, locator, and freshness dates. `updated_at: null` is displayed as unknown. An unresolved badge and “No resolution is implied” remain visible; value order does not indicate preference.

## Domain registries

The first-class domain routes call:

- `GET /api/items`
- `GET /api/vocations`
- `GET /api/monsters`
- `GET /api/monster-hearts`
- `GET /api/missables`
- `GET /api/farms`
- `GET /api/sources`
- `GET /api/seeds`
- `GET /api/medals`
- `GET /api/tablets`
- `GET /api/achievements`

Each returns an object containing `items`, `vocations`, `monsters`, `medals`, `fragments`, or `achievements`. Paginated registries also return `total`, `limit`, and `offset` (achievement paging metadata is under `page`). The browser normalizes persisted IDs and progress fields for display.

Monster Hearts return `{total, limit, offset, hearts}` and support `GET /api/monster-hearts/{heart_id}`. Detail includes effect, normalized availability where known, confidence, verification status, source URL, and locator. Hearts are read-only because player state has no dedicated Heart inventory field.

Missables return `{total, limit, offset, missables}` and support `GET /api/missables/{missable_id}`. `window_status` is `verified` only when both boundaries and direct source verification are present; otherwise it is `unresolved`. Every row carries its direct source locator; unknown cutoffs remain null instead of being inferred. The browser must not promote unresolved rows into STOP warnings.

Farms return `{total, limit, offset, farms}` and support `GET /api/farms/{farming_id}`. Target, location, time period, checkpoint gate, qualitative frequency, confidence, and direct locator are sourced facts. Numeric rates remain `numeric_unpublished`. Strategy text is separately sourced and labeled `attributed_strategy`, not canonical fact. Farms are read-only and never mutate player progress.

Sources return `{total, limit, offset, sources, publishers}` and support `GET /api/sources/{source_id}`. Search covers title, publisher, role, class, status, and ID. Exact filters are `role`, `publisher`, `retrieval_band`, and `update_date_status`. Retrieval bands are `within_180_days`, `over_180_days`, or `unknown`; they measure only days since this project retrieved the page. They do not assert that page content or dependent claims are current. Missing publication/update dates remain null and display as unknown. The registry is read-only.

Seeds return `{total, limit, offset, seeds}` and support `GET /api/seeds/{seed_id}`. Effect rows expose the fixed stat increase, standard/Super variant, Reimagined version, DLC scope exactly as stored, confidence, verification, source, and locator. A null DLC scope is displayed as “Not recorded,” not interpreted as included or excluded DLC. Reward-rule rows expose their checkpoint, trigger, quantity, random/fixed selection, and repeatability. When `eligible_items` is null, `eligible_pool_status` is `unknown`; the browser must not infer that every Super Seed belongs to the pool. Search covers names, stats, locations, triggers, and provenance; exact filters are `variant` and `stat`. The registry is read-only.

Domain-specific fields:

```json
{"id":"item_miracle_sword","name":"Miracle Sword","category":"weapons","location":"55 Mini Medals","checkpoint":"cp_015_greenthumb","completed":false}
{"id":"vocation_sage","name":"Sage","category":"intermediate","requirement":"Mage + Priest","summary":"Spell and recovery role"}
{"id":"monster_101","name":"Example","category":"regular","ordinal":101,"location":"Area (Past)","drop":"Item","completed":false}
{"id":63,"number":63,"name":"Mini Medal #63","category":"open","location":"Mountain Path","completed":false}
{"id":"tablet_fragment_001","name":"Fragment 1","category":"fragment","checkpoint":"cp_001_prologue","completed":false,"progress_kind":"tablet"}
{"id":"ach_heroic_hoarder","name":"Heroic Hoarder","category":"completion","requirement":"Obtain all 353 items","completed":false}
```

The Python server derives these endpoints from the generated database and explicitly selected state file. Vocation mastery and whole-tablet status need dedicated workflows and remain read-only in the generic catalog.

## Writes

### `PATCH /api/progress`

Records one explicit player action. It must never infer adjacent completion.

```json
{"kind":"action","id":"obl_id","completed":true}
{"kind":"medal","id":10,"completed":true}
{"kind":"monster","id":"monster_010","completed":true}
```

Items, tablet fragments, achievements, and checkpoint selection use validated resource mutations:

```text
PATCH /api/items/{item_id}             {"completed":true}
PATCH /api/tablets/{fragment_id}       {"completed":true}
PATCH /api/achievements/{achievement_id} {"completed":true}
PATCH /api/checkpoints/{checkpoint_id} {"selected":true}
```

Return `204 No Content` or the updated progress object. Reject unknown IDs with `404`, invalid shapes with `400`, and concurrent stale writes with `409` if versioning is implemented.

## Serving

Serve `web/index.html` for `/` and the three assets with UTF-8 MIME types. The API should derive responses from the committed seed/database plus the explicitly selected player-state file. Source URLs and precise locators remain required in checkpoint responses.
