# Recovery manifest

## Why this file exists

The earlier ChatGPT task created files in its own `/mnt/data` sandbox and exposed them through ChatGPT content references. The referenced conversation was readable in Codex, but the binary / project attachments were not attached to this local task, and `/mnt/data/dq7_reimagined_kb_v0_1` did not exist on the user's machine or shared Codex workspace.

Therefore this package is a **content-level reconstruction**, not a byte-for-byte modification of the original ZIP.

## Reconstructed from the prior task inventory

- hybrid SQLite + FTS5 / RAG + knowledge graph + player-state architecture;
- 20-source RPG Site / Game8 registry;
- all 26 vocation names;
- complete Intermediate and Advanced prerequisite graph;
- Moonlighting unlock trigger;
- named missables / choice-sensitive events;
- Mini Medal reward thresholds and major power spikes;
- early equipment power-spike examples;
- Lucky Panel completion and early-power guidance;
- Metal farming locations;
- postgame Super Seed farming note;
- representative high-value Monster Hearts;
- initial checkpoints through the first major vocation breakpoint;
- empty player save-state model;
- FTS5 search utility.

## Not claimed as recovered

- exact original table schemas, row IDs, timestamps, or prose;
- any unpublished rows not described in the referenced task;
- the original SQLite binary;
- the exact original 20 URLs (the registry here is a refreshed high-value set serving the same stated roles);
- exact hashes or file metadata from `v0.1`.

## How to achieve literal preservation later

If the original `dq7_reimagined_kb_v0_1.zip` is supplied, compare it against this repository, import any missing seed rows with their original IDs, retain both manifests, rebuild the database, rerun tests, and publish a new version. Do not overwrite user player-state during that merge.

