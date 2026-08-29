# Retrieval quality audit

Audit date: 2026-08-29

`data/golden_questions.json` defines 8 representative playthrough questions:
safe advancement, strongest legal gear, vocation planning, available farming,
Monster Hearts, visible conflicts, duplicate-accessory power, and achievement-counter
rules. `tests/test_retrieval_quality.py` verifies their structured evidence bundles
against a clean rebuilt database.

The suite requires:

- checkpoint-scoped obligations, advice, acquisition gates, and farms;
- precise locators for every externally sourced result;
- independent sources where a normalized mechanic or numeric profile claims
  corroboration;
- player-state unknowns to remain unknown;
- both claims and both citations for unresolved conflicts;
- rejection of source metadata explicitly scoped to PS1 or Nintendo 3DS.

The first audit added citations directly to checkpoint action payloads, added
`through_checkpoint` filtering and an explicit availability status to farm
retrieval, and exposed source IDs on both sides of conflict-report rows.

This suite protects representative evidence bundles; it does not imply that all
possible natural-language questions or all guide domains are complete.

The Alltrades gear bundle now independently reconstructs every compatible item
with an explicit route whose checkpoint window is open. It reports a numeric
dimension leader only when every candidate in that character/slot universe has
that independently corroborated stat. At cp009, coverage is sparse, so the
correct result is `global_strongest_not_proven`: attributed recommendations stay
useful, but effects, costs, prerequisites, finite-copy allocation, and unknown
stats are not collapsed into a fabricated score or universal best-in-slot claim.

The local `query_kb.py` search uses exact-term FTS matches first, then sourced
structured claims and item aliases, and only then broad OR fallback. Regression
queries cover Shell Shield, Slime Earring, Stella Fan, and Orgodemir Magic
Barrier so exact priority identities and conflicts do not disappear into generic
shield, slime, or spell results. Curated evidence gaps take priority when every
query term matches their subject, summary, acceptance condition, or maintained
player-query vocabulary. Matching uses whole tokens rather than substrings. Those results
state the unresolved conclusion and evidence needed, and expose the precise
supporting-claim URLs and locators rather than letting generic results imply closure.
