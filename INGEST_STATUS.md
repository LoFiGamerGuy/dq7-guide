# Ingestion status

Status date: 2026-08-25  
Package: `0.3.0-phase1`  
Build type: reconstructed seed (see `RECOVERY_MANIFEST.md`)

## Current coverage

| Domain | Seed coverage | Confidence | Next target |
|---|---:|---|---|
| Source registry | 50 high-value pages | High metadata / mixed page freshness | Add official and in-game evidence sources |
| Vocations | 26/26 names | High | Ingest all ranks, skills, stats, perks, and Let Loose data |
| Vocation prerequisites | 10 rule groups / 27 prerequisite edges | High | Add derived shortest paths and mastery cost |
| Moonlighting | Unlock and system summary | High | Normalize exact unlock checkpoint and legal skill access |
| Walkthrough checkpoints | 33 checkpoints through postgame cleanup; 57 normalized obligations | Medium/High for ingested obligations | Fill remaining atomic item/monster/achievement obligations and checkpoint locators |
| Mini Medal rewards | 19/19 reward thresholds | High | Cross-check reward stats/effects and exchange availability |
| Mini Medal locations | 100/100 normalized rows with earliest-availability checkpoint gates | 86 cross-source verified; 13 indexed-source checked; 1 Game8-only indexed row | Directly refresh Game8 when accessible and resolve the medal 78 locator conflict |
| Missables / choices | 7 named records | Mixed; only Fish Bits is fully windowed | Normalize exact windows, consequences, and resolution evidence |
| Heroic Hoarder items | 22 normalized items / 102 acquisition paths | High for ingested routes; incomplete overall | Expand by category and require a route or explicit gap for every item |
| Lucky Panel | 11 normalized pools / 39 reward paths plus system summary | High for normalized rows; entry costs remain unknown | Ingest every version/rank/chest item and preserve exclusivity conflicts |
| Equipment | Representative early recommendations | Medium | Full stats, usability, acquisition, earliest checkpoint |
| Farming | 7 Metal spots + postgame seed strategy | Medium/High | Add rates/rewards only when sourced; add gold/proficiency/heart farms |
| Monster Hearts | Representative high-value roles | Medium | Complete registry, effects, and acquisition |
| Achievements | Architecture only | Not started | Full achievement dependency graph |
| Tablets / fragments | Architecture only | Not started | Complete numbered/color acquisition and use graph |
| Player state | Schema and empty Ryan state | Ready, no user data | Fill only from Ryan's reports |
| Conflicts | Automatic exact-scope detection active; 5 unresolved source conflicts | Conservative coverage | Resolve Medal 78, Cautery Sword, Elevating Shoes, Iron Shield, and Ice Shield with direct in-game evidence |

## Database seed counts

Expected after `python scripts/build_kb.py`:

- sources: 50
- vocations/entities: 26
- prerequisite relationships: 27
- claims: 23
- medal rewards: 19
- missables: 7
- farming spots: 8
- checkpoints: 33
- mini medal locations: 100
- checkpoint obligations: 57
- Mini Medal corroborating evidence rows: 86
- Heroic Hoarder items: 22
- item acquisition paths: 102
- shops / inventory rows: 30 / 40
- Lucky Panel pools / reward rows: 11 / 39
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

The 2026-08-25 Phase 2 batches established typed item, shop, and Lucky Panel acquisition routes for 22 Heroic Hoarder items, including the shield sequence through Dragon Shield. Checkpoint-aware advice distinguishes verified free routes from paid routes, unknown costs, and unknown monster chronology. Unspecified containers and pool ranks remain explicit evidence gaps. Source disagreements for Ice Shield treasure, Iron Shield pricing, Elevating Shoes exclusivity, and the Cautery Sword chest location remain explicit alongside the existing Medal 78 conflict.

Phase 1 completed all 100 normalized Mini Medal locations, 86 independent RPG Site evidence rows, a 33-checkpoint spine through postgame, and 45 directly checked obligations. RPG Site's parenthetical medal ordinals remain source-specific walkthrough order and are never treated as canonical album IDs.

## Open questions requiring evidence

- Exact windows and consequences for six non-Fish-Bits missable records.
- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Complete fixed Seed effects and the exact postgame Super Seed reward table.
