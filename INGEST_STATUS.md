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
| Walkthrough checkpoints | 14 checkpoints (10 early plus 4 later backtracking outlines); 24 normalized obligations through Alltrades Present | Medium/High for ingested obligations | Complete remaining item/monster obligations and replace later outlines with atomic chronology |
| Mini Medal rewards | 19/19 reward thresholds | High | Ingest all 100 numbered locations and checkpoint gates |
| Mini Medal locations | 45/100 normalized rows | Mixed: 32 cross-source verified, 13 indexed-source checked | Continue rows 46–77; directly refresh Game8 when accessible |
| Missables / choices | 7 named records | Mixed; only Fish Bits is fully windowed | Normalize exact windows, consequences, and resolution evidence |
| Heroic Hoarder items | 0 complete normalized rows | Not started | Build full acquisition matrix by category |
| Lucky Panel | System role and version summary | Medium/High | Ingest every version/rank/chest item and exclusivity |
| Equipment | Representative early recommendations | Medium | Full stats, usability, acquisition, earliest checkpoint |
| Farming | 7 Metal spots + postgame seed strategy | Medium/High | Add rates/rewards only when sourced; add gold/proficiency/heart farms |
| Monster Hearts | Representative high-value roles | Medium | Complete registry, effects, and acquisition |
| Achievements | Architecture only | Not started | Full achievement dependency graph |
| Tablets / fragments | Architecture only | Not started | Complete numbered/color acquisition and use graph |
| Player state | Schema and empty Ryan state | Ready, no user data | Fill only from Ryan's reports |
| Conflicts | Automatic exact-scope detection active for registered single-valued factual predicates; 0 current conflicts | Conservative coverage | Add wildcard scope-overlap review and predicate comparators as domains expand |

## Database seed counts

Expected after `python scripts/build_kb.py`:

- sources: 24
- vocations/entities: 26
- prerequisite relationships: 27
- claims: 12
- medal rewards: 19
- missables: 7
- farming spots: 8
- checkpoints: 14
- mini medal locations: 45
- checkpoint obligations: 24
- Mini Medal corroborating evidence rows: 32
- searchable documents: 29 (10 curated summaries + 19 reward rows)

Treat these as build assertions, not completion percentages.

## Immediate Phase 1 batch order

1. Expand the initial Prologue-through-Emberdale obligations to full item, fragment, monster, and stop-condition coverage.
2. L'Arca through Alltrades checkpoints and obligations.
3. Mini Medals 46–77 and their story/key backtracking gates.
4. Add a source-ordinal mapping so RPG Site acquisition order can coexist explicitly with Game8's list numbering.
5. Directly refresh Game8 medal rows when the page is accessible; rows currently available only through its indexed table remain medium confidence unless independently corroborated.

## Latest completed batch

The 2026-08-25 Phase 1 batches added normalized tables for Mini Medal locations, independent medal evidence, and checkpoint obligations; Game8 list rows 1–45; and 24 directly checked obligations from the Prologue through Alltrades Present. Game8's direct page returned HTTP 402 during this batch; uncorroborated rows are therefore marked `search_index_checked` at medium confidence. RPG Site's parenthetical medal ordinals are walkthrough acquisition order, while Game8's 1–100 values are list/album order; they are not treated as interchangeable IDs or as a factual conflict.

## Open questions requiring evidence

- Exact windows and consequences for six non-Fish-Bits missable records.
- Exact patch / platform scope for current guide data.
- Whether every editorial “best” build assumes Moonlighting, DLC, easy difficulty, or heavy grinding.
- Full set of Lucky Panel exclusives and alternative enemy-drop sources.
- Complete fixed Seed effects and the exact postgame Super Seed reward table.
