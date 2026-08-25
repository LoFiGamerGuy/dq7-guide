# Ingestion status

Status date: 2026-08-25  
Package: `0.2.0-handoff`  
Build type: reconstructed seed (see `RECOVERY_MANIFEST.md`)

## Current coverage

| Domain | Seed coverage | Confidence | Next target |
|---|---:|---|---|
| Source registry | 24 high-value pages | High metadata / mixed page freshness | Add official and in-game evidence sources |
| Vocations | 26/26 names | High | Ingest all ranks, skills, stats, perks, and Let Loose data |
| Vocation prerequisites | 10 rule groups / 27 prerequisite edges | High | Add derived shortest paths and mastery cost |
| Moonlighting | Unlock and system summary | High | Normalize exact unlock checkpoint and legal skill access |
| Walkthrough checkpoints | 10 early checkpoints; 10 normalized obligations through Emberdale | Medium/High for ingested obligations | Expand L'Arca through Alltrades with atomic obligations |
| Mini Medal rewards | 19/19 reward thresholds | High | Ingest all 100 numbered locations and checkpoint gates |
| Mini Medal locations | 20/100 normalized rows | Mixed: 7 cross-source verified, 13 indexed-source checked | Continue rows 21–45; directly refresh Game8 when accessible |
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

- sources: 24
- vocations/entities: 26
- prerequisite relationships: 27
- claims: 12
- medal rewards: 19
- missables: 7
- farming spots: 8
- checkpoints: 10
- mini medal locations: 20
- checkpoint obligations: 11
- Mini Medal corroborating evidence rows: 7
- searchable documents: 29 (10 curated summaries + 19 reward rows)

Treat these as build assertions, not completion percentages.

## Immediate Phase 1 batch order

1. Expand the initial Prologue-through-Emberdale obligations to full item, fragment, monster, and stop-condition coverage.
2. L'Arca through Alltrades checkpoints and obligations.
3. Mini Medals 21–45 and all Thief's Key backtracking gates.
4. Add a source-ordinal mapping so RPG Site acquisition order can coexist explicitly with Game8's list numbering.
5. Directly refresh Game8 medal rows when the page is accessible; rows currently available only through its indexed table remain medium confidence unless independently corroborated.

## Latest completed batch

The 2026-08-25 Phase 1 foundation batch added normalized tables for Mini Medal locations and checkpoint obligations, Game8 list rows 1–20, and ten directly checked RPG Site obligations from the Prologue through Emberdale. Game8's direct page returned HTTP 402 during this batch; uncorroborated rows are therefore marked `search_index_checked` at medium confidence. RPG Site's parenthetical medal ordinals are walkthrough acquisition order, while Game8's 1–100 values are list/album order; they are not treated as interchangeable IDs or as a factual conflict.

## Open questions requiring evidence

- Exact windows and consequences for six non-Fish-Bits missable records.
- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Complete fixed Seed effects and the exact postgame Super Seed reward table.
