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
  "advice":[{"id":"advice_id","type":"boss","subject":"Glowering Inferno","text":"Use …","goal":"immediate_power","decision_group":"strongest_now","applicability":{"difficulty":"Normal"},"tradeoff":null,"confidence":"high","verification_status":"source_checked","source":{"id":"source_id","title":"Boss guide","url":"https://example.com","locator":"Boss Strategy > Tips"}}],
  "medals":[{"number":10,"location":"Burnmount","detail":"Chest …","found":false}],
  "monsters":[{"id":"monster_010","ordinal":10,"name":"Example","location":"Burnmount","drop":null,"defeated":false}],
  "safe_condition":"All required actions complete.",
  "sources":[{"id":"source_id","title":"Source title","url":"https://example.com","locator":"Heading > row"}]
}
```

Advice `goal` remains the source recommendation classification: `completion_safe`, `immediate_power`, or `both`. `decision_group` is presentation-only: grind advice becomes `optional_grind`; other `completion_safe`/`both` advice becomes `completion_safe`; remaining advice becomes `strongest_now`. The browser keeps STOP first and the safe advancement condition last. Stop warnings must contain only verified irreversible/time-sensitive warnings.

Every advice row retains its native `applicability` object. `tradeoff` mirrors only the explicitly stored `applicability.tradeoff` value and remains null when none was sourced; the server does not manufacture one. Direct source, locator, confidence, and verification status accompany the recommendation. The browser keeps these details collapsed under “When, tradeoff & source” to preserve the minimal-reading walkthrough.

`saved_state_applicability` annotates—but never filters—each recommendation with `status: satisfied|unmet|unknown` and a concise reason. Evaluation is conservative: `requires.mini_medals` uses an explicit total, or can be satisfied by enough explicitly numbered medals; a lower numbered-medal count without a reported total stays unknown, and inconsistent count records cannot produce an unmet result. A top-level normalized `vocation` is satisfied only by an explicitly current/secondary or mastered vocation. Missing mastery is not treated as false, unsupported requirements stay unknown, and raw applicability/provenance remain unchanged. To keep the walkthrough terse, the browser omits the state badge when a recommendation has no supported saved-state gate.

Checkpoint detail returns STOP obligations twice by design: `stop_warnings` is a
plain alert summary, while `stop_actions` contains stable IDs, concise subjects,
actions, and progress metadata so the interactive walkthrough can explicitly clear
the warning. STOP actions render before normal actions. Normal actions use their
sourced subject as the title and mark only the first open row with `is_next: true`.
Mini Medal rows include `timing: now|backtrack|later`; later-gated rows include their
availability gate and must not render as current checkboxes. The browser keeps them
in a collapsed “Later” reference section.

`advancement_readiness` summarizes only structured evidence: open STOPs, open
100%-required obligations, optional actions, unrecorded currently available medals,
whether the viewed checkpoint is the explicitly saved checkpoint, and the next
checkpoint. Status is `blocked_by_stop`, `required_actions_open`, or
`manual_confirmation`. Even `manual_confirmation` never asserts that prose story
conditions are complete: `safe_condition_requires_player_confirmation` remains true.
The browser enables “Confirm and set next current” only for the saved checkpoint when
no structured blocker remains. Clicking it is the player's explicit confirmation;
the guide never advances automatically. Each nonzero ledger gap is a large navigation
button that opens the matching collapsed ledger, focuses its summary, and scrolls it
below the sticky phone controls. These buttons never mutate progress. Browsing
Next/Previous does not change state.

Checkpoint detail also includes `tablet_fragments` available from that checkpoint.
Rows carry the stable fragment ID and ordinal, tablet/color, location/detail,
time period, explicit `found` state, cutoff when one is published, and full source
provenance. They use the same validated `PATCH /api/tablets/{fragment_id}` mutation
as the Tablets registry, so both views remain synchronized. Missing fragment state
is displayed as unchecked and is never inferred from story progress. Advancement
readiness reports the unrecorded checkpoint-fragment count without independently
declaring the prose safe condition complete or blocked.

`checkpoint_items` groups finite acquisition paths for Heroic Hoarder-required items
whose route first becomes available at the viewed checkpoint. Each canonical item
appears once with explicit `obtained` state and one or more route choices carrying
method, location, time period, free/unknown cost, cutoff, confidence, verification,
and source provenance. The checkpoint checkbox reuses the validated
`PATCH /api/items/{item_id}` ledger used by the Items registry; acquiring any listed
copy satisfies the item identity, but the API does not infer which route was used.
Renewable shops, Lucky Panel pools, and drops are not duplicated in this finite
opportunity list. Monster checkboxes likewise reuse the Monster registry ledger;
completed encounters disappear from the checkpoint's remaining-monster list.

Lucky Panel item routes inherit the independently corroborated system-wide zero
entry cost when their pool row has no narrower cost. This proves free entry, not a
free guaranteed item. Published 0/1/50/100 selection cells remain single-source raw
weights; no percentage or expected-value calculation is exposed without a denominator
and draw algorithm.

`checkpoint_achievements` distinguishes `due_here` from `tracking_starts`.
`due_here` means the normalized completion checkpoint matches the viewed checkpoint
and renders a checkbox backed by the same validated Achievements-registry ledger.
`tracking_starts` means a counter can begin at this checkpoint but has no exact
completion checkpoint; these rows remain collapsed, read-only reminders with
state-aware dependency progress. The guide never marks either class unlocked from
story position. Each row preserves platform scope, grade, requirement progress,
confidence, verification, and provenance. Advancement readiness reports unrecorded
due achievements but does not independently infer that the exit condition is met.

### `GET /api/progress`

Returns display totals plus explicit editor state: `saved_checkpoint`, raw `mini_medal_count` (nullable), and `party`. Member rows expose only recorded `level`, `primary_vocation`, `secondary_vocation`, and `mastered_vocations`; null values remain unknown. Equipment and party presence are not inferred.

`ledger_audit` covers medals, required items, monsters, tablet fragments, Monster
Hearts, missables, vocations, and achievements. Every ledger reports `status`,
nullable `known_count`, canonical `total`, and `unknown_state_ids`; missables also
separate completed and missed counts. Empty legacy identity arrays remain unknown
rather than becoming false zero. The optional Monster Heart ledger is the exception:
once explicitly created, an empty list means zero recorded Hearts.

Each counter may be a string, `{ "display": "x / y" }`, or `null`. `open_work` is ordered by current relevance.

```json
{"actions":{"display":"12 open"},"medals":null,"items":{"display":"20 / 353"},"monsters":null,"vocations":null,"achievements":null,"open_work":[{"title":"Mini Medals","detail":"Count unknown"}]}
```

### `GET /api/conflicts`

```json
[{"id":"conflict_id","subject":"item:tempest shield","predicate":"precise location","status":"unresolved","detection_method":"manual","rationale":null,"claims":[{"id":"claim_a","value":{"location":"A"},"scope":{"game":"DQ7 Reimagined"},"confidence":"high","verification_status":"source_checked","locator":"Heading > row","source":{"title":"Guide A","url":"https://example.com/a","updated_at":"2026-02-19","retrieved_at":"2026-08-25"}},{"id":"claim_b","value":{"location":"B"},"scope":{"game":"DQ7 Reimagined"},"confidence":"high","verification_status":"source_checked","locator":"Heading > row","source":{"title":"Guide B","url":"https://example.com/b","updated_at":null,"retrieved_at":"2026-08-25"}}]}]
```

The conflict view presents both claims symmetrically with their independent scopes, confidence, verification status, source, locator, and freshness dates. `updated_at: null` is displayed as unknown. An unresolved badge, `required_evidence`, and “No resolution is implied” remain visible; value order does not indicate preference. With `include_resolved=1`, resolved rows expose `resolution_claim_id`, the recorded adjudication rationale, and `resolution_evidence` containing every sourced claim with the winning normalized value. When one conflicting claim is the resolution, it has `is_resolution: true`. When two independent publishers instead agree on a third complete value, `resolution_is_external` is true and a separate consensus card displays the distinct corroborating publishers; both losing pair claims remain unchanged and visible. The build rejects an equipment consensus unless matching claims come from at least two distinct publishers.

The server validates the knowledge database before binding its listening socket.
Missing, unreadable, corrupt, empty, or wrong-schema databases fail startup with a
rebuild instruction, so `GET /api/health` cannot report ready while domain APIs are
unable to query the required schema.

`HEAD /api/health` returns the same status and representation headers as the GET
health check with no body. In LAN mode it requires the same pairing cookie, query
token, or `X-DQ7-Pair` authorization; an unpaired probe receives `401`, never a
public readiness signal.

The Stella/Stellar Fan spelling remains unresolved because the current direct evidence consists of conflicting guide text, not a legible English in-game name capture. Both spellings resolve to the same item detail/search result through the sourced alias, while the canonical display remains `Stellar Fan` without claiming that this adjudicates the conflict. Resolution requires a current-version English Item List, inventory, shop, or acquisition-result capture with the complete name visible.

Tempest Shield is intentionally absent from the conflict registry. Its Present Sanctum of the Cirrus treasure and later Ventus Tower 2F chest are independent finite acquisition rows, not competing values: Game8's dedicated item/map tables support the Sanctum route, and both Game8's Wind Spirit walkthrough and RPG Site support Ventus Tower. Item detail therefore returns both chest routes with their separate checkpoint gates.

## Domain registries

`GET /api/evidence-gaps` returns the maintained residual research audit. Every row
is explicitly tiered as `single_source`, `unsupported`, or
`corroborated_but_unresolved`, carries its last-audited date and exact acceptance
condition, and expands every registered `source_id` to current source metadata. Two
guide texts do not resolve a row whose acceptance condition requires direct UI or
save-tested evidence. `source_count` and `publisher_count` report all audited pages;
`supporting_claim_source_count` and `supporting_claim_publisher_count` report only
locator-linked atomic claims. The latter publisher count exclusively determines
single- versus multi-publisher tiering.

The phone view renders `verification_tier` as evidence strength (`1 claim publisher`, `No
publishable source`, or `N claim publishers · still unresolved`) separately from the
row's residual `status`. Cards start collapsed; the open-question label remains in
the summary, while expansion shows the acceptance condition, supporting-claim URLs
and locators, separately labelled additional audited pages, freshness, and audit
date. Corroboration is never presented as resolution.

The endpoint separately returns the complete unresolved-conflict count grouped by
predicate and whole-registry source freshness totals. The five priority research
gaps are therefore never presented as the entire conflict or source-maintenance
inventory.

The first-class domain routes call:

- `GET /api/items`
- `GET /api/vocations`
- `GET /api/monsters`
- `GET /api/monster-hearts`
- `GET /api/missables`
- `GET /api/farms`
- `GET /api/sources`
- `GET /api/seeds`

`GET /api/vocations/{id-or-name}` includes `rank_costs`, a two-source
`progression` profile, numeric stat modifiers, and `unlock_progress`. `groups`
preserves the sourced direct rule (`all_of` or `any_n_of`), required count,
candidate vocation IDs/names, and provenance. `party_progress` evaluates only
explicit `vocation_mastery: true` records: a satisfied threshold is `satisfied`,
while absent records remain `unknown`, never unmet.
`needed_if_unknowns_are_unmastered` is a conditional planning count, not an
assertion about saved state. Progression profiles distinguish full point ladders,
story-granted personal vocations, and Wolf Boy's story-granted early ranks plus
the verified 70/80-point final ranks.

`unlock_progress.recursive_plans` expands the complete sourced prerequisite DAG for
each party member. Every nested group retains `all_of`/`any_n_of`, its threshold,
candidate tree, direct provenance, explicit mastery status, and character-exclusive
eligibility. `next_options` contains base vocations or higher vocations whose direct
requirements are explicitly satisfied; it is an unranked planning menu, not a
shortest-cost recommendation. Missing mastery remains unknown, alternative branches
are never silently selected. Each next option carries its verified progression
profile; absent player mastery remains unknown.
- `GET /api/medals`
- `GET /api/tablets`
- `GET /api/achievements`

Each returns an object containing `items`, `vocations`, `monsters`, `medals`, `fragments`, or `achievements`. Paginated registries also return `total`, `limit`, and `offset` (achievement paging metadata is under `page`). The browser normalizes persisted IDs and progress fields for display.

Checkpoint `actions` and `stop_actions` include their precise source object.
`GET /api/farms?through_checkpoint={checkpoint_id}` excludes routes gated after
that checkpoint and labels returned rows `available_by_checkpoint`.

Monster Hearts return `{total, limit, offset, ownership_tracking, owned_count, unknown_state_ids, hearts}` and support `GET /api/monster-hearts/{heart_id}`. Detail includes effect, normalized availability where known, confidence, verification status, source URL, locator, `owned`, and `ownership_status`. `owned: null` / `ownership_tracking: "unknown"` means Ryan has never reported Heart inventory; it is not false or zero. Only canonical registry IDs contribute to `owned_count`; stale or foreign saved IDs remain visible in `unknown_state_ids`.

The browser derives Heart categories from `available_now`: `true` is available,
`false` is later, and null is unknown. A future checkpoint gate alone never labels
a Heart available at the current checkpoint.

Heart checkboxes use `PATCH /api/monster-hearts/{heart_id}` with `{ "completed": true|false }`. The first explicit change creates `completion.monster_hearts_owned`; subsequent changes are reversible and accept only canonical IDs from the 46-Heart registry. Checkpoint or route availability never implies ownership.

Heart detail also returns `routes`, reusing current-version item acquisition rows with their checkpoint, time period, method, supply, source, and locator. When the Heart row has no native gate, the earliest linked route supplies the displayed gate and `availability_status: "route_normalized"`; it does not overwrite the underlying effect claim. Drop routes return `drop_rate: null` and `drop_rate_status: "unknown"` because no numeric rate is stored. Acquisition DLC scope is likewise null/unknown unless directly sourced. Name mismatches or unlinked Hearts remain route-free rather than being guessed.

Missables return `{total, limit, offset, missables}` and support `GET /api/missables/{missable_id}`. `window_status` is `verified` only when both boundaries and direct source verification are present; otherwise it is `unresolved`. `window_gap_reason` explains a missing exact boundary and `stop_warning_eligible` is true only when the verified record links a normalized `stop_before_advancing` obligation. Every row carries its checkpoint, linked obligation, direct source locator, and explicit `progress_status: completed|missed|unknown`; unknown cutoffs remain null instead of being inferred. The browser must not promote unresolved rows into STOP warnings.

Missable checkboxes use `PATCH /api/missables/{missable_id}` with
`{"completed":true|false}`. This records/removes the ID in
`completion.missables_completed` and synchronizes only its explicitly linked
checkpoint obligation. It never marks story progress, unrelated obligations, or an
unknown-cutoff STOP. `missables_missed` remains an explicit external-state field;
completing a record removes the same ID from that list, but the browser does not infer
or automatically record a missed outcome. Checkpoint missable rows use the same
ledger as the registry and show unresolved windows as “Cutoff unknown · not a STOP.”

Farms return `{total, limit, offset, farms}` and support `GET /api/farms/{farming_id}`. Target, location, time period, checkpoint gate, qualitative frequency, confidence, and direct locator are sourced facts. Numeric rates remain `numeric_unpublished`. Strategy text is separately sourced and labeled `attributed_strategy`, not canonical fact. Farms are read-only and never mutate player progress.

The browser requests farms through the checkpoint currently being viewed and
invalidates its farm cache whenever that checkpoint changes.

`farm_type: "proficiency"` identifies the cp013 Highendreigh Tower route after Moonlighting. Its factual gate and guarantee of proficiency per completed battle are separate from Game8's attributed recommendation to combine proficiency, EXP, gold, and possible Metal Slime encounters there. No proficiency-per-time rate is stored or implied.

`farm_type: "gold"` identifies the cp009 Pilgrim's Rest Lucky Panel resale route. The Version 1 checkpoint gate and three-rewards-per-day rule are factual route data; the capture/record, sell, inn-reset loop is attributed Game8 strategy. No gold-per-time or expected prize value is stored or implied.

There is intentionally no `farm_type: "hearts"` yet. Current-version sources verify finite Vicious Heart rewards and identify Grody Gumdrops as a Heart source in Another World, but do not explicitly verify that its encounter or Heart reward repeats. Clients must not present those acquisition rows as a repeatable farm until direct respawn or rematch evidence is registered.

Sources return `{total, limit, offset, sources, publishers}` and support `GET /api/sources/{source_id}`. Search covers title, publisher, role, class, status, and ID. Exact filters are `role`, `publisher`, `retrieval_band`, and `update_date_status`. Retrieval bands are `within_180_days`, `over_180_days`, or `unknown`; they measure only days since this project retrieved the page. They do not assert that page content or dependent claims are current. Missing publication/update dates remain null and display as unknown. The registry is read-only.

`GET /api/moonlighting` (also embedded in vocation list/detail responses) returns the direct unlock, mechanics, and legal-pairing claims with full provenance. cp012 after Aishe is the normalized earliest checkpoint. The resolved process uses the Shrine of Mysteries trigger followed by Alltrades Abbey activation. Published behavior covers the Career Sphere tab, simultaneous learning, and access to both sets of skills/stat bonuses. Two official current-version sources establish `pairing_summary`: any two distinct vocations available to that character, while normal unlock prerequisites and character-exclusive availability still apply. Point splitting remains unknown. Attributed pair suggestions remain recommendations rather than mechanic claims.

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

Achievement list and detail rows include `dependency_progress` with `status`
(`unknown`, `partial`, `target_met`, or `complete`), `known_count`,
`required_count`, `basis`, and `reason`. Registry counts use only explicitly saved
identities. Empty item, monster, tablet, Vicious-obligation, and vocation trackers
remain `unknown`, not zero; an explicit `mini_medal_count: 0` is an exact zero.
`target_met` means the dependency counter is sufficient but the achievement unlock
has not itself been recorded. This distinction applies to Heroic Hoarder, Monster
List, Vicious encounters, tablets, vocations, and medals.

Missables use an explicit three-state result: `unknown`, `completed`, or `missed`.
Recording `missed` requires destructive confirmation, clears any contradictory
completed state, and blocks 100% advancement with recovery guidance. Changing the
result to completed or unknown is reversible; no missable result is inferred.

Achievement details retain every counter-semantic claim and every resolved or
unresolved counter conflict. A resolved row includes its `resolution` claim and
rationale; the browser displays the winning rule without hiding the losing claim.
Massively Minted is resolved to lifetime total gold acquired from four independent
current-version publishers. The exact metal-family roster is independently
corroborated as Metal Slime, Liquid Metal Slime, Metal King Slime, and Platinum
King; quick-win inclusion remains a separate unknown.
Straight to the Point's counter unit is independently corroborated as one successful
field-attack instant-kill event that avoids the battle screen. Semantic rows expose
an exact-value publisher/source evidence tier. Whether that event also increments
Field Day, Monster Masher, or Metal Mangler—and whether counters persist across
save slots, New Game, demo transfer, or reset—remains explicitly unknown.

`GET /api/equipment` is an equipment-readiness and comparison endpoint with
validated accessory and standard-slot editors.
It includes independently corroborated `mechanics` rows for the two accessory
slots and the one-slot cost of each equipped Monster Heart. `compatibility_coverage`
reports a complete 311-row canonical weapon/shield/head/torso/accessory/Heart audit separately. Only rows where at
least two independent publishers agree are expanded into six explicit character
decisions. `compatibility_audits` retains every agreeing,
disputed, and single-source row with both character lists and exact source
locators. Verified slot mechanics and partial matrix coverage must not be
mistaken for duplicate-effect rules. `PATCH /api/equipment/accessories/{character}/{accessory_1|accessory_2}`
accepts `{ "item_id": canonical_id_or_null }`. It permits only explicitly owned,
verified-compatible canonical accessories, treats Hearts as accessories, enforces
global exact-copy allocation, and clears a slot back to unknown with `null`. The
same ID in both slots additionally requires an exact total of at least two and
two-publisher item-specific same-item legality; this is currently verified only
for Rabbit Tail and Meteorite Bracer. Monster Heart duplicates remain unsupported.
It returns `accessory_editor_supported: true` and derives
`non_accessory_editor_supported` from complete two-publisher compatibility and
slot-rule coverage. `editor_supported` is true when both editor paths are safe; a
client must honor these flags rather than assuming support. The response also
includes the exact normalization `gaps`, each party
member's raw explicitly recorded equipment with an `unvalidated_record` warning,
and gear recommendations for the saved checkpoint. Recommendation rows resolve
canonical item IDs and nominal category slots, route availability, explicit
ownership, the recorded-value comparison, provenance, and an attributed
compatibility status and basis.

Route availability separates the checkpoint window from the one independently
state-evaluable acquisition gate: Mini Medal thresholds. `route_available` means
at least one open route has no Medal threshold or its threshold is explicitly
satisfied. An open route with an unknown Medal count is
`route_prerequisite_unconfirmed`; it is withheld from the phone's “Get now”
loadout list and shown only as a short gated-recommendation notice. Keys, events,
bosses, items, arena conditions, containers, rooms, ranks, and pools remain
visible route conditions or metadata; their normalized earliest checkpoint—not
untracked save-state inference—controls when the route can be pursued. Each row
also exposes an authoritative `actionable_route`; the phone never assumes the
first route in the full collection is current.

`PATCH /api/equipment/slots/{character}/{weapon|shield|helmet|armour}` accepts
`{ "item_id": canonical_id_or_null }` when `non_accessory_editor_supported` is
true. It requires explicit ownership, the matching canonical item category,
global copy availability, and two-publisher character compatibility. `null`
reversibly clears the recorded slot to unknown. These guards are enforced by the
server even if a client ignores the capability flag.

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

Item ownership and quantity are distinct. `completion.items_obtained` records identity for completion; optional `completion.item_quantities` records an exact non-negative copy total. Missing means unknown, not zero. A positive exact total adds identity, while exact zero removes it. Clearing a total restores unknown quantity and normally retains identity.

```text
PATCH /api/items/{item_id}/quantity {"quantity":2}
PATCH /api/items/{item_id}/quantity {"quantity":null}
```

A reversible client undo may send `{"quantity":null,"obtained":false}` when the item was not obtained before the edit. Equipment allocation is checked globally. Unknown quantity supports at most one explicitly owned copy; exact totals cap all allocations. Using the same accessory ID in both slots additionally requires at least two exact copies and two independent publishers explicitly supporting that item's same-item legality. This is item-specific and does not establish a universal duplicate-accessory or Monster Heart rule.

The Progress screen also reuses the allowlisted command endpoint for explicit values:

```json
{"command":"medal-count","values":[7]}
{"command":"vocation-mastered","values":["Hero","vocation_warrior"]}
{"command":"vocation-undo","values":["Hero","vocation_warrior"]}
{"command":"party-level","values":["Hero",17]}
{"command":"party-level","values":["Hero","unknown"]}
{"command":"party-vocations","values":["Hero","vocation_warrior","vocation_priest"]}
{"command":"party-vocations","values":["Hero","unknown","unknown"]}
```

The server validates checkpoint IDs, positive integer levels, party-member names, vocation IDs, and character-exclusive vocation eligibility. `unknown` explicitly restores nullable level/current/secondary vocation fields; the browser never fills them from checkpoint or mastery. Explicit Mini Medal records are reversible from the walkthrough and medal catalog. Equipment editing remains disabled until canonical slot and character-compatibility validation exists. Selecting a saved checkpoint never marks actions, collectibles, monsters, or other checkpoints complete. The dashboard distinguishes an explicitly saved checkpoint from the cp001 guide preview used when state is unknown.

Return `204 No Content` or the updated progress object. Reject unknown IDs with `404` and invalid shapes with `400`. The bundled threaded server serializes state mutations and atomically replaces the state file, so rapid independent checkbox writes cannot overwrite one another and readers never observe partial JSON. This is process-local coordination, not distributed versioning; external multi-process writers still require their own coordination.

## Serving

Serve `web/index.html` for `/` and the three assets with UTF-8 MIME types. The API should derive responses from the committed seed/database plus the explicitly selected player-state file. Source URLs and precise locators remain required in checkpoint responses.
