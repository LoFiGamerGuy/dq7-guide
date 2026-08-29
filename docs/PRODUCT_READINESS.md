# Interactive guide readiness

The local HTML guide is ready for an active playthrough. Launch it with
`start-guide.bat` on Windows or `./start-guide.sh` on macOS/Linux. Python 3.10+
is the only runtime dependency.

## Verified surface

- Dashboard, checkpoint walkthrough, progress editor, sources, and conflicts.
- Searchable items, vocations, monsters, Monster Hearts, missables, farms,
  seeds, Mini Medals, tablets, and achievements.
- Shared ledgers for checkpoint actions, medals, tablets, finite items,
  monsters, Monster Hearts, achievements, and missables. The Progress view audits
  every completion ledger and preserves unreported empty legacy arrays as unknown.
- Explicit saved checkpoint, party levels, vocations, and vocation mastery;
  unknown values remain unknown.
- STOP warnings precede normal actions; safe advancement comes last. Unresolved
  missable cutoffs never create a false STOP.
- Loading, empty, and error states; keyboard focus, mobile layouts, and reduced
  motion support. Failed checkbox saves roll back visibly.
- Player writes are validated, serialized, and atomic. Checkpoint advancement
  always requires an explicit action.

## Intentional limits

- Equipment remains read-only. The canonical non-accessory audit verifies only
  two-source-agreeing rows and exposes every disputed or single-source row.
- Monster Heart ownership is editable through a dedicated reversible ledger. An absent ledger remains unknown; route or checkpoint availability never implies ownership.
- Unknown rates, mastery costs, and unresolved evidence remain unknown.
- The Sources view exposes a dated five-gap audit with single-source, unsupported,
  and corroborated-but-unresolved tiers plus the exact evidence needed to close each gap.
- First use does not infer an existing save; enter only known state.

## Validation

Run `python scripts/build_kb.py` and
`python -m unittest discover -s tests -v`. When Node is installed, also run
`node --check web/app.js`.
