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
  "advice":[{"id":"advice_id","type":"boss","subject":"Glowering Inferno","text":"Use …","goal":"immediate_power"}],
  "medals":[{"number":10,"location":"Burnmount","detail":"Chest …","found":false}],
  "monsters":[{"id":"monster_010","ordinal":10,"name":"Example","location":"Burnmount","drop":null,"defeated":false}],
  "safe_condition":"All required actions complete.",
  "sources":[{"id":"source_id","title":"Source title","url":"https://example.com","locator":"Heading > row"}]
}
```

Advice `goal` is `completion_safe`, `immediate_power`, or `both`. Stop warnings must contain only verified irreversible/time-sensitive warnings.

### `GET /api/progress`

Each counter may be a string, `{ "display": "x / y" }`, or `null`. `open_work` is ordered by current relevance.

```json
{"actions":{"display":"12 open"},"medals":null,"items":{"display":"20 / 353"},"monsters":null,"vocations":null,"achievements":null,"open_work":[{"title":"Mini Medals","detail":"Count unknown"}]}
```

### `GET /api/conflicts`

```json
[{"id":"conflict_id","subject":"Tempest Shield location","summary":"Sources disagree …","status":"unresolved"}]
```

## Writes

### `PATCH /api/progress`

Records one explicit player action. It must never infer adjacent completion.

```json
{"kind":"action","id":"obl_id","completed":true}
{"kind":"medal","id":10,"completed":true}
{"kind":"monster","id":"monster_010","completed":true}
```

Return `204 No Content` or the updated progress object. Reject unknown IDs with `404`, invalid shapes with `400`, and concurrent stale writes with `409` if versioning is implemented.

## Serving

Serve `web/index.html` for `/` and the three assets with UTF-8 MIME types. The API should derive responses from the committed seed/database plus the explicitly selected player-state file. Source URLs and precise locators remain required in checkpoint responses.
