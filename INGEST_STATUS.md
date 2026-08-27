# Ingestion status

Status date: 2026-08-26
Package: `0.3.0-phase1`  
Build type: reconstructed seed (see `RECOVERY_MANIFEST.md`)

## Current coverage

| Domain | Seed coverage | Confidence | Next target |
|---|---:|---|---|
| Source registry | 73 high-value pages | High metadata / mixed page freshness | Add official and in-game evidence sources |
| Vocations | 26/26 names | High | Ingest all ranks, skills, stats, perks, and Let Loose data |
| Vocation prerequisites | 10 rule groups / 27 prerequisite edges | High | Add derived shortest paths and mastery cost |
| Moonlighting | Unlock and system summary | High | Normalize exact unlock checkpoint and legal skill access |
| Walkthrough checkpoints | 33 checkpoints; 222 obligations; cp001–cp033 ordered and progress-aware | High for the full main-story and postgame chronology/safety spine; optimization remains partial | Deepen item, achievement, and combat coverage |
| Mini Medal rewards | 19/19 reward thresholds | High | Cross-check reward stats/effects and exchange availability |
| Mini Medal locations | 100/100 normalized rows with earliest-availability checkpoint gates | 86 cross-source verified; 13 indexed-source checked; 1 Game8-only indexed row | Directly refresh Game8 when accessible and resolve the medal 78 locator conflict |
| Missables / choices | 7 named records | Mixed; only Fish Bits is fully windowed | Normalize exact windows, consequences, and resolution evidence |
| Heroic Hoarder items | 353/353 identities / 405 acquisition paths; all six categories complete | High for identities and explicit routes; 39 route gaps remain | Resolve remaining gaps without inferring unspecified stores or rewards |
| Lucky Panel | 12 normalized pools / 43 reward paths plus system summary | High for normalized rows; entry costs remain unknown | Ingest every version/rank/chest item and preserve exclusivity conflicts |
| Equipment | 20 ready-for-play gear, boss, grind, and vocation advice rows across cp003–cp009 | Medium/High, attributed | Expand only with checkpoint-valid acquisition and character usability |
| Farming | Roamer Metal Slime and cp009 Lucky Panel advice normalized without invented rates | Medium/High | Verify proficiency, gold, and heart farms before adding ceilings |
| Monster Hearts | Representative high-value roles | Medium | Complete registry, effects, and acquisition |
| Achievements | 61/61 identities; 29/29 non-story requirements; explicit player tracking | High for identities and counters; 2 dependency registries unresolved | Complete monster and all-vocation dependency registries |
| Tablets / fragments | 20/20 tablets and 71/71 numbered fragments | High; current-version source checked | Add explicit player update/report workflow |
| Player state | Schema and empty Ryan state | Ready, no user data | Fill only from Ryan's reports |
| Conflicts | Automatic exact-scope detection active; 6 unresolved source conflicts | Conservative coverage | Resolve the five prior conflicts plus Tempest Shield location with direct in-game evidence |

## Database seed counts

Expected after `python scripts/build_kb.py`:

- sources: 73
- vocations/entities: 26
- prerequisite relationships: 27
- claims: 26
- medal rewards: 19
- missables: 7
- farming spots: 8
- checkpoints: 33
- mini medal locations: 100
- checkpoint obligations: 222
- achievements / aliases: 61 / 1
- achievement requirements: 29
- stone tablets / fragments: 20 / 71
- ready-for-play checkpoint advice: 20
- Mini Medal corroborating evidence rows: 86
- Heroic Hoarder items: 353
- item acquisition paths: 405
- shops / inventory rows: 45 / 82
- Lucky Panel pools / reward rows: 12 / 75
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

The Phase 2 equipment batches established typed item, shop, and Lucky Panel acquisition routes for 30 Heroic Hoarder items, including the shield sequence through Shield of Shame. Unspecified containers and pool ranks remain explicit evidence gaps. The Tempest Shield location disagreement is preserved alongside the five earlier unresolved conflicts.

Phase 1 completed all 100 normalized Mini Medal locations, 86 independent RPG Site evidence rows, a 33-checkpoint spine through postgame, and 45 directly checked obligations. RPG Site's parenthetical medal ordinals remain source-specific walkthrough order and are never treated as canonical album IDs.

## Open questions requiring evidence

- Exact windows and consequences for six non-Fish-Bits missable records.
- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Complete fixed Seed effects and the exact postgame Super Seed reward table.
