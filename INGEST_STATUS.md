# Ingestion status

Status date: 2026-08-28
Package: `0.3.0-phase1`  
Build type: reconstructed seed (see `RECOVERY_MANIFEST.md`)

## Current coverage

| Domain | Seed coverage | Confidence | Next target |
|---|---:|---|---|
| Source registry | 334 high-value pages | High metadata / mixed page freshness | Add official and in-game evidence sources |
| Vocations | 26/26 names; 250 sourced rank skills, 26 Let Loose perks, 7 progression rules, and 220 stat modifiers across all non-default vocations | High for normalized rows | Add directly published numeric modifiers if found; do not infer values from arrows |
| Vocation prerequisites | 10 rule groups / 27 prerequisite edges with per-edge locators | High | Add derived shortest paths and mastery cost |
| Moonlighting | cp012-after-Aishe gate, Career Sphere flow, simultaneous two-vocation learning, and dual skill/stat access normalized | High for published behavior; Alltrades-vs-Shrine activation venue conflict and unpublished restrictions remain open | Resolve venue conflict and legal-pair/skill-retention restrictions from in-game evidence |
| Walkthrough checkpoints | 33 checkpoints; 222 obligations; cp001–cp033 ordered and progress-aware; all 33 have directly verified RPG Site section-range locators | High for chronology and locator provenance; optimization/content depth remains partial | Expand checkpoint-specific optimization without treating locator coverage as content completeness |
| Mini Medal rewards | 19/19 reward thresholds with per-row table locators | High | Cross-check reward stats/effects and exchange availability |
| Mini Medal locations | 100/100 normalized rows with earliest-availability checkpoint gates | 86 cross-source verified; 13 indexed-source checked; 1 Game8-only indexed row | Directly refresh Game8 when accessible and resolve the medal 78 locator conflict |
| Missables / choices | 7/7 direct-source records with precise locators; 5 exact choice/window cutoffs and 2 explicitly unknown cutoffs | High for documented consequences; medium where the source omits a cutoff | Resolve Wooden Doll's branching cutoff and Little Blue Button's story cutoff |
| Heroic Hoarder items | 353/353 identities / 633 acquisition paths; all items have routes; 44 direct monster-drop alternatives normalized for 19 items previously represented only by Lucky Panel routes | High for identities and explicit routes; Stella/Stellar spelling conflict remains visible | Expand remaining alternate free routes and finite-supply evidence |
| Lucky Panel | 14 normalized pools / 223 reward paths; Version 2 Ranks 1/2 link 30/32 and 28/31, while Version 3 Ranks 1–4 link 22/25, 32/36, 29/31, and 21/21 published names | High for normalized rows; entry costs and reward probabilities remain unknown | Resolve name gaps, then complete Version 2 Rank 3 and Version 1 matrices |
| Equipment | 86 ready-for-play gear, boss, grind, vocation, and tactical rows across cp001–cp033 | Medium/High, attributed | Continue direct boss-strategy coverage |
| Farming | 10/10 routes have direct-source locators and checkpoint gates, including cp009 Lucky Panel gold and cp013 Moonlighting proficiency routes; factual locations and attributed tactics are separated | High for routes/gates; numeric encounter, gold-per-time, and proficiency-per-time rates remain unpublished | Add a verified repeatable Heart farm without inventing rates |
| Stat Seeds | 18/18 standard and Super Seed effects normalized; one repeatable postgame random-Super-Seed reward rule | High for fixed effects and one-per-victory reward; eligible random pool remains unknown | Verify the postgame random reward membership without inference |
| Monster Hearts | 46/46 normalized Hearts with sourced effects; 40/46 now surface checkpoint-aware acquisition from existing current-version item routes | High for effects and linked routes; six unlinked names, drop rates, and route DLC scope remain unknown | Resolve remaining name/link gaps from direct pages without inventing rates |
| Achievements | 61/61 identities; 29/29 non-story requirements; explicit player tracking | High for identities and dependency structure; no unresolved registry placeholder remains | Verify monster English-name alignment and remaining counter semantics |
| Tablets / fragments | 20/20 tablets and 71/71 numbered fragments; explicit progress tracking | High; current-version source checked | Add independent evidence for final placement unlock behavior |
| Monster List / Vicious | 333/333 ordinals and English names; 302 gated locations across 200 monsters and 164 drops across 144 monsters; 15 Vicious Monster List entries routed; dedicated tracker remains 10 targets / 11 target encounters | High for normalized rows | Continue remaining encounter and drop ingestion |
| Player state | Schema and empty Ryan state | Ready, no user data | Fill only from Ryan's reports |
| Conflicts | Automatic exact-scope detection active; 7 unresolved source conflicts | Conservative coverage | Resolve location disputes and Stella/Stellar spelling with direct in-game evidence |

## Database seed counts

Expected after `python scripts/build_kb.py`:

- sources: 334
- vocations/entities: 26
- prerequisite relationships: 27
- vocation rank skills / perks: 250 / 26
- vocation progression rules: 7
- vocation stat modifiers: 220
- claims: 28
- medal rewards: 19
- missables: 7
- farming spots: 8
- seed effects / reward rules: 18 / 1
- monster hearts: 46
- checkpoints: 33
- mini medal locations: 100
- checkpoint obligations: 222
- achievements / aliases: 61 / 1
- achievement requirements: 29
- stone tablets / fragments: 20 / 71
- monsters: 333
- monster encounters / drops: 302 / 164
- Vicious species / encounters: 10 / 11
- ready-for-play checkpoint advice: 86
- Mini Medal corroborating evidence rows: 86
- Heroic Hoarder items: 353
- item aliases / acquisition paths: 1 / 633
- shops / inventory rows: 47 / 115
- Lucky Panel pools / reward rows: 14 / 223
- searchable documents: 29 (10 curated summaries + 19 reward rows)

Treat these as build assertions, not completion percentages.

## Immediate Phase 1 batch order

1. Expand the initial Prologue-through-Emberdale obligations to full item, fragment, monster, and stop-condition coverage.
2. L'Arca through Alltrades checkpoints and obligations.
3. Complete the remaining item, monster, fragment, and achievement obligations within the 33-checkpoint spine.
4. Continue the existing source-ordinal mapping for every independently corroborated medal.
5. Directly refresh Game8 medal rows when the page is accessible; rows currently available only through its indexed table remain medium confidence unless independently corroborated.

The `medal_report.py --through CHECKPOINT` query uses `available_checkpoint_id`, not physical location order, so later key-gated chests are excluded from early availability reports.

## Latest completed batch

The 2026-08-26 early-game vertical slice has 54 explicitly ordered obligations and 20 attributed recommendations through Alltrades. It supports explicit completed-check tracking, checkpoint-focused output, honest medal state, conditional threshold advice, operational STOP warnings, and checkpoint-scoped conflict alerts. Unsupported advice remains an explicit gap; no levels or grind rates were invented.

The next chronological slice adds 45 ordered obligations across Alltrades Present, the desert arc, Aishe/Moonlighting, the Flying Carpet route, and Sir Mervyn. No irreversible STOP was asserted without evidence. `walkthrough.py` is now the canonical checkpoint-generic command; `early_walkthrough.py` remains compatible.

The 2026-08-26 main-story expansion adds 77 obligations and completes explicit chronology from Greenthumb through the ending (cp015–cp029). Verified STOPs cover the Vogograd tablet choice, Cathedral pre-sleep cleanup, Estard/Pilchard pre-teleportal cleanup, the timed Villa Priores Hermes Hat opportunity, and the completion-safe Nottagen branch. The final boss is not treated as a permanent cutoff because the clear file reloads before the battle. Postgame cp030–cp033 remains the next chronological target.

The postgame expansion adds 27 obligations and completes explicit ordering through cp033. Another World, Testy Road, the eight-Gold-Fragment gate, every Yet Another World branch and boss, all 100 Mini Medals, and every documented arena turn-threshold reward are now represented as playable steps. No postgame irreversible STOP is asserted. The final completion audit remains explicitly partial until the dedicated achievement and full item registries are complete.

The achievement-ledger batch adds all 61 achievements with stable IDs, story/checkpoint scope, trophy grades, hidden flags, provenance, and an explicit player-progress/reporting workflow. The Steam `Field Day` versus cross-platform `A Questrian` name is retained as an alias instead of silently merged. Counter and collection dependencies remain the next normalization layer.

The first Heroic Hoarder registry expansion completes all 24 Shields and 33 Head items. It adds 34 identities and 20 supported routes; 15 Head entries deliberately retain `source_checked_route_gap` rather than receiving invented acquisition data.

The full identity expansion completes the evidence-backed 353-item Heroic Hoarder list: 110 Weapons, 69 Armour, 74 Accessories, 24 Shields, 33 Head items, and 43 Usable Items. There are 272 supported acquisition paths across 181 items; the other 172 identities retain explicit route gaps. The earlier 354 estimate was corrected from the source category totals rather than padded with an invented item.

The route-resolution batch adds 96 supported paths, reducing Heroic Hoarder route gaps from 172 to 76. It adds precise early shop prices and checkpoint gates plus typed Lucky Panel details, without silently resolving the `Stella`/`Stellar Fan` name discrepancy or the unsupported Wizard's Staff purchase. The achievement layer now links all 29 non-story achievements to measurable counters, checkpoint obligations, the 353-item registry, or an explicit unresolved registry.

The tablet and route batch adds all 20 tablets and 71 current-version fragments with numbered provenance and checkpoint gates, resolving the No Stone Left Unturned dependency. A further 37 item routes reduce Heroic Hoarder gaps from 76 to 39 while keeping the Wizard/Wizard's and Stella/Stellar naming discrepancies explicit.

The monster and vocation batch adds all 333 Monster List ordinals, 10 distinct Vicious species across 11 encounters, and party-wide mastery aggregation for all 26 vocations. Take No Prisoners, Vanquisher of the Vicious, and Master of All now have structured dependencies and explicit progress commands. English monster names remain unset where ordinal alignment is not proven.

The English-name, item-route, and optimization batch maps 289/333 Monster List ordinals to source-verified English names, reduces Heroic Hoarder to one explicit Stella/Stellar Fan naming conflict, and adds eight checkpoint-valid gear, vocation, Heart, and farming recommendations across cp010–cp019.

The completion and live-play batch gives all 353 Heroic Hoarder items a sourced route, preserves Stella Fan as an alias and unresolved name claim, completes all 333 English Monster List mappings, adds seven optimization rows across cp020–cp032, and introduces compact walkthrough output for play alongside the game.

The first combat-engine batch adds 24 checkpoint-gated encounters and 12 verified drops across the first 15 monsters, all eight Martial Artist rank skills plus Critical Stance, and ten concise live-play recommendations across cp003–cp020.

The second combat-engine batch completes rank skills and Let Loose perks for all ten beginner vocations, extends monster encounter/drop coverage through Alltrades Present, adds seven pre-Alltrades gear/grind recommendations, and exposes monster lookup by name, ID, or ordinal.

The third combat-engine batch completes rank skills and Let Loose perks for all seven intermediate vocations, extends monster encounter/drop coverage through Sir Mervyn, adds six midgame vocation/grind recommendations, and exposes exact vocation skill ladders through `vocation_report.py`.

The fourth combat-engine batch completes all three advanced vocation skill ladders and perks, extends gated monster/drop coverage through Aeolus Vale, adds five later-midgame vocation-role recommendations, and adds prerequisite summaries to vocation lookup.

The fifth combat-engine batch completes sourced rank skills and Let Loose perks for all six character-exclusive vocations, extends monster/drop coverage through the Wind Spirit slice, adds six late/postgame vocation recommendations, and adds checkpoint-based remaining-monster lookup.

The sixth combat-engine batch extends monster routes through postgame, adds six late-game fixed-gear recommendations, records seven verified vocation-progression mechanics without inventing unpublished rank costs, and adds concise Monster List coverage reporting.

The seventh combat-engine batch adds direct tactics for five midgame bosses, 33 qualitative advanced-vocation stat modifiers, four additional monster pages, and an opt-in inline monster checklist for the compact walkthrough.

The eighth combat-engine batch extends qualitative modifiers to all non-default vocations, adds six later/postgame boss tactics, adds five Vicious/postgame monster pages, and lets progress commands accept Monster List ordinals or unambiguous English names.

The first browser-interface batch adds a responsive dependency-free dashboard and checkpoint walkthrough, validated progress mutations, provenance/conflict views, domain JSON endpoints, three server integration tests, and two additional monster pages.

The current monster expansion has 302 checkpoint-gated encounter routes across 200 of 333 monsters and 164 verified drop rows across 144 monsters. The latest late-game batch adds Togre in the Present Cathedral of Blight at cp028 with its Heroic Hoarder Shield of Shame drop, The Stranger in Present Another World at cp030 with Seed of Deftness, and the previously routed Cathedral Stout Troll's Seed of Strength. All three rates remain unpublished. Togre's separate Wilted Heart Region habitat is intentionally not normalized because the direct page does not establish whether that high-level encounter shares the area's much earlier story availability.

The item-route normalization batch links 44 existing source-verified monster drops into checkpoint-aware acquisition paths. This gives 19 Heroic Hoarder items a renewable enemy-drop alternative to Lucky Panel and reduces items represented only by Lucky Panel paths from 40 to 21; each route retains the direct monster-page drop and location locator.

The first Monster Heart batch adds a forward-compatible registry and 12 directly sourced effects covering the earliest entries through Mud Mannequin Heart. Golem Heart is gated at Ballymolloy from explicit availability evidence; the other 11 acquisition windows remain unknown, and the Metal Slime Heart note preserves its documented DLC scope without claiming a non-DLC route.

The second Monster Heart batch completes all 46 current-version identities and effects. Availability remains unset for 45 Hearts, and both Metal Slime Heart and Gold Golem Heart retain the source's Jam-Packed Swag Bag DLC scope without implying exclusivity or a non-DLC route.

The acquisition-link batch reuses independently sourced item-acquisition rows to expose checkpoint, period, method, supply, source, and locator on Heart details. Earliest playable examples now include Slime/Golem/Hammerhood at cp003, Bodkin Archer/Little Devil at cp004, Healslime at cp005, and additional fixed/drop routes through cp011. No stored numeric drop rate or acquisition DLC scope exists, so both remain explicitly unknown; unmatched Heart/item names remain unlinked.

The missable audit gives all seven records precise direct-source locators and normalizes five exact action boundaries. It corrects the Vogograd reward to Pretty Betsy, records the irreversible Wrecked Specs, Wiggles, and Kiefer choices, and leaves the Wooden Doll's branching cutoff and Little Blue Button's unnamed story cutoff explicitly unknown.

The Lucky Panel chest batch completes Version 2's three-item and Version 3's eleven-item treasure-chest matrices. It adds 13 version-scoped reward paths, retains the Version 2 replacement boundary at the final Elemental Spirits upgrade, and leaves chest probability and slot counts unknown.

The next Lucky Panel batch completes all safely linkable Version 3 Rank 1 rows: 22 of the source's 25 published names now have version-, rank-, venue-, and checkpoint-scoped atomic routes. `Knuckledusters`, `Magic Vestments`, and plural `Slime Earrings` remain unlinked because those exact identities are absent from the canonical 353-item registry; they were not silently merged with similarly named entries. Entry cost and reward probabilities remain unknown.

The Version 3 Rank 2 batch links 32 of 36 directly published names, adding 29 atomic routes beyond the three already normalized. Curly-versus-straight apostrophes for Assassin's Dagger and the two Pillager items are explicitly marked as typographic resolutions. `Faerie Foil`, `Ledgerdemantle`, `Scholar’s Glasses`, and `Shard of Lucida` remain unlinked because the canonical registry lacks those exact identities; costs and probabilities remain unknown.

The Version 3 Rank 3 batch links 29 of 31 directly published names, adding 24 atomic routes beyond the five already normalized. Princess's Robe retains an explicit typographic-apostrophe resolution. `Angel Robe` and singular `Falcon Knife Earring` remain unlinked because those exact identities are absent from the canonical registry; costs, slots, and probabilities remain unknown.

The Version 3 Rank 4 batch completes all 21 directly published names, adding 15 atomic routes beyond the six already normalized. Dancer's Mail, Sage's Staff, and Siren's Staff retain explicit typographic-apostrophe resolutions. The source's Lucky Panel-exclusive qualifiers are preserved in structured route prerequisites and locators for Fire Blade, Metal Goomerang, and Thinking Cap; costs, slots, and probabilities remain unknown.

The Version 2 Rank 1 batch links 30 of 32 directly published names, adding 25 atomic routes beyond the five already normalized. Dancer's Costume and Wizard's Staff retain explicit typographic-apostrophe resolutions. `Iron Claw` and `Shell Shield` remain unlinked because those exact identities are absent from the canonical registry. Costs, probabilities, and the standard pool's replacement cutoff remain unknown.

The Version 2 Rank 2 batch links 28 of 31 directly published names, adding 22 atomic routes beyond the six already normalized. Scholar's Specs retains an explicit typographic-apostrophe resolution, and Stellar Fan uses the existing adjudicated spelling identity without hiding its conflict. `Knuckledusters`, `Magic Vestment`, and singular `Steel Fang` remain unlinked exact-name gaps. Costs, probabilities, and the replacement cutoff remain unknown.

The farming audit adds precise provenance and checkpoint gates to all eight routes, separates factual target/location evidence from attributed strategy provenance, and removes unsupported generic tactics. Metal-enemy frequency remains qualitative because the direct source publishes no numeric encounter rates; the repeatable Almighty-and-Spirits reward is sourced separately from Game8's recommended Magic Burst composition.

The Seed normalization batch records fixed current-version increases for all nine standard Seeds and nine Super Seeds. It separately models the repeatable cp032 Almighty-and-Spirits rematch as one random Super Seed per victory while leaving the eligible-item pool unknown because the direct farming source does not enumerate it.

The provenance-completeness batch adds non-empty direct-page row locators and verification states to all 19 Medal rewards, 26 Vocations, and 27 vocation-prerequisite edges. Direct RPG Site heading audits now map all 33 checkpoints to exact chapter/section ranges. Every checkpoint remains visibly `seed_partial` because complete locator coverage does not imply complete walkthrough or optimization coverage.

The Phase 2 equipment batches established typed item, shop, and Lucky Panel acquisition routes for 30 Heroic Hoarder items, including the shield sequence through Shield of Shame. Unspecified containers and pool ranks remain explicit evidence gaps. The Tempest Shield location disagreement is preserved alongside the five earlier unresolved conflicts.

Phase 1 completed all 100 normalized Mini Medal locations, 86 independent RPG Site evidence rows, a 33-checkpoint spine through postgame, and 45 directly checked obligations. RPG Site's parenthetical medal ordinals remain source-specific walkthrough order and are never treated as canonical album IDs.

## Open questions requiring evidence

- Exact story cutoffs for the Wooden Doll branch and Little Blue Button sequence; keep both unresolved until a current-version source names the boundary.
- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Complete fixed Seed effects and the exact postgame Super Seed reward table.
