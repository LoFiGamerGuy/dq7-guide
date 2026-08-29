# Ingestion status

Status date: 2026-08-29
Package: `0.3.0-phase1`  
Build type: reconstructed seed (see `RECOVERY_MANIFEST.md`)

## Current coverage

| Domain | Seed coverage | Confidence | Next target |
|---|---:|---|---|
| Source registry | 635 registered pages; all retrieval dates are currently within 180 days | High metadata / page publication freshness is still mixed | Add official and in-game evidence sources only where they close an explicit gap; refresh retrievals before the 180-day audit threshold |
| Vocations | 26/26 names; 250 sourced rank skills, 26 Let Loose perks, 9 progression rules, and 454 stat modifiers | High for normalized rows | Add directly published numeric modifiers if found; do not infer values from arrows |
| Vocation prerequisites | 10 rule groups / 27 prerequisite edges with per-edge locators; vocation detail exposes sourced unlock rules, explicit-state party progress, 163 verified rank-cost cells, and two-source progression profiles for all 26 vocations | High; 23 complete point ladders, Wolf Boy's story-then-points profile, and two story-granted personal vocations are normalized | Replace guide-table adjudications only if stronger direct current-patch evidence disagrees |
| Moonlighting | cp012-after-Aishe gate, Shrine trigger, Alltrades activation, Career Sphere flow, simultaneous learning, current-vocation-only skills, dual skill/stat access, and any-two-distinct-available-vocations pairing normalized | High; pairing scope and distinctness are independently established by two official current-version pages | Preserve character-exclusive availability and unlock prerequisites when deriving legal pairs |
| Walkthrough checkpoints | 33 checkpoints; 223 obligations; cp001–cp033 ordered and progress-aware; all 33 have directly verified RPG Site section-range locators; cp010 Mighty Pip control advice has two-source boss support and source-checked vocation-rank gates | High for chronology and locator provenance; exact Leg Sweep/Dazzle ranks currently have one dedicated skill-table source and remain labeled accordingly | Expand checkpoint-specific optimization without treating locator coverage as content completeness |
| Mini Medal rewards | 19/19 reward thresholds with per-row table locators | High | Cross-check reward stats/effects and exchange availability |
| Mini Medal locations | 100/100 normalized rows with earliest-availability checkpoint gates; #78 resolved to The Beacon Past 3F south-balcony chest | 100/100 cross-source verified; #74 is directly corroborated by RPG Site's Custodians' Camp well-closet route | Preserve source-specific container aliases and refresh only if new evidence changes a route |
| Missables / choices | 7/7 direct-source records with precise locators and exact choice/window cutoffs; Little Blue Button closes at the late-game Cataclysm | High; the Cataclysm boundary has two independent current-version sources and a continuous walkthrough directly maps its trigger to end-cp022 before cp023 | Preserve player-unknown state; never infer that the Button sidequest was completed |
| Heroic Hoarder items | 353/353 required identities / 748 acquisition paths across 355 shared items; all required items have routes; direct finite pickups now provide free alternatives for panel-listed equipment throughout the early and midgame in addition to normalized monster-drop alternatives | High for identities and explicit routes; exact containers remain unknown where the direct source publishes only an item list; Stella/Stellar spelling conflict remains visible | Expand remaining alternate free routes and exact finite-container evidence |
| Lucky Panel | 14 normalized pools / 303 reward paths; all standard matrices are normalized; free entry, three attempts per in-game day, and the inn reset are independently corroborated | High for normalized rows and entry/attempt/reset rules; `Shell Shield` is resolved as RPG Site's source-error alias for Scale Shield. Version 1 Rank 2 retains one legacy Slime Earring row absent from the current table; one source publishes raw numeric selection cells but no probability formula | Verify the legacy row and numerical probabilities only if directly published |
| Equipment | 39 checkpoint gear-advice rows; all 311 canonical compatibility rows have two-publisher agreement; all 74 accessories/Hearts verified; all six slot-use/count mechanics corroborated; Magic Shield and selected early power items have independently corroborated numeric cells | High for normalized compatibility and slot layout; Cautery Sword, White Shield, and Windcheater now expose two-source combat payoffs; Windcheater's exact drop-rate increase remains single-source and unpublished here | Expand checkpoint-recommended item stats only where two current-version pages agree; keep single-source effects out of verified power comparisons |
| Farming | 10/10 routes have direct-source locators and checkpoint gates, including cp009 Lucky Panel gold and cp013 Moonlighting proficiency routes; factual locations and attributed tactics are separated | High for routes/gates; numeric encounter, gold-per-time, and proficiency-per-time rates remain unpublished. No Heart route is labeled repeatable: direct pages establish one-time Vicious rewards, while Grody Gumdrops sources establish a Heart reward/drop but not repeatability. | Resolve a repeatable Heart route from explicit respawn/rematch evidence before adding a Heart farm/filter |
| Stat Seeds | 18/18 standard and Super Seed effects normalized; one repeatable postgame random-Super-Seed reward rule | High for fixed effects and one-per-victory reward; eligible random pool remains unknown | Verify the postgame random reward membership without inference |
| Monster Hearts | 46/46 normalized Hearts with sourced effects; 41/46 surface shared-item acquisition routes; Dragonlord, Malroth, and Zoma have independently corroborated DLC Arena thresholds and cp020 gates; dedicated reversible ownership ledger in CLI/API/browser | High for effects and published routes; unreported ownership remains unknown; numeric drop rates and repeatable Heart routes remain unknown | Resolve a genuinely repeatable Heart route only from explicit rematch/respawn evidence |
| Achievements | 61/61 identities; 29/29 non-story requirements; explicit player tracking | High for identities and dependency structure; no unresolved registry placeholder remains | Verify monster English-name alignment and remaining counter semantics |
| Tablets / fragments | 20/20 tablets and 71/71 numbered fragments; explicit progress tracking | High; current-version source checked | Add independent evidence for final placement unlock behavior |
| Monster List / Vicious | 333/333 ordinals and English names; 476 gated locations cover 333/333 monsters and 227 drops across 196 monsters; 15 Vicious Monster List entries routed; dedicated tracker remains 10 targets / 11 target encounters | High for normalized rows; only Scarewell remains explicitly single-independent-source | Seek independent confirmation for Scarewell's exact fixed route |
| Player state | Schema and empty Ryan state | Ready, no user data | Fill only from Ryan's reports |
| Conflicts | Automatic exact-scope detection active; 15 unresolved claim-pairs represent 11 disputed source-level facts: 14 pairs across 10 equipment-compatibility identities plus Stella/Stellar Fan | High for normalized compatibility where independent publishers agree; Pirate's Hat, Fishnet Stockings, and Marshal Lourgh chronology conflicts retain their losing claims after resolution | Resolve equipment/name conflicts with legible current-version UI or direct in-game evidence |

## Database seed counts

Expected after `python scripts/build_kb.py`:

- sources: 635
- vocations/entities: 26
- prerequisite relationships: 27
- vocation rank skills / perks: 250 / 26
- vocation progression rules: 9
- vocation stat modifiers: 454
- claims: 1,782
- medal rewards: 19
- missables: 7
- farming spots: 10
- seed effects / reward rules: 18 / 1
- monster hearts: 46
- checkpoints: 33
- mini medal locations: 100
- checkpoint obligations: 223
- achievements / aliases: 61 / 1
- achievement requirements: 29
- stone tablets / fragments: 20 / 71
- monsters: 333
- monster encounters / drops: 476 / 227
- Vicious species / encounters: 10 / 11
- ready-for-play checkpoint advice: 112
- Mini Medal corroborating evidence rows: 100
- Heroic Hoarder items: 353
- item aliases / acquisition paths: 5 / 748
- shops / inventory rows: 47 / 118
- Lucky Panel pools / reward rows: 14 / 303
- searchable documents: 29 (10 curated summaries + 19 reward rows)
- conflicts: 406 total / 15 unresolved claim-pairs / 11 unresolved fact scopes

Treat these as build assertions, not completion percentages.

## Final collectibles/data residual audit

Completion-critical registries are closed at the identity/route level: 353/353 Heroic Hoarder items have at least one sourced acquisition path; all 46 Monster Hearts have sourced effects and acquisition evidence; all 100 Mini Medals have independent direct walkthrough evidence; all 20 tablets and 71 fragments are normalized; and all 61 achievements have identities with all 29 non-story requirements structured.

The remaining evidence-blocked inventory is exact and intentionally conservative:

- **Items:** 6 finite acquisition rows retain an unknown exact container member of a published pair/group. These are route refinements, not Heroic Hoarder route gaps. Present Poolside Cave Fur Cape is resolved to the lone chest in the B2 section-1 northeast terminal alcove; Coagulant is corrected from Hubble Castle to the lower-roof barrel of Hubble Past's western Inquisitory. The three formerly untyped shop-like rows have direct prices and typed shop inventory records.
- **Lucky Panel:** all published standard-matrix names now link to canonical items. GameWith and hyperWiki independently place canonical Scale Shield in Present Rank 1, adjudicating RPG Site's isolated `Shell Shield` wording as a retained source-error alias. The Version 1 Rank 2 singular `Slime Earring` legacy row remains stored despite being absent from the current direct table. Entry is independently verified as free. hyperWiki publishes source-native numeric selection cells (including 100, 50, 1, and 0), but no denominator or selection algorithm; they are retained as single-source weights and never displayed as item probabilities. All 303 normalized reward probabilities remain unknown.
- **Monster Hearts:** Dragonlord, Malroth, and Zoma have independently corroborated DLC Battle Arena turn thresholds and a cp020 gate after the Buccanham Past storyline. No source proves a repeatable Heart rematch/drop route, and no numeric Heart drop rate is stored. Metal Slime and Gold Golem retain explicit DLC acquisition notes without asserting DLC exclusivity where a non-DLC route is unverified.
- **Mini Medals:** no identity, location, locator, or independent-evidence gap remains. Source-specific closet/wardrobe and route wording differences remain visible.
- **Tablets:** no identity, fragment-location, or locator gap remains. Independent corroboration of the final placement/unlock behavior is still desirable but is not a registry gap.
- **Achievements:** no identity or structured non-story requirement gap remains. Remaining work is counter-semantics/in-game confirmation, not a missing achievement.
- **Missables:** all seven records have exact named action/window boundaries. Little Blue Button becomes unavailable at the late-game Cataclysm. A continuous Game8 Japan walkthrough directly places the trigger when leaving Estard Castle after the cp022 Ultimate-Key cleanup, before cp023's changed-world route. Immediate pre-trigger child presence remains unobserved; player completion is never inferred.
- **Conflicts:** 15 automatically detected claim-pairs remain unresolved, representing 11 distinct disputed source-level facts: 14 pairs across 10 equipment-compatibility identities and one `Stella Fan` / `Stellar Fan` display-name fact. Fishnet Stockings is resolved to Present Frobisher and Marshal Lourgh to the Past Exposure Enclosure route; every losing isolated-page claim remains auditable. Pirate's Hat likewise remains resolved to Past with both losing Present pairs visible. All 311 compatibility rows nevertheless have normalized two-publisher agreement; losing claims remain visible pending direct UI evidence.
- **Provenance:** required source-bearing tables pass locator and foreign-key validation. All 635 registered sources currently have retrieval dates within 180 days, but retrieval recency does not establish publication/patch freshness; indexed/snippet evidence is not promoted to canonical fact.

## Current residual batch order

1. Verify the legacy Version 1 Rank 2 Slime Earring row and Lucky Panel probabilities only from direct current-version evidence.
2. Seek explicit rematch or respawn evidence before adding any repeatable Heart route.
3. Preserve the complete 100/100 cross-source Mini Medal evidence set unless a direct source publishes a correction.

The `medal_report.py --through CHECKPOINT` query uses `available_checkpoint_id`, not physical location order, so later key-gated chests are excluded from early availability reports.

## Latest completed batch

The chronology adjudication pass resolves Fishnet Stockings to the Present
Frobisher inn's right-room wardrobe: Game8's dedicated Frobisher Past/Present
treasure tables agree with Eliteguias and override Game8's isolated item-page
Past label. It also resolves Marshal Lourgh to the Past Exposure Enclosure route:
Game8's continuous Curious Tablet walkthrough defeats him before returning to
the Present, matching Eliteguias and cp027. All three losing conflict pairs remain
visible and cited.

The late-boss corroboration pass gives Time Being a two-publisher Side Winder
group-pressure core while leaving multi-target-healer/item backup, resistance,
and revival details source-specific. Lourgh/Disorder now has two-publisher support
for Magic Barrier, elemental protection, magic damage during Barbatos physical
impairment, and Kiefer's autonomous contribution. That batch first exposed
Game8's Rucker Region Present versus Eliteguias Past disagreement; the later
chronology adjudication above resolves it to Past from Game8's continuous route.

The late fixed-gear pass independently corroborates Malign Shrine's Sunderbolt
Blade and Dark Robe, Estard Castle's Ultimate-Key Kingsblade/Pallium Regale/
Platinum Shield trio, and Burnmount's Magma Staff. The Estard teleportal deadline
and broader region sweep remain RPG Site-only. Sacred Armour remains a visibly
single-source extra beside the two-source Magma Staff core, and none of these
route cards asserts permanent missability or a universal best wearer.

The metal/medal/Heart power pass gives six more phone cards narrow atomic
two-publisher evidence. Roamer and Highendreigh now expose independently
corroborated Metal Slime companion-encounter routes while numeric rates and level
ceilings remain unknown; Highendreigh's Whistle tactic and observed 4F starting
point remain source-specific. Sage's Stone at 65 medals, Sacreder Armour at 80,
and Metal King Sword at 100 have independent reward-table support without
promoting checkpoint availability assumptions or wearer rankings. Cyclops Heart's
30% critical-damage increase is independently corroborated; using it for a
critical build is labeled synthesis, with no repeatability or drop-rate claim.

The exact-container follow-up resolves three more finite routes from independent
current-version Eliteguias walkthroughs: Kamikazee Bracer is the middle 5F chest
in Likeness of the Great Evil, the Wilted Heart Mountain Path Strength Ring is
the first chest before the bridge, and Burnmount's Yggdrasil Leaf is in the Level
2 south-exit chest. The finite-container residual falls from 12 to 9. Eliteguias
also independently places Fishnet Stockings in the Present Frobisher inn's
right-hand wardrobe, initially exposing two conflicts with Game8's isolated Past
item row. The later map-based adjudication above resolves both to Present.

The container-conflict follow-up resolves Pirate's Hat to Buccanham Palace Past.
Neoseeker's continuous palace route and Eliteguias's independent screenshot-rich
Past chapter agree on the 2F bedroom wardrobe pair; both losing Present conflict
pairs remain visible. GuíasPSN narrows Poolside Cave Fur Cape to the northeast
double chest and separates Silver Platter into the west chest, reducing the
finite-container residual to 12. Its Present Frobisher inn-wardrobe Fishnet
Stockings claim conflicts with Game8's Past Frobisher route and remains unresolved
with a translation/derivation caveat.

The fixed-gear corroboration pass gives four more checkpoint cards explicit
two-publisher cores: Hardlypool Tunnel's Ice Shield; Tallest Tower's Dragon
Claws and Staff of Sentencing; Grand Conjuratorium's Duplic Hat and Staff of
Antimagic; and the Aeolus route's Silver Mail, Lightning Staff, and Falcon
Blade. Highendreigh's Pillager's Platemail/Slime Crown, Hubble's post-Hybris
Lightning Staff, and the Sanctum Windbraker remain visibly one-walkthrough
extras. These cards recommend collecting free finite gear, not a universal
best wearer or ranking.

The actionable-power corroboration batch upgrades six phone cores. Tribulators
now leads with two-publisher manual healing safety while leaving Auto-Battle as
a Game8-only speed option. The cp011 La Bravoure Metal King Slime route and
critical-hit tactic are independently corroborated, with rate and level ceiling
still unknown. Luminary, Monster Wrangler, and Druid cards distinguish their
two-source Let Loose mechanics from editorial role/timing synthesis. The first
Orgodemir card now scopes verified Magic Barrier/reapplication to phase one and
shows the phase-two source disagreement—Game8's Magic Barrier versus
DQ7Reimagined.com's Insulatle—without pretending both are one recommendation.

The finite-container refinement batch applies the current-version RPG Site
walkthrough's exact directions to 28 formerly area-only routes. Eighteen now
identify the precise chest, closet, or drawer; ten more identify the exact room,
route, or container pair without guessing which paired container holds the item.
The unresolved finite-route queue falls from 31 to 13. Notable phone-ready
directions include both Prologue Leather Hats, the Rainbow Mines Pointy Hat,
L'Arca Hairband and Rabbit Ears, Grotta del Sigillo and Allblades Iron Lances,
Frobisher Scale Armour, Bandits' Base Silk Robe, Mount Gora Ogre Shield, and the
Alltrades Abbey B1 northeast Lucida Shard. Fishnet Stockings was still unresolved
at that stage; the later dedicated Frobisher map and continuous walkthrough
adjudication resolves it to Present.

The shop-price closure batch types the last three purchase-like acquisition rows.
Direct current-version Game8 pages establish Dragon Robe at 19,000 gold and
Enchanted Armour at 21,000 gold in Rucker Castle Past, plus Pilchard Pie at 10
gold in Pilchard Bay. All three now join canonical shops and inventory rows with
checkpoint gates and exact table/item locators; no unknown shop price remains.

The early-game vertical slice now includes direct tactical coverage for the Tribulators, Golem, Tinpot Dictator, and Florin alongside the existing bosses through Alltrades. It supports explicit completed-check tracking, checkpoint-focused output, honest medal state, conditional threshold advice, operational STOP warnings, and checkpoint-scoped conflict alerts. Unsupported advice remains an explicit gap; no levels or grind rates were invented.

The Ballymolloy/Frobisher corroboration pass independently confirms Golem's Buff plan, Crabble-Rouser's Dazzle/Fire/Buff plan, Maeve's Fire/Buff/support plan, and Tinpot Dictator's focused-target Buff, group-damage, and resource-conservation plan. Golem's Fire weakness and Maeve's inability to be Dazzled remain explicit single-independent-source findings with no invented numeric resistance. Tinpot Dictator is correctly scoped to `cp_007_frobisher`; Emberdale's `cp_004_emberdale` boss remains Glowering Inferno.

The first Allblades Arena control pass independently matches Game8 and NoobFeed
on Numpton's opening round: use multi-target damage on the three Drake Slimes and
have Ruff use Aooo! to stop Numpton. The tactic is now two-source verified, while
the Wolf Boy rank-4 unlock cell remains separately sourced and is not promoted by
the strategy corroboration. Game8's explicit conserve-HP/MP framing remains a
single-source detail for the four-fight sequence.

The Glowering Inferno pass adds a two-source cp004 phase plan: use Ice/Water attacks normally, then switch to physical attacks while its glow raises Ice resistance. Hero support and frequent party-shield Let Loose use are independently corroborated. GameWith's full-party Defend response after Muster Strength remains explicitly single-source; suggested level, approximate HP, and numeric resistance values are not promoted.

The remaining Allblades Arena pass independently corroborates round 2 multi-target damage plus recovery, round 3 Muddy Hand priority plus Hero's Let Loose, and round 4 multi-target damage, Bound restraint, and green-HP safety. Nava's Repel/physical response and default-vocation Ruff Call of the Wild tactic remain explicit single-source options.

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

The monster expansion now has 476 checkpoint-gated encounter routes covering all 333 monsters and 227 verified drop rows across 196 monsters. Independent current-version sources corroborate exact routes for Cannibox, Urnexpected, Vicious Fandangow, Vicious Kisser, Vicious Scrapper, Damned Well, Mothertoad, Dark Gryphon, Miry Hand, and Miry Mudraker. RPG Site's exact Silver/Gold Arena rosters for ten members are independently matched by a current-version Steam 100% achievement walkthrough. Only Scarewell's precise Neoseeker route remains explicitly `single_independent_source` and is not promoted to verified.

The current boss-advice audit adds three directly sourced early-game tactics: the scripted-loss and item-only recovery rules for Rashers and Stripes, multi-target damage plus Fizzle control for the Mild Bunch, and Leg Sweep/Dazzle/support alternatives for the Mighty Pip. The Mighty Pip row explicitly preserves the source's incompatible Ruff role alternatives instead of presenting both vocations as one simultaneous build.

The Alltrades boss corroboration pass independently verifies Cardinal Sin's
Let Loose/Burst survival response between Game8 Japan and Altema: defend to reduce
both incoming damage and the boss's damage-based healing. Sap and Dazzle remain
clearly labeled single-publisher control options. Game8 and Altema also independently
confirm that the first Rashers and Stripes encounter is an unwinnable story loss and
that the rematch requires carried recovery items while spells and skills are sealed.
The English Game8 target order remains explicitly single-source rather than being
promoted with those verified core facts.

The Alltrades party pass independently matches each recommended early role: Hero
Warrior and Maribel Mage through GamerBlurb, and Ruff Priest through GamerHour.
These are attributed editorial recommendations. Only Game8 publishes the exact
three-person Arena composition, so the phone guide labels the individual roles as
two-source while retaining the complete trio as single-source.

The final combat audit adds three directly sourced late tactics: summon priority and poison preparation for the Slamphibians, the forced Sir Mervyn solo constraint for Smothers, and Water-Spirit-first priority plus Dieamend/Magic Barrier preparation for the Four Spirits. Later batches complete equipment compatibility and slot counts and establish Moonlighting's any-two-distinct-available-vocations rule. Residual evidence blocks include numeric farm/drop/encounter rates and a proven repeatable Heart route. No suggested level or inferred rate is normalized.

The item-route normalization batch links 44 existing source-verified monster drops into checkpoint-aware acquisition paths. This gives 19 Heroic Hoarder items a renewable enemy-drop alternative to Lucky Panel and reduces items represented only by Lucky Panel paths from 40 to 21; each route retains the direct monster-page drop and location locator.

The first Monster Heart batch adds a forward-compatible registry and 12 directly sourced effects covering the earliest entries through Mud Mannequin Heart. Golem Heart is gated at Ballymolloy from explicit availability evidence; the other 11 acquisition windows remain unknown, and the Metal Slime Heart note preserves its documented DLC scope without claiming a non-DLC route.

The second Monster Heart batch completes all 46 current-version identities and effects. Availability remains unset for 45 Hearts, and both Metal Slime Heart and Gold Golem Heart retain the source's Jam-Packed Swag Bag DLC scope without implying exclusivity or a non-DLC route.

The acquisition-link batch reuses independently sourced item-acquisition rows to expose checkpoint, period, method, supply, source, and locator on Heart details. Earliest playable examples now include Slime/Golem/Hammerhood at cp003, Bodkin Archer/Little Devil at cp004, Healslime at cp005, and additional fixed/drop routes through cp011. No stored numeric drop rate or acquisition DLC scope exists, so both remain explicitly unknown; unmatched Heart/item names remain unlinked.

The remaining-heart audit directly links Meowgician Heart to the finite Vicious Meowgician reward/drop in L'Arca Past at `cp_005_larca`. Its dedicated page proves the exact identity and monster source, while the existing encounter page supplies the checkpoint gate; drop rate and repeatability remain unpublished, so it is not labeled renewable. Metal Slime and Gold Golem Hearts are directly documented as Jam-Packed Swag Bag DLC grants. NightlyGamingBinge and Game8 independently establish Dragonlord, Malroth, and Zoma as DLC-only Buccanham Palace Battle Arena rewards with 25-, 50-, and 40-turn conditions; Game8 and RPG Site place Arena availability after Buccanham Past at `cp_020_buccanham`. All five exact identities remain outside the shared item registry until their non-Heroic item semantics are normalized.

The missable audit gives all seven records precise direct-source locators and exact action boundaries. It corrects the Vogograd reward to Pretty Betsy and records the irreversible Wrecked Specs, Wooden Doll branch confirmations, Wiggles, and Kiefer choices. A later two-source batch resolves Little Blue Button's boundary to the late-game Cataclysm.

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

The prior residual-name audit resolved `Iron Claw` to the current UI's plural `Iron Claws`, `Scholar’s Glasses` to the dedicated page/UI identity `Scholar's Specs`, and the source typo `Scake Armour` to `Scale Armour`; each matrix route retains an explicit adjudication marker. At that stage `Shell Shield` remained unresolved because no dedicated current-version identity or UI entry had been found. RPG Site directly publishes the legacy singular Slime Earring row but describes its lists as potentially non-exhaustive; Game8 corroborates generic Lucky Panel availability without a version/rank. Neither direct source publishes entry costs or numerical reward probabilities, so those fields remain unknown.

The Scale Shield adjudication closes the last standard-matrix identity gap without inventing a new item. GameWith and hyperWiki independently place うろこの盾 (canonical English Scale Shield on Game8's dedicated item page) at Present Pilgrim's Rest Rank 1, exactly where RPG Site alone prints `Shell Shield`. The published wording remains searchable as an alias and in an atomic claim, while the normalized Version 2 Rank 1 reward targets Scale Shield. Its probability remains `null` because none of the sources publishes a draw denominator or algorithm.

Dedicated current-version helmet pages add four early finite/free routes: Leather Hat in Pilchard Bay and Estard from `cp_001_prologue`, plus Pointy Hat in Past Rainbow Mines and Hardwood Headwear in Present Ballymolloy from `cp_003_ballymolloy`. The pages publish areas but not exact containers, which remains explicit.

Adjacent dedicated armour pages add Noble Garb in Past Institute of Automatry at `cp_007_frobisher` and Silk Robe in Present Bandits' Base at `cp_010_alltrades_present`. Both are finite/free alternatives to Lucky Panel with exact containers explicitly unpublished.

The next direct-page batch adds Edged Boomerang in Past Faraday Castle at `cp_007_frobisher` and Fur Cape in Past Poolside Cave at `cp_009_alltrades`; both finite/free routes preserve the unpublished exact container.

The next accessory pass upgrades Rabbit Tail from an area-only Heroic entry to the exact Grotta del Sigillo Level 3 chest at `cp_005_larca`, using the current L'Arca walkthrough. It also adds a second finite/free Fishnet Stockings route in Past Frobisher at `cp_007_frobisher`, with the exact container still unpublished.

Three further direct-page routes add Hardwood Headwear in Past Faraday Castle (`cp_007_frobisher`), Fur Cape in Present Poolside Cave (`cp_010_alltrades_present`), and Silk Robe in Present Temple Palace (`cp_011_la_bravoure`). Each is finite/free and retains the source's unpublished exact container.

The direct L'Arca walkthrough also upgrades Sledgehammer from a generic Grotta del Sigillo chest to the exact Level 4 route: climb the stairs before going outside and open the exterior chest. This preserves the existing `cp_005_larca` gate while making the free alternative actionable before purchase decisions.

The early-power stat audit independently corroborates Sledgehammer's +26 Attack and -20 Agility through dedicated current-version Game8 and GameWith pages. The cp005 phone advice now presents it as a free high-attack option with a clear turn-order tradeoff, rather than implying it is universally strongest.

The Ruff early-power audit independently corroborates Windcheater's +33 Defence, +50 Deftness, qualitative enemy-drop boost, 15-Medal route, and Ruff legality through dedicated current-version Game8 Japan and GameWith pages. The cp007 and cp009 phone advice now surfaces those verified payoffs while preserving the four-piece Ruff loadout as a single-source editorial recommendation. A separate table publishes a 6% drop increase, but that numeric rate remains single-source and is not promoted.

The current Roamer walkthrough refines Past Poolside Cave Fur Cape to the Underground Level 2 northern-corner chest pair reached by falling through the northwest pits. The page identifies the pair's two rewards but not which individual chest contains the cape, so that remaining ambiguity is explicit.

The farming audit adds precise provenance and checkpoint gates to all eight routes, separates factual target/location evidence from attributed strategy provenance, and removes unsupported generic tactics. Metal-enemy frequency remains qualitative because the direct source publishes no numeric encounter rates; the repeatable Almighty-and-Spirits reward is sourced separately from Game8's recommended Magic Burst composition.

The Seed normalization batch records fixed current-version increases for all nine standard Seeds and nine Super Seeds. It separately models the repeatable cp032 Almighty-and-Spirits rematch as one random Super Seed per victory while leaving the eligible-item pool unknown because the direct farming source does not enumerate it.

The provenance-completeness batch adds non-empty direct-page row locators and verification states to all 19 Medal rewards, 26 Vocations, and 27 vocation-prerequisite edges. Direct RPG Site heading audits now map all 33 checkpoints to exact chapter/section ranges. Every checkpoint remains visibly `seed_partial` because complete locator coverage does not imply complete walkthrough or optimization coverage.

The Phase 2 equipment batches established typed item, shop, and Lucky Panel acquisition routes for 30 Heroic Hoarder items, including the shield sequence through Shield of Shame. Unspecified containers and pool ranks remain explicit evidence gaps. The Elevating Shoes exclusivity conflict is now resolved to the dedicated current-version item page: Metal King Slime is a second acquisition method, while its numeric drop rate and earliest gated encounter remain unknown. Mini Medal 78 is resolved to The Beacon Past 3F south-balcony chest because RPG Site's precise route is independently matched by a current-version screenshot guide; Game8's second-level label is retained as a resolved conflicting claim. Tempest Shield is no longer a conflict: Game8's dedicated Present Sanctum table supports one fixed treasure, while Game8's Wind Spirit walkthrough and RPG Site independently support a later Ventus Tower 2F chest. Both are normalized as finite free copies under a multi-location acquisition predicate.

The achievement-readiness batch makes all 29 structured completion dependencies state-aware in the API and browser. Heroic Hoarder, Monster List, Vicious, tablet, vocation, and medal progress now distinguishes explicit partial counts, met counters with an unrecorded unlock, and unknown tracking. Empty identity arrays are no longer presented as zero; only a deliberately saved numeric Mini Medal count can establish exact zero.

The equipment-readiness audit confirms that item categories provide nominal slots and checkpoint advice provides a bounded set of attributed character/item recommendations, but the KB has no complete current-version character equipability matrix, accessory slot count, or duplicate-equip rules. The browser therefore keeps equipment writes disabled and exposes a read-only saved-checkpoint comparison with canonical items, route availability, explicit ownership, raw recorded gear, and the precise validation gaps instead of accepting potentially invalid loadouts.

The recursive vocation-planning batch expands all 10 sourced prerequisite groups / 27 edges into a complete per-character dependency tree in vocation details. It preserves every `all_of` and `any_n_of` branch, character exclusivity, group provenance, and explicit mastery state, then surfaces all currently derivable next mastery options without ranking alternatives. Numeric mastery/proficiency cost and absent mastery remain unknown.

The interactive walkthrough readiness pass makes completion STOP obligations explicitly checkable before the normal action list, replaces opaque “Step N” labels with sourced subjects, and marks only the first open action as next. Mini Medals are now structurally separated into current/backtrack checkboxes and a collapsed later-gated reference list, preventing early players from hunting inaccessible medals.

The safe-advancement pass adds a conservative checkpoint readiness summary over explicit STOP and required-obligation state, while separately reporting optional work and unrecorded available medals. The browser distinguishes browsing from advancement and offers an explicit “Confirm and set next current” action only after structured blockers are cleared at the saved checkpoint; the sourced prose exit condition always requires player confirmation and is never inferred.

The checkpoint-ledger synchronization pass surfaces all 71 canonical tablet fragments at their directly sourced availability checkpoints with stable IDs, ordinals, locations, provenance, and explicit found state. Walkthrough checkboxes reuse the validated Tablets-registry mutation, so either view updates the same player ledger; saved-story progress never implies fragment collection.

The finite-item synchronization pass groups checkpoint-gated finite Heroic Hoarder routes into one canonical item checkbox per checkpoint opportunity, preserving alternate routes and provenance without inferring which copy was taken. Walkthrough item and monster controls now have integration coverage proving they share the Items and Monsters registry ledgers; renewable acquisition rows remain in item detail instead of cluttering the live checklist.

The checkpoint-achievement pass separates achievements with an exact completion checkpoint from counters that only begin tracking there. Due rows reuse the validated Achievements-registry checkbox; open-ended counters remain collapsed, read-only progress reminders. Story position never implies an unlock, and checkpoint/registry integration coverage verifies explicit changes remain synchronized and reversible.

The missable-ledger pass normalizes checkpoint and obligation links for all seven current-version missable records and activates the existing explicit completed/missed player fields. Completing a missable synchronizes only its linked checkpoint obligation and registry state. Verified linked STOPs clear reversibly; Little Blue Button now has a separately sourced final warning at cp022.

The interactive-runtime hardening pass serializes threaded browser mutations and atomically replaces player-state files, preventing rapid checkbox writes from losing progress or exposing partial JSON to concurrent reads. An eight-way integration test records distinct items concurrently and verifies all survive with no temporary files left behind. The existing Windows launcher is joined by a dependency-free macOS/Linux launcher; both preserve the same explicit-state server workflow.

The retrieval-quality audit adds six golden question/evidence bundles covering
safe advancement, strongest legal gear, vocation paths, checkpoint-available
farms, Monster Hearts, and conflicts. It requires precise locators, checkpoint
scope, independent corroboration where claimed, preserved player unknowns, and
no explicitly PS1/3DS-scoped source leakage. Checkpoint actions now expose their
own citations, farm retrieval supports `through_checkpoint`, and conflict rows
expose both source IDs.

The first-use end-to-end audit exercises a blank temporary save through the
Prologue and early-game walkthrough over the HTTP server. It verifies STOP/action
citations, medals, tablets, finite items, monsters, Hearts, vocations, checkpoint-
available farms, and full rollback without touching Ryan's state. The browser now
reloads checkpoint-scoped farms when the viewed checkpoint changes and labels
future-gated Hearts as `later`, not `available`.

The earlier Moonlighting venue re-audit kept the conflict unresolved because the English sources described different venues without showing the transition. A later expanded-source batch resolves it as process-stage ambiguity: three independent current-version Japanese walkthroughs agree that the Career Sphere event triggers at the Shrine of Mysteries, transports the party to Alltrades Abbey, and activates Moonlighting there.

The expanded systems batch adds two-source Lucky Panel limits (three attempts per in-game day, reset by staying at an inn). A later audit independently corroborates free entry through GAME攻略BOX and Game8 Japan. hyperWiki's raw selection cells remain single-source, source-native weights because no denominator or draw algorithm is published; they are not probabilities. Official and independently maintained sources establish that both assigned Moonlighting vocations provide their skills/spells/perks and gain proficiency, while learned skills stop being available when their vocation is no longer assigned. Normal-setting proficiency is scoped to 1 point for an overworld instant defeat, 5 for a regular entered battle, and 10 for a boss/special battle. Luminary's matching two-source rank costs are normalized through 480 cumulative points; disagreeing numeric stat cells remain visible claims and are not promoted.

The Stella/Stellar Fan re-audit also remains unresolved. Game8's dedicated current-version page consistently uses `Stellar Fan`, while RPG Site says its `Stella Fan` checklist spelling follows the in-game menu; neither available page exposes a legible English UI capture that directly adjudicates the name. Search and item detail continue accepting both spellings through the sourced alias, and conflict details now require an Item List, inventory, shop, or acquisition-result capture with the complete name visible.

The vocation readiness batch adds direct unlock planning to every vocation detail. Intermediate and advanced requirements retain their sourced `all_of` or `any_n_of` semantics, candidate names, required count, locator, and URL. Per-member status uses only explicit mastery records: satisfied thresholds are recognized, while absent records remain unknown and conditional remaining counts are labeled accordingly. Numeric mastery cost remains unknown rather than being inferred from eight-rank skill tables.

Phase 1 completed all 100 normalized Mini Medal locations, now with 100 independent RPG Site evidence rows, a 33-checkpoint spine through postgame, and 45 directly checked obligations. RPG Site's parenthetical medal ordinals remain source-specific walkthrough order and are never treated as canonical album IDs.

## Open questions requiring evidence

- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Exact membership of the postgame random Super Seed reward pool; all 18 fixed Seed/Super Seed effects are already normalized.

## Authoritative residual-evidence audit

Audited 2026-08-29 against a clean generated database. The browser's four-item
evidence-gap list is a curated research queue, not the total number of disputed
database facts. The API therefore reports it separately from automatic conflict
pairs.

- **Curated research queue:** 4 items: 1 single-source, 1 unsupported, and 2
  corroborated-but-unresolved. None can be safely closed from the currently
  registered evidence. The Blue Button row now isolates only immediate pre-trigger
  presence; its cp022-to-cp023 event mapping is directly evidenced.
- **Automatic conflicts:** 15 unresolved claim-pairs represent 11 distinct fact
  scopes. Ten are equipment-compatible-character lists (14 pairwise conflicts),
  and one is the Stella/Stellar Fan display name. Fishnet Stockings and Marshal
  Lourgh chronology are now resolved from location-specific and continuous
  walkthrough evidence, with their losing claims preserved. Resolving the
  remaining equipment/name facts requires a legible
  current-version English equipment/inventory UI capture that shows the relevant
  character list or full item name. Additional guide consensus is not treated as
  equivalent to direct UI evidence.
- **Little Blue Button:** Game8 Japan and GameWith independently name the
  late-game Cataclysm (`異変`) as the boundary. A separate continuous Game8
  Japan walkthrough places the trigger when leaving Estard Castle after the
  cp022 Ultimate-Key cleanup and before the cp023 changed-world route. No source
  checks the child immediately before that trigger; completion remains unknown
  until reported.
- **Lucky Panel probabilities:** requires a published draw algorithm/denominator
  or controlled sampling/source-code evidence. Source-native numeric weights are
  not probabilities.
- **Repeatable Heart farming and numeric farm rates:** requires explicit
  respawn/rematch evidence for a Heart route and, for rate claims, a reproducible
  benchmark with patch, platform, difficulty, party/build, route, duration,
  attempts, and rewards. A monster drop listing alone does not prove repeatability
  or a rate.
- **Patch/platform scope and remaining editorial assumptions:** require source- or
  UI-level version evidence. They remain answer-time qualifications rather than
  silently inferred global facts.
- **Freshness:** all 635 source records currently have retrieval dates within 180
  days (0 stale, 0 unknown by retrieval date). This measures retrieval recency,
  not whether a publisher updated a page for the current patch.

The equipment residual batch independently corroborates the two formerly
single-source armour compatibility rows. GameWith's current-version armour list
matches Game8 Japan for Party Dress (Maribel and Aishe) and Metal King Armour
(Hero, Maribel, Ruff, Aishe, and Sir Mervyn), using visible active-character
icons and matching item stats to bridge the Japanese display-name variants.
This raises two-publisher compatibility coverage to all 311 rows. The later slot-layout
batch separately verifies the one-each non-accessory counts; same-item accessory/Heart
duplicate and effect-stacking behavior remains unverified.

The next compatibility adjudication adds GameWith's weapon and shield matrices.
Its active-character icons match Gamers-High for Liquid Metal Sword (Hero,
Maribel, Ruff, Aishe, and Sir Mervyn) and Game8 Japan for White Shield (Hero,
Maribel, and Aishe). All disagreeing HyperWiki, Game8, and Gamers-High claims
remain stored and visible; the matching independent pairs provide the normalized
legal lists. GameWith's Iron Lance row matches none of the three then-existing lists,
so it remains a visible disagreement rather than determining the normalized row.

The Iron Lance adjudication adds AppMedia's current-version item page. Its exact
compatible-character list (Hero, Kiefer, Ruff, Aishe, and Sir Mervyn) matches
HyperWiki, establishing the final two-publisher audit consensus. Game8 Japan,
GameWith, Gamers-High, and GameDeep publish differing lists; each claim remains
stored and conflicted rather than overwritten. Character compatibility is now
normalized for all 311 equipment rows. Non-accessory slot counts are now separately
verified; same-item accessory/Heart duplicate and effect-stacking behavior remains
unverified.

The slot-layout batch promotes one weapon, one shield, one helmet/head item, and one
armour/torso item per playable character. Gamers-High directly states that accessories
alone receive two equipment slots; Hobby Consolas independently and consistently
enumerates one of each non-accessory category plus Accessory 1 and Accessory 2 across
early-, mid-, and late-game character loadouts. Character legality remains governed by
the complete 311-row compatibility matrix. Monster Hearts still consume accessory
slots. Hobby Consolas shows one repeated accessory in a sample loadout, but no second
independent current-version source establishes same-item legality or effect stacking,
so that narrower duplicate rule remains explicitly unpromoted.

The cp009 Hero power batch independently verifies Cautery Sword's +42 Attack and
one-group battle-use flame effect between Game8's dedicated English item page and
D-navi's current-version weapon table. Altema separately matches Game8's complete
early Hero recommendation through Alltrades Abbey: Cautery Sword, Iron Armour,
Magic Shield, and Iron Mask. The normalized advice keeps the free fixed Sword and
Mask plus 20-medal Shield ahead of optional Lucky Panel grinding for Iron Armour;
the older Game8 location error remains resolved rather than silently restored.

The same cp009 defensive pass independently matches White Shield's +19 Defence,
6% block chance, and 10% fire-damage reduction between its dedicated Game8 and
GameWith pages. These cells are exposed on Maribel's phone gear card without
upgrading the broader partial-build recommendation beyond its attributed source.

The Arena roster corroboration batch matches all ten Silver and Gold Cup members
between RPG Site and Nerthing's independent current-version Steam achievement
walkthrough. Each corroborating roster claim has an exact cup/challenge/member
locator and the existing cp020 gate is unchanged. These ten routes are now
verified; Scarewell remains the only single-independent-source encounter route.

The final-boss summon audit resolves Miry Mudraker's exact mechanism. Game no
Monochrome's current-version Orgodemir strategy states that the flesh-flinging
action summons one Miry Hand and one Miry Mudraker, independently matching the
Dragon Quest Wiki's Cathedral of Blight boss listing. The route is now tied to
the cp028 final Orgodemir battle; no unsupported turn or phase number is added.
Searches found only area-level or generic farming corroboration for Scarewell,
not a second source matching Neoseeker's exact fixed position west of Hardlypool,
so that last route remains explicitly single-source.

The early Hackrobat/Slaughtomaton pass adds two direct current-version NoobFeed
full pages as independent corroboration for the existing Game8 plans. Hackrobat's
Fire damage, Hero support role, and Hero Aqua Slash into Kiefer Lightning setup
are now two-source verified; the Buff opener remains explicitly single-source.
Slaughtomaton's Crack, Lightning Slash, Aqua Slash setup, and Hero Buff/Heal role
are likewise two-source verified, while NoobFeed's Ruff MP fallback remains
single-source. Aqua Slash's rank-4 unlock evidence stays separate and is not
upgraded merely because the boss tactic is corroborated.

The cp008 pass adds direct GameWith corroboration for Florin and the Guardians of
the Roamers. Florin's Aqua Slash and Lightning Slash setup is now two-source,
while Buff and Ruff support remain single-source. The Guardians' Hero-plus-Aishe
constraint, healing-item preparation, and Jovan/highest-physical-threat priority
are two-source; best-gear wording and defending after charge-up remain explicitly
single-source. Skill-rank evidence remains separately scoped.

The cp017 power pass independently matches Game8 and Power Up Gaming on
Gladiator's Flashback role: high physical boss burst in exchange for abandoning
Defence. The phone advice is now conditional on explicit Warrior and Martial
Artist mastery, so reaching Hubble alone never asserts that Gladiator is legal.
Power Up Gaming's global tier placement remains attributed opinion rather than
canonical truth.

The cp019 Cumulus Vex pass independently matches Game8 and Into Indie Games on
the recurring Sky Fry summons and the efficient multi-target response. The phone
plan now leads with group damage that controls summons without dropping boss
pressure. Game8's Wind-resistance and keep-HP-high precautions remain explicitly
single-source extras; neither was promoted by the summon corroboration.

The cp013-cp014 Hardlypool boss pass adds direct NoobFeed corroboration for the
Sunken Spirits group plan, Gracos's accuracy-and-element switch, Ethereal
Serpent's anti-airborne/debuff plan, and Gracos V's party Buff plus Fire plan.
GameWith independently confirms sealing King Slime's Midheal with Fizzle. The
leave-one-Spirit recovery window, exact Dazzle and Flying Knee tools, King
Slime's Attack-down/Buff plan, and Gracos V's poison/Let Loose details remain
explicitly single-source. Conflicting Highendreigh period labels remain visible;
this tactical batch does not silently resolve chronology.

The cp023 pass adds two-source current-version support for Fire resistance
against Fire Spirit and for the forced solo Sir Mervyn constraint against
Smothers. Fire Spirit's multi-target healer, Magic Barrier, and named Dragon
gear remain explicitly single-source. Smothers's offence/healing cycle and
Neoseeker's physical-weakness plus encounter-regeneration observations also
remain single-source; no damage estimates or recommended levels were promoted.

The cp030/cp032 postgame pass independently corroborates The Almighty's
elemental defence, group-recovery, and post-dispel support loop with Game8 and
GameWith. Xenlon's Fire/Ice protection and healer-plus-buffer roles now have
independent GameWith/gameplay support alongside Game8. Exact status counters,
revival-item economy, defensive pre-Burst buffs, breath reflection, and Astoron
remain attributed single-source tools. Suggested levels, numeric HP floors,
turn targets, and weaknesses were deliberately not promoted.

The remaining early/mid boss pass adds GameWith corroboration for neutralizing
Mild Bunch's Rogue early, maintaining Buff and recovering from Skeleton
Squire's group attack, and using Buff plus recovery during Setesh's counter
stance. Exact Fizzle/AoE sequencing, target orders, elemental options, MP
attrition, and Priest assignment remain single-source. No independent publisher
was found for the Tribulators tutorial plan, so Auto-Battle and Medicinal Herb
advice stays explicitly single-source. Levels, numeric HP, and weakness tables
were not promoted.

The early boss evidence-label audit aligns Golem, the Crabble-Rouser/Maeve
sequence, and Tinpot Dictator phone rows with their existing atomic claims. Each
core plan now displays verified confidence because two independent current-
version publishers agree. Applicability notes preserve the narrower one-source
boundaries: Golem's exact role/resource note, Maeve's Dazzle resistance, and the
Tinpot Dictator Kiefer Let Loose caution. No underlying tactics or player state
were changed.

The cp001-cp009 evidence-link migration now gives all 19 early advice rows that
claim a two-source tier explicit `evidence_claim_ids`. Every linked core resolves
to at least two distinct source IDs. Mixed rows link only their corroborated
core; source-specific options remain represented by their existing advice status
and are not included as badge evidence.

The cp028 final Orgodemir pass matches Game8's Cathedral walkthrough and
Korosenai's direct phase guide on sustained Magic Barrier coverage and group
attacks against the phase-four hands. The phone plan leads with those verified
survival anchors. Priest Benediction for the phase-three max-HP curse remains
explicitly one-publisher evidence, and no exact level, heart loadout, weakness,
or scripted damage rotation is normalized.

The cp032 Spirits pass now keeps its two encounters separate. For the standalone
Four Spirits, Game8 and Neoseeker agree on Water Spirit first and Magic Barrier
after Water falls; Dieamend stocking remains Game8-only. For the later Almighty
plus Spirits fight, both agree to remove spirits before tether and switch to the
Almighty once they are linked. Their exact pre-tether order conflicts—Game8 says
Wind then Fire, while Neoseeker says Water then Wind—so both claims remain visible
and unresolved rather than being collapsed into a false canonical order.

The midgame anti-magic pass adds direct Korosenai corroboration for the Envoy
and Vaipur. Envoy physical offence is verified across two guides, while Game8's
opening Fizzle and Korosenai's Bounce wording remain separate mechanism notes;
multi-target healing and Sleep cleansing remain source-specific extras. Vaipur's
party spell resistance and offensive-buffer roles are two-source verified, while
Hymn of Air/Let Loose, double Magic Barrier, and named rotations remain attributed
to their individual guides.

The cp018 Gasputin pass matches Into Indie Games and Korosenai on the safe
Silence response: spells become unavailable, so switch to physical attacks.
Game8 describes a broader skill lock instead; that scope remains explicitly
disputed, and its healing/revival-item fallback, poison cures, and pre-lock
debuff plan remain source-specific. Korosenai's Magic Barrier/Slow rotation is
also retained only as a single-source extra.

The cp010-cp019 evidence-link migration gives all 15 remaining midgame advice
rows that claim a two-source tier explicit `evidence_claim_ids`. Each linked
core resolves to at least two distinct publishers. Mixed advice links only the
corroborated core: exact skills, rotations, recovery timing, resistance notes,
and other one-publisher extras remain outside the phone badge evidence.

The Rainiac/Hybris evidence pass verifies only the independently corroborated
phone core. Game8 and Neoseeker support safe-HP recovery against Rainiac's
possible second action and party-wide attack; Buff, Fire/Light, status cures,
Dazzle, and Kasap remain publisher-specific. Game8 and Neoseeker support
physical offence during Hybris's Magic Barrier and multi-target healing; exact
buffs and GameWith's named elemental-mitigation skills remain single-source.
No recommended level, numeric HP, resistance, or weakness table was promoted.

The cp009-cp012 vocation audit adds explicit two-source evidence for the
Warrior/Mage/Martial Artist prerequisite-coverage graph and for Moonlighting's
resolved trigger-to-activation sequence. Moonlighting now states the actual
gate, Shrine trigger, Alltrades activation, and two-distinct-vocation rule.
Choosing those three beginner vocations remains an attributed efficiency
inference rather than a mandatory build, and no universal Moonlighting pair is
asserted. Existing Priest, Mage, and rank-8 Martial Artist recommendations keep
their narrower editorial or skill-table evidence boundaries.

The cp020 boss pass verifies Togrus Maximus party-Defence setup across Game8 and
Korosenai; exact double-Kabuff, resurrection, and multi-target-healing details
remain publisher-specific. For the Slamphibians, both publishers verify group
damage across all three enemies. Target priority stays disputed because Game8's
dedicated boss page and Korosenai say smaller frogs first while Game8's own 100%
walkthrough says Mossferatu first due to revival. Poison-cure preparation remains
Game8-only and is excluded from the verified-core evidence badge.

The cp018-cp023 intermediate-vocation pass verifies five distinct power roles
across Game8 and Power Up Gaming: Paladin survival tank, Sailor party buffer,
Armamentalist elemental offence/defence, Sage echoed spell damage/recovery, and
Pirate sustained physical ramp. Advice remains conditional on the normalized
mastery gates (or Alltrades story access for Sailor), and each row states the
cost of choosing that role over burst, recovery, or another specialist. Exact
Sailor stat buffs and Paladin mitigation mechanics remain Game8-specific detail.

The cp015 Miracle Sword pass verifies its +100 Attack, +28 Charm, 25%-of-attack-
damage self-heal, and 55-Mini-Medal route across direct Game8 and GameWith item
pages. The existing independent equipment matrices agree that Hero, Aishe, and
Sir Mervyn can equip it. Phone advice now says to equip it immediately on the
active physical sword user once the saved medal count reaches 55, while clearly
avoiding a claim that it outranks every available elemental or utility weapon.

The cp020 optional-power pass verifies Heavy Metal Hole Past and The Beacon Past
as Liquid Metal Slime farms across Game8 and GameWith. Both recommend critical-
hit and multi-hit skills. The phone card keeps this grind optional and retains
unknown encounter rate and numeric stopping level instead of inventing a target.

The earlier late single-source boss audit promoted Macho Picchu's party-Defence setup
and post-Let-Loose burst window after direct current-version agreement between
Game8 and Korosenai. Great Leveller, attack reduction, exact stack counts,
party composition, levels, weaknesses, and rotations remain source-specific or
unknown. A later direct-page audit found independent actionable sources for Time
Being and Lourgh/Disorder: their narrow shared cores and source-specific extras
are now normalized above. Lourgh's chronology disagreement was then exposed as
an automatic conflict and is now resolved to Past by continuous-route evidence.
Neoseeker also supplies the independently adjudicated
first-Orgodemir phase-one Magic Barrier core; phase-two recommendations remain
split and visible.

The advanced-vocation audit promotes Hero's worked-up ability gate and exact
unlock rule after direct Game8/GameWith agreement: Hero requires mastery of any
three of the seven Intermediate vocations, and its reserved abilities are
available only during Mark of the Hero/Burst. The cp030 phone row now carries
the complete mastery pool and cp012 Moonlighting story floor; assigning routine
healing elsewhere remains an explicit editorial tradeoff, not a sourced fact.
No independent direct page was found that corroborates the existing exact
Showtime!, Positive Reinforcement, or four-turn That Special Summon usage advice,
so Luminary, Monster Wrangler, and Druid remain single-source rather than being
upgraded from general tier/build opinions.

The late-gear usability audit promotes the 90-medal Uber Gringham Whip as a
compact Hero power spike after Game8 and GameWith independently recommend that
assignment; RPG Site and GameWith agree on the acquisition gate, while Game8
and GameWith agree on +162 Attack, +40 Charm, and equal normal-attack damage to
all enemies. The phone row explicitly prefers comparison with a compatible
single-target weapon for bosses and makes no universal best-in-slot claim.

The postgame power-gap audit adds an optional cp032 Platinum King Jewel leveling
card. Game8 and GameWith independently identify Yet Another World as the
postgame farm; GameWith alone supplies the Whistle shortcut and map-transition
refresh loop. Spawn rate, time-to-level, and a mandatory level ceiling remain
unknown, so the phone card stops at comfort for the next arena or superboss.

The cp030 defensive power audit upgrades the Metal King Shield phone card with
two-publisher stats and effect (+75 Defence, +10% block, 10% all-element damage
reduction), the verified 95-medal gate, and Game8/GameWith's attributed Hero
assignment. The card explicitly permits encounter-specific redistribution among
legal wearers and does not promote the editorial build to a universal ranking.

The early gear usability pass makes Maribel's optional Alltrades setup and the
Present Steel Helmet opportunity phone-ready without claiming a complete
ranking. Snooze Stick's stats and battle-use sleep attempt link to matching
Game8/GameWith facts; its assignment and Maribel's other slots stay attributed
or optional. Steel Helmet's +41 Defence and Present Pilgrim's Rest rank-3 route
are independently matched, while assigning it to Hero is conditional on
legality and an actual improvement. The random-panel tradeoff remains explicit.

The cp001-cp011 power-gap audit corrects the 20-medal Magic Shield phone row.
Game8 and Altema independently assign it to the early Hero build, while Dragon
Quest Wiki and D-navi match +22 Defence, +12 Magical Might, +11 Magical Mending,
and 5% elemental reduction. The row no longer presents an unsupported battle-
use party effect and explicitly allows encounter-specific shields to win the
slot. The cp008 gate remains derived from collecting all medals available by
that route rather than assumed from player state.
