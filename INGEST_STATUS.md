# Ingestion status

Status date: 2026-08-28
Package: `0.3.0-phase1`  
Build type: reconstructed seed (see `RECOVERY_MANIFEST.md`)

## Current coverage

| Domain | Seed coverage | Confidence | Next target |
|---|---:|---|---|
| Source registry | 411 high-value pages | High metadata / mixed page freshness | Add official and in-game evidence sources |
| Vocations | 26/26 names; 250 sourced rank skills, 26 Let Loose perks, 7 progression rules, and 220 stat modifiers across all non-default vocations | High for normalized rows | Add directly published numeric modifiers if found; do not infer values from arrows |
| Vocation prerequisites | 10 rule groups / 27 prerequisite edges with per-edge locators; vocation detail now exposes sourced direct unlock rules and explicit-state party progress | High for direct paths; numeric mastery cost remains unpublished | Add mastery cost only from direct numeric evidence; expand derived multi-tier alternatives without hiding `any_n_of` choices |
| Moonlighting | cp012-after-Aishe gate, Career Sphere flow, simultaneous two-vocation learning, and dual skill/stat access normalized | High for published behavior; Alltrades-vs-Shrine activation venue conflict and unpublished restrictions remain open | Resolve venue conflict and legal-pair/skill-retention restrictions from in-game evidence |
| Walkthrough checkpoints | 33 checkpoints; 222 obligations; cp001–cp033 ordered and progress-aware; all 33 have directly verified RPG Site section-range locators | High for chronology and locator provenance; optimization/content depth remains partial | Expand checkpoint-specific optimization without treating locator coverage as content completeness |
| Mini Medal rewards | 19/19 reward thresholds with per-row table locators | High | Cross-check reward stats/effects and exchange availability |
| Mini Medal locations | 100/100 normalized rows with earliest-availability checkpoint gates; #78 resolved to The Beacon Past 3F south-balcony chest | 86 cross-source verified; 13 indexed-source checked; 1 Game8-only indexed row | Directly refresh the remaining indexed-only rows when accessible |
| Missables / choices | 7/7 direct-source records with precise locators; 6 exact choice/window cutoffs and Little Blue Button explicitly unresolved | High for documented consequences; medium where the source omits a cutoff | Resolve Little Blue Button's story cutoff; it is not STOP-eligible until then |
| Heroic Hoarder items | 353/353 required identities / 744 acquisition paths across 355 shared items; all required items have routes; direct finite pickups now provide free alternatives for panel-listed equipment throughout the early and midgame in addition to normalized monster-drop alternatives | High for identities and explicit routes; exact containers remain unknown where the direct source publishes only an item list; Stella/Stellar spelling conflict remains visible | Expand remaining alternate free routes and exact finite-container evidence |
| Lucky Panel | 14 normalized pools / 302 reward paths; all standard matrices are normalized: Version 1 Ranks 1–3 link 23/23, 31/31, and 19/19 published names; Version 2 Ranks 1–3 link 31/32, 31/31, and 33/33; Version 3 Ranks 1–4 link 25/25, 36/36, 31/31, and 21/21 | High for normalized rows; dedicated current-version pages resolve all defensible spelling/number/order variants; `Shell Shield` remains the sole exact-name gap. Version 1 Rank 2 retains one legacy Slime Earring row absent from the current table; entry costs/probabilities remain unknown | Verify Shell Shield, the legacy row, and costs/probabilities if directly published |
| Equipment | 86 ready-for-play gear, boss, grind, vocation, and tactical rows across cp001–cp033 | Medium/High, attributed | Continue direct boss-strategy coverage |
| Farming | 10/10 routes have direct-source locators and checkpoint gates, including cp009 Lucky Panel gold and cp013 Moonlighting proficiency routes; factual locations and attributed tactics are separated | High for routes/gates; numeric encounter, gold-per-time, and proficiency-per-time rates remain unpublished. No Heart route is labeled repeatable: direct pages establish one-time Vicious rewards, while Grody Gumdrops sources establish a Heart reward/drop but not repeatability. | Resolve a repeatable Heart route from explicit respawn/rematch evidence before adding a Heart farm/filter |
| Stat Seeds | 18/18 standard and Super Seed effects normalized; one repeatable postgame random-Super-Seed reward rule | High for fixed effects and one-per-victory reward; eligible random pool remains unknown | Verify the postgame random reward membership without inference |
| Monster Hearts | 46/46 normalized Hearts with sourced effects; 41/46 now surface acquisition routes after adding the finite Vicious Meowgician reward at cp005 | High for effects and linked routes; Metal Slime and Gold Golem have explicit DLC notes, while Dragonlord, Malroth, and Zoma availability remains unknown; numeric drop rates remain unknown | Verify and normalize the three availability-unknown Hearts without implying DLC, base-game, or Heroic Hoarder scope |
| Achievements | 61/61 identities; 29/29 non-story requirements; explicit player tracking | High for identities and dependency structure; no unresolved registry placeholder remains | Verify monster English-name alignment and remaining counter semantics |
| Tablets / fragments | 20/20 tablets and 71/71 numbered fragments; explicit progress tracking | High; current-version source checked | Add independent evidence for final placement unlock behavior |
| Monster List / Vicious | 333/333 ordinals and English names; 426 gated locations across 295 monsters and 213 drops across 185 monsters; 15 Vicious Monster List entries routed; dedicated tracker remains 10 targets / 11 target encounters | High for normalized rows | Continue remaining encounter and drop ingestion |
| Player state | Schema and empty Ryan state | Ready, no user data | Fill only from Ryan's reports |
| Conflicts | Automatic exact-scope detection active; Iron Shield price, Ice Shield chest, Cautery Sword's Tunnel route, Elevating Shoes methods, and Mini Medal 78 are resolved; Tempest Shield is modeled as two supported acquisition routes rather than a false single-value conflict; 2 source conflicts remain unresolved | High for resolved location rows; conservative for Moonlighting venue and Stella/Stellar spelling | Resolve spelling with direct English UI evidence and Moonlighting venue with a continuous activation capture |

## Database seed counts

Expected after `python scripts/build_kb.py`:

- sources: 453
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
- monster encounters / drops: 426 / 213
- Vicious species / encounters: 10 / 11
- ready-for-play checkpoint advice: 86
- Mini Medal corroborating evidence rows: 86
- Heroic Hoarder items: 353
- item aliases / acquisition paths: 4 / 744
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

The current monster expansion has 426 checkpoint-gated encounter routes across 295 of 333 monsters and 213 verified drop rows across 185 monsters. The latest batch adds the exact Yet Another World Four Spirits boss members (Earth, Water, and Wind), the area's explicit Ersatz Estark and Seavern roster entries, two Metal King Slime rare-bonus-enemy habitats, the common Nottagen Worm of Woe route, and the optional Yes-branch Wiggles fight. Every Rampaging Monster List entry retains a direct postgame Buccanham Arena route; exact Testy / Simmering / Fuming / Furious membership remains unresolved for 34 of them. Generic `Special Encounter` alone still does not support a route for Cannibox, Urnexpected, Scarewell, Frighturn, or Damned Well; no route is created from taxonomy/navigation lists alone.

The item-route normalization batch links 44 existing source-verified monster drops into checkpoint-aware acquisition paths. This gives 19 Heroic Hoarder items a renewable enemy-drop alternative to Lucky Panel and reduces items represented only by Lucky Panel paths from 40 to 21; each route retains the direct monster-page drop and location locator.

The first Monster Heart batch adds a forward-compatible registry and 12 directly sourced effects covering the earliest entries through Mud Mannequin Heart. Golem Heart is gated at Ballymolloy from explicit availability evidence; the other 11 acquisition windows remain unknown, and the Metal Slime Heart note preserves its documented DLC scope without claiming a non-DLC route.

The second Monster Heart batch completes all 46 current-version identities and effects. Availability remains unset for 45 Hearts, and both Metal Slime Heart and Gold Golem Heart retain the source's Jam-Packed Swag Bag DLC scope without implying exclusivity or a non-DLC route.

The acquisition-link batch reuses independently sourced item-acquisition rows to expose checkpoint, period, method, supply, source, and locator on Heart details. Earliest playable examples now include Slime/Golem/Hammerhood at cp003, Bodkin Archer/Little Devil at cp004, Healslime at cp005, and additional fixed/drop routes through cp011. No stored numeric drop rate or acquisition DLC scope exists, so both remain explicitly unknown; unmatched Heart/item names remain unlinked.

The remaining-heart audit directly links Meowgician Heart to the finite Vicious Meowgician reward/drop in L'Arca Past at `cp_005_larca`. Its dedicated page proves the exact identity and monster source, while the existing encounter page supplies the checkpoint gate; drop rate and repeatability remain unpublished, so it is not labeled renewable. Metal Slime and Gold Golem Hearts are directly documented as Jam-Packed Swag Bag DLC grants. Dragonlord, Malroth, and Zoma have sourced effects but no normalized availability evidence, so their DLC/base-game scope and routes remain unknown rather than inferred. All five exact identities remain outside the shared item registry until their non-Heroic item semantics are normalized.

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

The next panel-only audit adds Garter as finite, free Present treasure in Greenthumb Gardens Region at `cp_015_greenthumb`, with its exact container unpublished. It also normalizes renewable Slime Earrings drops from Seaslime in Falls Hollow at `cp_016_hubble` and Slimecicle in Coral Cave at `cp_020_buccanham`; neither dedicated monster page publishes a rate. The apparent Wilted Heart fixed Slime Earrings in the walkthrough remains unmodeled because the dedicated item page says no treasure is available in either period.

The early/midgame finite-equipment batch adds Divine Dagger and an exact Level 2 Scale Armour chest in Burnmont at `cp_004_emberdale`, a second Scale Armour treasure in Frobisher and Strength Ring in Faraday Castle at `cp_007_frobisher`, and another Strength Ring on the Present Mountain Path Near Wilted Heart at `cp_015_greenthumb`. Dedicated pages leave four exact containers unknown; the Emberdale walkthrough directly identifies the Burnmont Level 2 Scale Armour chest. Conflicting Pillager's Helmet and Agility Ring walkthrough candidates remain unmodeled.

The next first-half route batch registers Knuckledusters as a sourced non-Heroic shared item, resolving its exact-name gaps in Version 1 Rank 3, Version 2 Rank 2, and Version 3 Rank 1 without changing the 353-item Heroic matrix. Its finite Pilgrim's Perdition treasure is gated at `cp_009_alltrades`. The same batch adds Iron Lance treasures in Grotta del Sigillo at `cp_005_larca` and Allblades Arena at cp009, plus the Burnmont Yggdrasil Leaf at `cp_004_emberdale`; exact containers remain unknown because the dedicated pages publish areas only.

The latest exact-name audit uses dedicated current-version item pages to adjudicate eight additional published matrix spellings without changing canonical IDs: plural `Magic Vestments`, misspelled `Ledgerdemantle` (two rows), reordered `Shard of Lucida`, omitted possessive `Angel Robe`, and singular `Falcon Knife Earring`, `Steel Fang`, and `Ferocious Fang`. `Iron Claw`, `Shell Shield`, `Scholar’s Glasses`, and `Scake Armour` remain unresolved rather than silently merged. The same batch adds the finite free Lucida Shard at Past Alltrades Abbey (`cp_009_alltrades`), while preserving the unpublished exact container.

The final residual-name audit resolves `Iron Claw` to the current UI's plural `Iron Claws`, `Scholar’s Glasses` to the dedicated page/UI identity `Scholar's Specs`, and the source typo `Scake Armour` to `Scale Armour`; each matrix route retains an explicit adjudication marker. `Shell Shield` remains unresolved because no dedicated current-version identity or UI entry was found. RPG Site directly publishes the legacy singular Slime Earring row but describes its lists as potentially non-exhaustive; Game8 corroborates generic Lucky Panel availability without a version/rank. Neither direct source publishes entry costs or numerical reward probabilities, so those fields remain unknown.

Dedicated current-version helmet pages add four early finite/free routes: Leather Hat in Pilchard Bay and Estard from `cp_001_prologue`, plus Pointy Hat in Past Rainbow Mines and Hardwood Headwear in Present Ballymolloy from `cp_003_ballymolloy`. The pages publish areas but not exact containers, which remains explicit.

Adjacent dedicated armour pages add Noble Garb in Past Institute of Automatry at `cp_007_frobisher` and Silk Robe in Present Bandits' Base at `cp_010_alltrades_present`. Both are finite/free alternatives to Lucky Panel with exact containers explicitly unpublished.

The next direct-page batch adds Edged Boomerang in Past Faraday Castle at `cp_007_frobisher` and Fur Cape in Past Poolside Cave at `cp_009_alltrades`; both finite/free routes preserve the unpublished exact container.

The next accessory pass upgrades Rabbit Tail from an area-only Heroic entry to the exact Grotta del Sigillo Level 3 chest at `cp_005_larca`, using the current L'Arca walkthrough. It also adds a second finite/free Fishnet Stockings route in Past Frobisher at `cp_007_frobisher`, with the exact container still unpublished.

The farming audit adds precise provenance and checkpoint gates to all eight routes, separates factual target/location evidence from attributed strategy provenance, and removes unsupported generic tactics. Metal-enemy frequency remains qualitative because the direct source publishes no numeric encounter rates; the repeatable Almighty-and-Spirits reward is sourced separately from Game8's recommended Magic Burst composition.

The Seed normalization batch records fixed current-version increases for all nine standard Seeds and nine Super Seeds. It separately models the repeatable cp032 Almighty-and-Spirits rematch as one random Super Seed per victory while leaving the eligible-item pool unknown because the direct farming source does not enumerate it.

The provenance-completeness batch adds non-empty direct-page row locators and verification states to all 19 Medal rewards, 26 Vocations, and 27 vocation-prerequisite edges. Direct RPG Site heading audits now map all 33 checkpoints to exact chapter/section ranges. Every checkpoint remains visibly `seed_partial` because complete locator coverage does not imply complete walkthrough or optimization coverage.

The Phase 2 equipment batches established typed item, shop, and Lucky Panel acquisition routes for 30 Heroic Hoarder items, including the shield sequence through Shield of Shame. Unspecified containers and pool ranks remain explicit evidence gaps. The Elevating Shoes exclusivity conflict is now resolved to the dedicated current-version item page: Metal King Slime is a second acquisition method, while its numeric drop rate and earliest gated encounter remain unknown. Mini Medal 78 is resolved to The Beacon Past 3F south-balcony chest because RPG Site's precise route is independently matched by a current-version screenshot guide; Game8's second-level label is retained as a resolved conflicting claim. Tempest Shield is no longer a conflict: Game8's dedicated Present Sanctum table supports one fixed treasure, while Game8's Wind Spirit walkthrough and RPG Site independently support a later Ventus Tower 2F chest. Both are normalized as finite free copies under a multi-location acquisition predicate.

The achievement-readiness batch makes all 29 structured completion dependencies state-aware in the API and browser. Heroic Hoarder, Monster List, Vicious, tablet, vocation, and medal progress now distinguishes explicit partial counts, met counters with an unrecorded unlock, and unknown tracking. Empty identity arrays are no longer presented as zero; only a deliberately saved numeric Mini Medal count can establish exact zero.

The equipment-readiness audit confirms that item categories provide nominal slots and checkpoint advice provides a bounded set of attributed character/item recommendations, but the KB has no complete current-version character equipability matrix, accessory slot count, or duplicate-equip rules. The browser therefore keeps equipment writes disabled and exposes a read-only saved-checkpoint comparison with canonical items, route availability, explicit ownership, raw recorded gear, and the precise validation gaps instead of accepting potentially invalid loadouts.

The recursive vocation-planning batch expands all 10 sourced prerequisite groups / 27 edges into a complete per-character dependency tree in vocation details. It preserves every `all_of` and `any_n_of` branch, character exclusivity, group provenance, and explicit mastery state, then surfaces all currently derivable next mastery options without ranking alternatives. Numeric mastery/proficiency cost and absent mastery remain unknown.

The interactive walkthrough readiness pass makes completion STOP obligations explicitly checkable before the normal action list, replaces opaque “Step N” labels with sourced subjects, and marks only the first open action as next. Mini Medals are now structurally separated into current/backtrack checkboxes and a collapsed later-gated reference list, preventing early players from hunting inaccessible medals.

The Moonlighting venue re-audit keeps the conflict unresolved. Both current-version sources agree on the cp012 gate after recruiting Aishe, but Game8 directs the player to Jacqui at Alltrades Abbey while RPG Site places the event at the Shrine of Mysteries; available corroboration does not continuously show the Career Sphere contact and activation venue. The walkthrough now follows the prompt, tries the Shrine route, and names Alltrades as a fallback without implying either disputed venue is canonical. Conflict details request a same-version capture or continuous video with the venue name visible.

The Stella/Stellar Fan re-audit also remains unresolved. Game8's dedicated current-version page consistently uses `Stellar Fan`, while RPG Site says its `Stella Fan` checklist spelling follows the in-game menu; neither available page exposes a legible English UI capture that directly adjudicates the name. Search and item detail continue accepting both spellings through the sourced alias, and conflict details now require an Item List, inventory, shop, or acquisition-result capture with the complete name visible.

The vocation readiness batch adds direct unlock planning to every vocation detail. Intermediate and advanced requirements retain their sourced `all_of` or `any_n_of` semantics, candidate names, required count, locator, and URL. Per-member status uses only explicit mastery records: satisfied thresholds are recognized, while absent records remain unknown and conditional remaining counts are labeled accordingly. Numeric mastery cost remains unknown rather than being inferred from eight-rank skill tables.

Phase 1 completed all 100 normalized Mini Medal locations, 86 independent RPG Site evidence rows, a 33-checkpoint spine through postgame, and 45 directly checked obligations. RPG Site's parenthetical medal ordinals remain source-specific walkthrough order and are never treated as canonical album IDs.

## Open questions requiring evidence

- Exact story cutoff for the Little Blue Button sequence; keep it unresolved and out of STOP warnings until a current-version source names the boundary.
- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Complete fixed Seed effects and the exact postgame Super Seed reward table.
