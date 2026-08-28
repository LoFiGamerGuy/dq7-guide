# Ingestion status

Status date: 2026-08-28
Package: `0.3.0-phase1`  
Build type: reconstructed seed (see `RECOVERY_MANIFEST.md`)

## Current coverage

| Domain | Seed coverage | Confidence | Next target |
|---|---:|---|---|
| Source registry | 366 high-value pages | High metadata / mixed page freshness | Add official and in-game evidence sources |
| Vocations | 26/26 names; 250 sourced rank skills, 26 Let Loose perks, 7 progression rules, and 220 stat modifiers across all non-default vocations | High for normalized rows | Add directly published numeric modifiers if found; do not infer values from arrows |
| Vocation prerequisites | 10 rule groups / 27 prerequisite edges with per-edge locators | High | Add derived shortest paths and mastery cost |
| Moonlighting | cp012-after-Aishe gate, Career Sphere flow, simultaneous two-vocation learning, and dual skill/stat access normalized | High for published behavior; Alltrades-vs-Shrine activation venue conflict and unpublished restrictions remain open | Resolve venue conflict and legal-pair/skill-retention restrictions from in-game evidence |
| Walkthrough checkpoints | 33 checkpoints; 222 obligations; cp001–cp033 ordered and progress-aware; all 33 have directly verified RPG Site section-range locators | High for chronology and locator provenance; optimization/content depth remains partial | Expand checkpoint-specific optimization without treating locator coverage as content completeness |
| Mini Medal rewards | 19/19 reward thresholds with per-row table locators | High | Cross-check reward stats/effects and exchange availability |
| Mini Medal locations | 100/100 normalized rows with earliest-availability checkpoint gates | 86 cross-source verified; 13 indexed-source checked; 1 Game8-only indexed row | Directly refresh Game8 when accessible and resolve the medal 78 locator conflict |
| Missables / choices | 7/7 direct-source records with precise locators; 6 exact choice/window cutoffs and Little Blue Button explicitly unresolved | High for documented consequences; medium where the source omits a cutoff | Resolve Little Blue Button's story cutoff; it is not STOP-eligible until then |
| Heroic Hoarder items | 353/353 required identities / 707 acquisition paths across 354 shared items; all required items have routes; direct finite pickups now provide free alternatives for Hairband, Rabbit Ears, Coagulant, Pretty Betsy, Prayer Ring, Kamikazee Bracer, Pirate's Hat, and Steel Helmet in addition to normalized monster-drop alternatives | High for identities and explicit routes; exact containers remain unknown where the direct source publishes only an item list; Stella/Stellar spelling conflict remains visible | Expand remaining alternate free routes and exact finite-container evidence |
| Lucky Panel | 14 normalized pools / 288 reward paths; all standard matrices are normalized: Version 1 Ranks 1–3 link 23/23, 30/31, and 18/19 published names; Version 2 Ranks 1–3 link 30/32, 29/31, and 31/33; Version 3 Ranks 1–4 link 23/25, 33/36, 29/31, and 21/21 | High for normalized rows; three dedicated current-version item pages resolve Slime Earrings, Magic Vestment, and Faerie Foil spelling/number variants; Version 1 Rank 2 retains one legacy Slime Earring row absent from the current table; the source says its lists may be non-exhaustive, and entry costs/probabilities remain unknown | Resolve remaining exact-name gaps and the legacy row; verify costs/probabilities if published |
| Equipment | 86 ready-for-play gear, boss, grind, vocation, and tactical rows across cp001–cp033 | Medium/High, attributed | Continue direct boss-strategy coverage |
| Farming | 10/10 routes have direct-source locators and checkpoint gates, including cp009 Lucky Panel gold and cp013 Moonlighting proficiency routes; factual locations and attributed tactics are separated | High for routes/gates; numeric encounter, gold-per-time, and proficiency-per-time rates remain unpublished. No Heart route is labeled repeatable: direct pages establish one-time Vicious rewards, while Grody Gumdrops sources establish a Heart reward/drop but not repeatability. | Resolve a repeatable Heart route from explicit respawn/rematch evidence before adding a Heart farm/filter |
| Stat Seeds | 18/18 standard and Super Seed effects normalized; one repeatable postgame random-Super-Seed reward rule | High for fixed effects and one-per-victory reward; eligible random pool remains unknown | Verify the postgame random reward membership without inference |
| Monster Hearts | 46/46 normalized Hearts with sourced effects; 41/46 now surface acquisition routes after adding the finite Vicious Meowgician reward at cp005 | High for effects and linked routes; five DLC identities/routes remain outside the shared item registry, and numeric drop rates remain unknown | Normalize the five dedicated-page DLC routes without implying base-game or Heroic Hoarder scope |
| Achievements | 61/61 identities; 29/29 non-story requirements; explicit player tracking | High for identities and dependency structure; no unresolved registry placeholder remains | Verify monster English-name alignment and remaining counter semantics |
| Tablets / fragments | 20/20 tablets and 71/71 numbered fragments; explicit progress tracking | High; current-version source checked | Add independent evidence for final placement unlock behavior |
| Monster List / Vicious | 333/333 ordinals and English names; 338 gated locations across 225 monsters and 190 drops across 166 monsters; 15 Vicious Monster List entries routed; dedicated tracker remains 10 targets / 11 target encounters | High for normalized rows | Continue remaining encounter and drop ingestion |
| Player state | Schema and empty Ryan state | Ready, no user data | Fill only from Ryan's reports |
| Conflicts | Automatic exact-scope detection active; Iron Shield price, Ice Shield chest, Cautery Sword's Tunnel route, and Elevating Shoes methods are resolved from dedicated current-version pages; 4 source conflicts remain unresolved and expose required evidence | High for resolved location rows; conservative elsewhere; Tempest may represent two valid routes rather than a single-value disagreement | Verify Tempest Shield's Sanctum and Ventus chests in-game under one patch before adjudicating; resolve spelling with direct UI evidence |

## Database seed counts

Expected after `python scripts/build_kb.py`:

- sources: 367
- vocations/entities: 26
- prerequisite relationships: 27
- vocation rank skills / perks: 250 / 26
- vocation progression rules: 7
- vocation stat modifiers: 220
- claims: 30
- medal rewards: 19
- missables: 7
- farming spots: 10
- seed effects / reward rules: 18 / 1
- monster hearts: 46
- checkpoints: 33
- mini medal locations: 100
- checkpoint obligations: 222
- achievements / aliases: 61 / 1
- achievement requirements: 29
- stone tablets / fragments: 20 / 71
- monsters: 333
- monster encounters / drops: 338 / 190
- Vicious species / encounters: 10 / 11
- ready-for-play checkpoint advice: 86
- Mini Medal corroborating evidence rows: 86
- Heroic Hoarder items: 353
- item aliases / acquisition paths: 4 / 707
- shops / inventory rows: 47 / 115
- Lucky Panel pools / reward rows: 14 / 288
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

The early-game vertical slice now includes direct tactical coverage for the Tribulators, Golem, Tinpot Dictator, and Florin alongside the existing bosses through Alltrades. It supports explicit completed-check tracking, checkpoint-focused output, honest medal state, conditional threshold advice, operational STOP warnings, and checkpoint-scoped conflict alerts. Unsupported advice remains an explicit gap; no levels or grind rates were invented.

The cp011–cp020 boss pass fills Skeleton Squire, Setesh, Sunken Spirits, King Slime, Ethereal Serpent, Rainiac, The Envoy, and Vaipur. Consecutive-fight recovery and counter/Fizzle windows are kept in encounter order without importing the source pages' suggested character levels.

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

The late/postgame boss-sequence audit adds six direct current-version tactics: optional The Time Being before the first Orgodemir fight, Moostapha then Malign Vine in Nottagen, Lourgh and Disorder, the first postgame Almighty fight, and Xenlon before the Almighty-and-Spirits encounter. Each row retains its exact checkpoint/period gate and role tradeoff; published suggested levels were deliberately not normalized.

The first browser-interface batch adds a responsive dependency-free dashboard and checkpoint walkthrough, validated progress mutations, provenance/conflict views, domain JSON endpoints, three server integration tests, and two additional monster pages.

The current monster expansion has 338 checkpoint-gated encounter routes across 225 of 333 monsters and 190 verified drop rows across 166 monsters. The latest late-world cleanup batch adds Delusionist (Present Burnmont and Hidden Pyramid), Infernal Serpent (Present Burnmont and Aeolus Vale Region), Hyperpyrexion (Present Roamer Encampment and Alltrades Abbey Regions), and Alarmour (Present Hardlypool and Aeolus Vale Regions), conservatively gated to cp026. Direct pages verify Garish Garb, Seed of Strength, Hate Mail, Magic Water, and Platinum Mail drops; published rates remain unknown.

The item-route normalization batch links 44 existing source-verified monster drops into checkpoint-aware acquisition paths. This gives 19 Heroic Hoarder items a renewable enemy-drop alternative to Lucky Panel and reduces items represented only by Lucky Panel paths from 40 to 21; each route retains the direct monster-page drop and location locator.

The first Monster Heart batch adds a forward-compatible registry and 12 directly sourced effects covering the earliest entries through Mud Mannequin Heart. Golem Heart is gated at Ballymolloy from explicit availability evidence; the other 11 acquisition windows remain unknown, and the Metal Slime Heart note preserves its documented DLC scope without claiming a non-DLC route.

The second Monster Heart batch completes all 46 current-version identities and effects. Availability remains unset for 45 Hearts, and both Metal Slime Heart and Gold Golem Heart retain the source's Jam-Packed Swag Bag DLC scope without implying exclusivity or a non-DLC route.

The acquisition-link batch reuses independently sourced item-acquisition rows to expose checkpoint, period, method, supply, source, and locator on Heart details. Earliest playable examples now include Slime/Golem/Hammerhood at cp003, Bodkin Archer/Little Devil at cp004, Healslime at cp005, and additional fixed/drop routes through cp011. No stored numeric drop rate or acquisition DLC scope exists, so both remain explicitly unknown; unmatched Heart/item names remain unlinked.

The remaining-heart audit directly links Meowgician Heart to the finite Vicious Meowgician reward/drop in L'Arca Past at `cp_005_larca`. Its dedicated page proves the exact identity and monster source, while the existing encounter page supplies the checkpoint gate; drop rate and repeatability remain unpublished, so it is not labeled renewable. Metal Slime and Gold Golem Hearts are directly documented as Jam-Packed Swag Bag DLC grants, and Dragonlord, Malroth, and Zoma Hearts as Road of Regal Battle Arena DLC rewards. Those five exact identities remain outside the shared item registry until DLC ownership/availability and non-Heroic item semantics are normalized rather than guessed.

The missable audit gives all seven records precise direct-source locators and normalizes six exact action boundaries. It corrects the Vogograd reward to Pretty Betsy, records the irreversible Wrecked Specs, Wooden Doll branch confirmations, Wiggles, and Kiefer choices, and leaves only the Little Blue Button's unnamed story cutoff explicitly unknown and ineligible for STOP presentation.

The Lucky Panel chest batch completes Version 2's three-item and Version 3's eleven-item treasure-chest matrices. It adds 13 version-scoped reward paths, retains the Version 2 replacement boundary at the final Elemental Spirits upgrade, and leaves chest probability and slot counts unknown.

The next Lucky Panel batch completes all safely linkable Version 3 Rank 1 rows: 22 of the source's 25 published names now have version-, rank-, venue-, and checkpoint-scoped atomic routes. `Knuckledusters`, `Magic Vestments`, and plural `Slime Earrings` remain unlinked because those exact identities are absent from the canonical 353-item registry; they were not silently merged with similarly named entries. Entry cost and reward probabilities remain unknown.

The Version 3 Rank 2 batch links 32 of 36 directly published names, adding 29 atomic routes beyond the three already normalized. Curly-versus-straight apostrophes for Assassin's Dagger and the two Pillager items are explicitly marked as typographic resolutions. `Faerie Foil`, `Ledgerdemantle`, `Scholar’s Glasses`, and `Shard of Lucida` remain unlinked because the canonical registry lacks those exact identities; costs and probabilities remain unknown.

The Version 3 Rank 3 batch links 29 of 31 directly published names, adding 24 atomic routes beyond the five already normalized. Princess's Robe retains an explicit typographic-apostrophe resolution. `Angel Robe` and singular `Falcon Knife Earring` remain unlinked because those exact identities are absent from the canonical registry; costs, slots, and probabilities remain unknown.

The Version 3 Rank 4 batch completes all 21 directly published names, adding 15 atomic routes beyond the six already normalized. Dancer's Mail, Sage's Staff, and Siren's Staff retain explicit typographic-apostrophe resolutions. The source's Lucky Panel-exclusive qualifiers are preserved in structured route prerequisites and locators for Fire Blade, Metal Goomerang, and Thinking Cap; costs, slots, and probabilities remain unknown.

The Version 2 Rank 1 batch links 30 of 32 directly published names, adding 25 atomic routes beyond the five already normalized. Dancer's Costume and Wizard's Staff retain explicit typographic-apostrophe resolutions. `Iron Claw` and `Shell Shield` remain unlinked because those exact identities are absent from the canonical registry. Costs, probabilities, and the standard pool's replacement cutoff remain unknown.

The Version 2 Rank 2 batch links 28 of 31 directly published names, adding 22 atomic routes beyond the six already normalized. Scholar's Specs retains an explicit typographic-apostrophe resolution, and Stellar Fan uses the existing adjudicated spelling identity without hiding its conflict. `Knuckledusters`, `Magic Vestment`, and singular `Steel Fang` remain unlinked exact-name gaps. Costs, probabilities, and the replacement cutoff remain unknown.

The Version 2 Rank 3 batch links 30 of 33 directly published names, adding 20 atomic routes beyond the ten already normalized. Assassin's Dagger retains explicit typographic resolution. Staff of Salvation preserves the source's `Lucky Panel or enemy drop` qualifier in structured prerequisites and its locator; the existing Saw Blade route retains its exclusive qualifier. `Faerie Foil`, singular `Ferocious Fang`, and `Ledgerdemantle` remain unlinked exact-name gaps. Costs and probabilities remain unknown.

The Version 1 Rank 1 batch links 22 of the direct source's 23 published names, adding 11 atomic Past routes beyond the 11 already normalized. Wayfarer's Clothes retains explicit typographic-apostrophe resolution. Plural `Slime Earrings` remains an exact-name gap rather than being silently merged with singular `Slime Earring`. Pool timing is inherited from the Version 1 Past pool at `cp_009_alltrades`; no unsupported cutoff was added. The source itself warns that its reward lists may not be exhaustive, and costs and probabilities remain unknown.

The Version 1 Rank 2 batch links 30 of 31 directly published names, adding 17 atomic Past routes beyond 14 legacy rows (13 matching current published names plus one legacy singular `Slime Earring` row absent from the current table). Cottontail Costume preserves the source's `Lucky Panel exclusive` qualifier, while Dancer's Costume, Scholar's Specs, and Wizard's Staff retain explicit typographic-apostrophe resolution. The source spelling `Scake Armour` remains an unresolved exact-name gap rather than being silently mapped to `Scale Armour`; the legacy Slime Earring row is retained rather than silently discarded. Pool timing is inherited from `cp_009_alltrades`; costs and probabilities remain unknown, and the source describes its lists as potentially non-exhaustive.

The Version 1 Rank 3 batch completes normalization of every directly published standard-rank table. It links 17 of 19 published names, adding 11 atomic Past routes beyond six legacy rows and refining those legacy locators to the exact table entries. `Stellar Fan` uses the existing adjudicated Stella/Stellar alias without erasing the visible spelling conflict. `Knuckledusters` and singular `Magic Vestment` remain exact-name gaps; the latter was not silently merged with canonical `Magic Vetment`. Pool timing is inherited from `cp_009_alltrades`; costs and probabilities remain unknown, and the source describes its lists as potentially non-exhaustive.

The exact-name audit adds three provenance-backed aliases from dedicated current-version item pages: `Slime Earrings` to the retained `Slime Earring` identity, `Magic Vestment` to `Magic Vetment`, and `Faerie Foil` to `Fairie Foil`. Those aliases resolve six published matrix rows without changing canonical IDs. Other typos, plurals, punctuation differences, and reordered names remain unresolved because no dedicated page or in-game naming evidence directly proves equivalence. The Version 1 Rank 2 legacy singular Slime Earring row is still retained: the dedicated page proves the identity and generic Lucky Panel availability, but not that absent Rank 2 listing.

The alternate-route batch adds three direct current-version finite, free treasures for items otherwise represented only by Lucky Panel: Hairband in L'Arca Past and Rabbit Ears in L'Arca Present at `cp_005_larca`, plus Coagulant in Hubble Castle Past at `cp_016_hubble`. The dedicated pages publish the area and period but not the exact container, which remains explicit in verification status rather than inferred.

The next early-game route batch adds two fixed alternatives from the direct current-version walkthrough: Pretty Betsy in the northern L'Arca Region Present at `cp_005_larca` (requiring direct boat landing), and Prayer Ring in the Tunnel to Alltrades Abbey Past at `cp_009_alltrades` after obtaining the Alltrades Key. Both are finite and free; the source does not publish an exact container for either, so no container detail was invented.

The cp010–cp020 audit adds Kamikazee Bracer as a finite, free treasure in Likeness of the Great Evil Past at `cp_011_la_bravoure`, backed by its dedicated current-version item page; the exact container remains unpublished. Potential Pillager's Helmet and Slime Earrings fixed pickups were not normalized because the direct dedicated pages conflict with or do not support the walkthrough wording, so those source differences remain unresolved.

The late-game finite-route batch adds Pirate's Hat from the explicitly published Buccanham Palace closet at `cp_020_buccanham` and Steel Helmet as Rucker Castle Past treasure at `cp_027_deja_vous_rucker`. The Pirate's Hat page does not identify the closet room, and the Steel Helmet page does not identify the exact container; both unknowns remain explicit. Agility Ring was not linked to the walkthrough's Villa Priores wording because its dedicated current-version page instead lists Sanctum of the Cirrus and Ventus Tower treasures.

The farming audit adds precise provenance and checkpoint gates to all eight routes, separates factual target/location evidence from attributed strategy provenance, and removes unsupported generic tactics. Metal-enemy frequency remains qualitative because the direct source publishes no numeric encounter rates; the repeatable Almighty-and-Spirits reward is sourced separately from Game8's recommended Magic Burst composition.

The Seed normalization batch records fixed current-version increases for all nine standard Seeds and nine Super Seeds. It separately models the repeatable cp032 Almighty-and-Spirits rematch as one random Super Seed per victory while leaving the eligible-item pool unknown because the direct farming source does not enumerate it.

The provenance-completeness batch adds non-empty direct-page row locators and verification states to all 19 Medal rewards, 26 Vocations, and 27 vocation-prerequisite edges. Direct RPG Site heading audits now map all 33 checkpoints to exact chapter/section ranges. Every checkpoint remains visibly `seed_partial` because complete locator coverage does not imply complete walkthrough or optimization coverage.

The Phase 2 equipment batches established typed item, shop, and Lucky Panel acquisition routes for 30 Heroic Hoarder items, including the shield sequence through Shield of Shame. Unspecified containers and pool ranks remain explicit evidence gaps. The Elevating Shoes exclusivity conflict is now resolved to the dedicated current-version item page: Metal King Slime is a second acquisition method, while its numeric drop rate and earliest gated encounter remain unknown. Tempest Shield and four other disagreements remain unresolved.

Phase 1 completed all 100 normalized Mini Medal locations, 86 independent RPG Site evidence rows, a 33-checkpoint spine through postgame, and 45 directly checked obligations. RPG Site's parenthetical medal ordinals remain source-specific walkthrough order and are never treated as canonical album IDs.

## Open questions requiring evidence

- Exact story cutoff for the Little Blue Button sequence; keep it unresolved and out of STOP warnings until a current-version source names the boundary.
- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Complete fixed Seed effects and the exact postgame Super Seed reward table.
