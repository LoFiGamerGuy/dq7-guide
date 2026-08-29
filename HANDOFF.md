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

The browser exposes first-class item, vocation, monster, Monster Heart, Seed, missable, farm, medal, tablet, achievement, source, and conflict registries alongside the walkthrough. Reads are state-aware and paginated; supported writes reuse the validated player-progress layer. Monster Heart ownership has a dedicated canonical-ID ledger: absence remains unknown, the first explicit checkbox starts tracking, and every change is reversible. Equipment compatibility verifies all 311 canonical rows through two-publisher agreement; no normalized row is disputed or single-source, while every disagreeing source claim remains visible. The reversible editor requires explicit ownership, the sourced slot layout, the matching item category, and verified character compatibility before equipping a weapon, shield, helmet, armour, or one of two distinct accessories. The published `Meowgiican Heart` typo redirects to `Meowgician Heart`, leaving all 74 canonical accessories verified. Checkpoint selection is explicit, and the responsive UI includes keyboard focus, high-contrast support, loading/retry states, and a default hide-completed mode.

Current reproducible headline counts are tracked in `INGEST_STATUS.md`. The database contains 355 shared items (353 in the registered Heroic Hoarder matrix), all 46 Monster Heart identities/effects, 18 fixed Seed effects and one repeatable reward rule, 11 checkpoint-gated farms with separate fact/strategy provenance, 7 sourced missable records, 14 Lucky Panel pools with 302 rewards, 100 Mini Medals, 71 tablet fragments, 61 achievements, and 26 complete vocation skill/perk ladders. Meowgician Heart has a direct finite Vicious Meowgician route at cp005; Metal Slime and Gold Golem have explicit DLC notes. Dragonlord, Malroth, and Zoma have independently corroborated DLC Battle Arena thresholds and are gated from cp020 after the Buccanham Past storyline. All 100 Mini Medals have independent direct walkthrough evidence. Dedicated current-version pages and cross-publisher rank tables resolve every standard-matrix identity variant without changing the 353-item Heroic matrix; RPG Site's `Shell Shield` wording is retained as a source-error alias for canonical Scale Shield. Direct evidence adds finite free alternatives throughout the early and midgame while retaining unknown exact containers. Vocation details expose sourced unlock rules and state-aware per-member progress without inferring missing mastery or numeric costs. The browser provides current-equipment comparison and exposes independently corroborated one-each weapon/shield/head/torso, two-accessory-slot, and Monster-Heart slot-use rules. Character legality is complete. Rabbit Tail alone now has two-publisher evidence that two copies are legal and stack qualitatively; other identical accessories, Monster Hearts, and the numeric formula/cap remain constrained unknowns. All 33 walkthrough checkpoints have direct RPG Site section-range locators; their `seed_partial` status remains because provenance completeness does not mean the guide content and optimization layers are complete.

Combat/optimization handoff: 115 checkpoint advice rows cover every checkpoint except the non-combat ending victory lap, 11 farming routes have exact gates, all 26 vocation skill/perk ladders and qualitative non-default modifiers are normalized, and all 333 monsters have at least one gated encounter. Twenty-one formerly missing routes have two independent current-version sources. Scarewell's fixed Past route is now corroborated; its town-reset method remains explicitly PS5-scoped, single-firsthand evidence, and no numeric rate is normalized. Normal-setting field/regular/boss proficiency awards are 1/5/10 with explicit scope, and all 26 vocations have two-source progression profiles with 163 normalized rank-cost cells. Two official sources establish that Moonlighting accepts any two distinct vocations available to the character, including cross-tier pairs; character-exclusive availability still applies. Rabbit Tail farming advice is quantity-guarded and qualitative only. Vicious/strong Heart encounters are independently verified as finite after victory and phone guidance forbids treating them as farms. Do not fill the remaining evidence blocks by inference: numeric farm/drop/encounter rates, a repeatable non-Vicious Heart route, non-Rabbit-Tail duplicate accessories, or Monster Heart duplicate/stacking behavior.

Achievement-counter handoff: all thresholds remain structured, and current sources now distinguish individual monster/metal-monster units, in-battle wins, successful pre-battle field attacks, no-combat quick wins, and party-wide Let Loose aggregation at their actual evidence strengths. Massively Minted is deliberately conflicted: one current guide requires holding 300,000 gold simultaneously while another says lifetime gross acquisition survives spending. The phone/source audit lists the remaining quick-win overlaps, metal-family membership, and save/reset scope rather than presenting any of them as settled.
The achievement detail turns that visible conflict into a conservative, explicitly
synthesized action: bank 300,000 gold at once before spending it. This satisfies
either registered condition without resolving the counter semantics or creating a
new fact claim.

Roamer and Highendreigh Metal Slime companion-encounter routes now have narrow
two-publisher phone evidence, as do the 65/80/100 Mini Medal rewards and Cyclops
Heart's +30% critical-damage effect. Encounter rates, numeric grind ceilings,
checkpoint medal availability assumptions, universal wearer rankings, and Heart
repeatability remain explicitly unverified. Highendreigh Whistle use and the
Neoseeker author's 4F observation are displayed only as source-specific extras.

Late fixed-gear cards now independently corroborate Malign Shrine's Sunderbolt
Blade and Dark Robe, Estard Castle's Ultimate-Key gear trio, and Burnmount's
Magma Staff. Keep the Estard teleportal deadline and broader cleanup single-source;
keep Sacred Armour visibly separate from the verified Magma Staff core. These
route checks do not establish permanent missability or best-wearer rankings.

Time Being's shared phone core is limited to group pressure on the Side Winders
and survival while Time Stop disables characters; healer composition, item backup,
resistance, and revival behavior remain attributed extras. Lourgh/Disorder's
Magic Barrier, elemental protection, magic-damage response, and autonomous Kiefer
contribution are independently corroborated. Its encounter chronology is resolved
to Past Exposure Enclosure: Game8's continuous Curious Tablet walkthrough defeats
Lourgh before returning to the Present, matching Eliteguias and cp027. The isolated
Game8 boss page's Present label remains visible as the losing claim.

Lucky Panel entry is independently verified as free. Its single-source numeric selection cells remain raw weights, not probabilities, because no denominator or draw algorithm is published.

The final three unpublished purchase prices are now typed shop inventory:
Dragon Robe (19,000 gold) and Enchanted Armour (21,000 gold) at Rucker Castle
Past, and Pilchard Pie (10 gold) at Pilchard Bay. Exact finite-container
refinements remain separate evidence gaps.

The current-version walkthrough and video audits close all 31 exact-container
residuals. Direct English item-result footage resolves Dragon Shield, Pirate's Hat,
Silk Robe, Steel Helmet, and Knuckledusters to individual containers. A separately
scoped current-version PS5 video with Italian UI resolves Faraday Strength Ring to
the lower/southern drawer of the east-wall bedroom pair; it does not establish an
English item name. Fishnet Stockings is separately resolved to the Present inn
wardrobe.

Six additional power cards now carry two-publisher atomic evidence: Tribulators
healing-item safety, the Present La Bravoure Metal King Slime route and critical
tactic, Luminary/Monster Wrangler/Druid Let Loose mechanics, and first-Orgodemir
phase-one Magic Barrier. Orgodemir phase two deliberately retains the visible
Magic Barrier versus Insulatle recommendation split; vocation role/timing advice
remains labeled as editorial synthesis beyond the verified mechanics.

Four fixed-gear sweep cards now separate two-publisher route cores from their
remaining one-walkthrough extras. Verified pickups cover Ice Shield; Dragon
Claws and Staff of Sentencing; Duplic Hat and Staff of Antimagic; and Silver
Mail, Lightning Staff, and Falcon Blade. Collection advice does not imply a
universal best wearer.

Pirate's Hat is resolved to Buccanham Palace Past: Neoseeker and Eliteguias
independently agree on the 2F bedroom wardrobe pair. Both losing Present conflict
pairs remain visible. Fishnet Stockings is resolved to the Present inn's
right-hand wardrobe: Game8's dedicated Frobisher map agrees with Eliteguias and
GuíasPSN, overriding the isolated Game8 item page's Past label while preserving
that losing claim.

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
