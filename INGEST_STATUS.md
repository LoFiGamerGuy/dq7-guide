# Ingestion status

Status date: 2026-08-25  
Package: `0.2.0-handoff`  
Build type: reconstructed seed (see `RECOVERY_MANIFEST.md`)

## Current coverage

| Domain | Seed coverage | Confidence | Next target |
|---|---:|---|---|
| Source registry | 20 high-value pages | High metadata / mixed page freshness | Add official and in-game evidence sources |
| Vocations | 26/26 names | High | Ingest all ranks, skills, stats, perks, and Let Loose data |
| Vocation prerequisites | 10 rule groups / 27 prerequisite edges | High | Add derived shortest paths and mastery cost |
| Moonlighting | Unlock and system summary | High | Normalize exact unlock checkpoint and legal skill access |
| Walkthrough checkpoints | 10 early checkpoints, partial | Medium | Expand through endgame with atomic obligations |
| Mini Medal rewards | 19/19 reward thresholds | High | Ingest all 100 numbered locations and checkpoint gates |
| Mini Medal locations | 0/100 normalized rows | Not started | Phase 1 priority |
| Missables / choices | 7 named records | Mixed; only Fish Bits is fully windowed | Normalize exact windows, consequences, and resolution evidence |
| Heroic Hoarder items | 0 complete normalized rows | Not started | Build full acquisition matrix by category |
| Lucky Panel | System role and version summary | Medium/High | Ingest every version/rank/chest item and exclusivity |
| Equipment | Representative early recommendations | Medium | Full stats, usability, acquisition, earliest checkpoint |
| Farming | 7 Metal spots + postgame seed strategy | Medium/High | Add rates/rewards only when sourced; add gold/proficiency/heart farms |
| Monster Hearts | Representative high-value roles | Medium | Complete registry, effects, and acquisition |
| Achievements | Architecture only | Not started | Full achievement dependency graph |
| Tablets / fragments | Architecture only | Not started | Complete numbered/color acquisition and use graph |
| Player state | Schema and empty Ryan state | Ready, no user data | Fill only from Ryan's reports |
| Conflicts | Schema ready; 0 seeded conflicts | Not evaluated comprehensively | Run subject/predicate/scope comparison during each batch |

## Database seed counts

Expected after `python scripts/build_kb.py`:

- sources: 20
- vocations/entities: 26
- prerequisite relationships: 27
- claims: 9
- medal rewards: 19
- missables: 7
- farming spots: 8
- checkpoints: 10
- searchable documents: 28 (9 curated summaries + 19 reward rows)

Treat these as build assertions, not completion percentages.

## Immediate Phase 1 batch order

1. RPG Site checkpoints from Prologue through Emberdale, with all items, medals, fragments, monsters, and stop conditions.
2. Mini Medals 1–20, cross-checked between RPG Site chronology and Game8's numbered list.
3. L'Arca through Alltrades checkpoints.
4. Mini Medals 21–45 and all Thief's Key backtracking gates.
5. Resolve the numbering / route differences between sources without overwriting either claim.

## Open questions requiring evidence

- Exact windows and consequences for six non-Fish-Bits missable records.
- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Complete fixed Seed effects and the exact postgame Super Seed reward table.
