# Ingestion status

Status date: 2026-08-25  
Package: `0.3.0-phase1`  
Build type: reconstructed seed (see `RECOVERY_MANIFEST.md`)

## Current coverage

| Domain | Seed coverage | Confidence | Next target |
|---|---:|---|---|
| Source registry | 24 high-value pages | High metadata / mixed page freshness | Add official and in-game evidence sources |
| Vocations | 26/26 names | High | Ingest all ranks, skills, stats, perks, and Let Loose data |
| Vocation prerequisites | 10 rule groups / 27 prerequisite edges | High | Add derived shortest paths and mastery cost |
| Moonlighting | Unlock and system summary | High | Normalize exact unlock checkpoint and legal skill access |
| Walkthrough checkpoints | 33 checkpoints through postgame cleanup; 45 normalized obligations | Medium/High for ingested obligations | Fill remaining atomic item/monster/achievement obligations |
| Mini Medal rewards | 19/19 reward thresholds | High | Cross-check reward stats/effects and exchange availability |
| Mini Medal locations | 100/100 normalized rows | 86 cross-source verified; 13 indexed-source checked; 1 Game8-only indexed row | Directly refresh Game8 when accessible and retain the medal 78 locator conflict |
| Missables / choices | 7 named records | Mixed; only Fish Bits is fully windowed | Normalize exact windows, consequences, and resolution evidence |
| Heroic Hoarder items | 0 complete normalized rows | Not started | Build full acquisition matrix by category |
| Lucky Panel | System role and version summary | Medium/High | Ingest every version/rank/chest item and exclusivity |
| Equipment | Representative early recommendations | Medium | Full stats, usability, acquisition, earliest checkpoint |
| Farming | 7 Metal spots + postgame seed strategy | Medium/High | Add rates/rewards only when sourced; add gold/proficiency/heart farms |
| Monster Hearts | Representative high-value roles | Medium | Complete registry, effects, and acquisition |
| Achievements | Architecture only | Not started | Full achievement dependency graph |
| Tablets / fragments | Architecture only | Not started | Complete numbered/color acquisition and use graph |
| Player state | Schema and empty Ryan state | Ready, no user data | Fill only from Ryan's reports |
| Conflicts | Automatic exact-scope detection active; 1 unresolved source conflict (Mini Medal 78 precise floor/area) | Conservative coverage | Resolve with direct in-game evidence; add wildcard scope-overlap review as domains expand |

## Database seed counts

Expected after `python scripts/build_kb.py`:

- sources: 24
- vocations/entities: 26
- prerequisite relationships: 27
- claims: 14
- medal rewards: 19
- missables: 7
- farming spots: 8
- checkpoints: 33
- mini medal locations: 100
- checkpoint obligations: 45
- Mini Medal corroborating evidence rows: 86
- searchable documents: 29 (10 curated summaries + 19 reward rows)

Treat these as build assertions, not completion percentages.

## Immediate Phase 1 batch order

1. Expand the initial Prologue-through-Emberdale obligations to full item, fragment, monster, and stop-condition coverage.
2. L'Arca through Alltrades checkpoints and obligations.
3. Complete the remaining item, monster, fragment, and achievement obligations within the 33-checkpoint spine.
4. Continue the existing source-ordinal mapping for every independently corroborated medal.
5. Directly refresh Game8 medal rows when the page is accessible; rows currently available only through its indexed table remain medium confidence unless independently corroborated.

## Latest completed batch

The 2026-08-25 Phase 1 batches completed all 100 normalized Mini Medal locations, 86 independent RPG Site evidence rows, a 33-checkpoint spine through postgame, and 45 directly checked obligations. Game8's direct page returned HTTP 402 during these batches; uncorroborated rows remain medium confidence. Medal 78 has an explicit unresolved floor/area conflict between sources rather than a silently blended locator. RPG Site's parenthetical medal ordinals remain source-specific walkthrough order and are never treated as canonical album IDs.

## Open questions requiring evidence

- Exact windows and consequences for six non-Fish-Bits missable records.
- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Complete fixed Seed effects and the exact postgame Super Seed reward table.
