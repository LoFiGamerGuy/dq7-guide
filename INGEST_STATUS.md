# Ingestion status

Status date: 2026-08-25  
Package: `0.3.0-phase1`  
Build type: reconstructed seed (see `RECOVERY_MANIFEST.md`)

## Current coverage

| Domain | Seed coverage | Confidence | Next target |
|---|---:|---|---|
| Source registry | 31 high-value pages | High metadata / mixed page freshness | Add official and in-game evidence sources |
| Vocations | 26/26 names | High | Ingest all ranks, skills, stats, perks, and Let Loose data |
| Vocation prerequisites | 10 rule groups / 27 prerequisite edges | High | Add derived shortest paths and mastery cost |
| Moonlighting | Unlock and system summary | High | Normalize exact unlock checkpoint and legal skill access |
| Walkthrough checkpoints | 33 checkpoints through postgame cleanup; 57 normalized obligations | Medium/High for ingested obligations | Fill remaining atomic item/monster/achievement obligations and checkpoint locators |
| Mini Medal rewards | 19/19 reward thresholds | High | Cross-check reward stats/effects and exchange availability |
| Mini Medal locations | 100/100 normalized rows with earliest-availability checkpoint gates | 86 cross-source verified; 13 indexed-source checked; 1 Game8-only indexed row | Directly refresh Game8 when accessible and resolve the medal 78 locator conflict |
| Missables / choices | 7 named records | Mixed; only Fish Bits is fully windowed | Normalize exact windows, consequences, and resolution evidence |
| Heroic Hoarder items | 6 normalized items / 11 acquisition paths | High for ingested routes; incomplete overall | Expand by category and require a route or explicit gap for every item |
| Lucky Panel | 6 normalized pools / 7 reward paths plus system summary | High for normalized rows; entry costs remain unknown | Ingest every version/rank/chest item and preserve exclusivity conflicts |
| Equipment | Representative early recommendations | Medium | Full stats, usability, acquisition, earliest checkpoint |
| Farming | 7 Metal spots + postgame seed strategy | Medium/High | Add rates/rewards only when sourced; add gold/proficiency/heart farms |
| Monster Hearts | Representative high-value roles | Medium | Complete registry, effects, and acquisition |
| Achievements | Architecture only | Not started | Full achievement dependency graph |
| Tablets / fragments | Architecture only | Not started | Complete numbered/color acquisition and use graph |
| Player state | Schema and empty Ryan state | Ready, no user data | Fill only from Ryan's reports |
| Conflicts | Automatic exact-scope detection active; 3 unresolved source conflicts | Conservative coverage | Resolve Medal 78, Cautery Sword, and Elevating Shoes with direct in-game evidence; add wildcard scope-overlap review as domains expand |

## Database seed counts

Expected after `python scripts/build_kb.py`:

- sources: 31
- vocations/entities: 26
- prerequisite relationships: 27
- claims: 18
- medal rewards: 19
- missables: 7
- farming spots: 8
- checkpoints: 33
- mini medal locations: 100
- checkpoint obligations: 57
- Mini Medal corroborating evidence rows: 86
- Heroic Hoarder items: 6
- item acquisition paths: 11
- shops / inventory rows: 1 / 1
- Lucky Panel pools / reward rows: 6 / 7
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

The 2026-08-25 Phase 2 batch established typed item, shop, and Lucky Panel acquisition routes for six Heroic Hoarder items. It added checkpoint-aware purchase advice that distinguishes verified free routes from paid routes and unknown costs, plus strict validation for typed details, route windows, and cost contradictions. Source disagreements for Elevating Shoes exclusivity and the Cautery Sword chest location remain explicit alongside the existing Medal 78 conflict.

Phase 1 completed all 100 normalized Mini Medal locations, 86 independent RPG Site evidence rows, a 33-checkpoint spine through postgame, and 45 directly checked obligations. RPG Site's parenthetical medal ordinals remain source-specific walkthrough order and are never treated as canonical album IDs.

## Open questions requiring evidence

- Exact windows and consequences for six non-Fish-Bits missable records.
- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Complete fixed Seed effects and the exact postgame Super Seed reward table.
