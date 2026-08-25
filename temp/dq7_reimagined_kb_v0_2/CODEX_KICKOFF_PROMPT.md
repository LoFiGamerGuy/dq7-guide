# Ready-to-paste Codex kickoff prompt

```text
Read AGENTS.md, HANDOFF.md, INGEST_STATUS.md, docs/PROVENANCE_AND_CONFLICT_POLICY.md, docs/INGESTION_ROADMAP.md, and player/ryan-save-state.json before changing anything.

Treat this repository as the durable source of truth for my Dragon Quest VII Reimagined completionist/min-max knowledge base. Preserve source provenance, distinguish facts from recommendations, retain conflicting claims, and never import legacy PS1/3DS facts as Reimagined facts without explicit verification.

First, run the database builder and test suite, then query “alltrades vocation” to confirm the seed works. Next, begin Phase 1 of the roadmap: expand the chronological checkpoint graph from the RPG Site 100% walkthrough and normalize the complete 100 Mini Medal location table. Work in small, reviewable batches. For every batch, register sources and locators, add checkpoint availability / missable gates, run integrity checks, update INGEST_STATUS.md, and make a meaningful git commit if this folder is a repository.

Do not copy full guide text. Store atomic facts, short necessary evidence excerpts, original synthesis, and source links. If sources disagree, record the conflict instead of choosing silently. If the exact original v0.1 data is unavailable, preserve the reconstruction disclosure in RECOVERY_MANIFEST.md.

The end-user answer contract is: warn me first if advancing can lose content; otherwise show immediate completion actions, strongest currently obtainable party/gear/vocations, optional grind ceiling, and the condition for safely advancing. Base personalized advice on player/ryan-save-state.json and surface any missing state you need.
```

