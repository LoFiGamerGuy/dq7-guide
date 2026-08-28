# Interactive guide readiness

The local HTML guide is ready for an active playthrough. Launch it with
`start-guide.bat` on Windows or `./start-guide.sh` on macOS/Linux. Python 3.10+
is the only runtime dependency.

## Verified surface

- Dashboard, checkpoint walkthrough, progress editor, sources, and conflicts.
- Searchable items, vocations, monsters, Monster Hearts, missables, farms,
  seeds, Mini Medals, tablets, and achievements.
- Shared ledgers for checkpoint actions, medals, tablets, finite items,
  monsters, achievements, and missables.
- Explicit saved checkpoint, party levels, vocations, and vocation mastery;
  unknown values remain unknown.
- STOP warnings precede normal actions; safe advancement comes last. Unresolved
  missable cutoffs never create a false STOP.
- Loading, empty, and error states; keyboard focus, mobile layouts, and reduced
  motion support. Failed checkbox saves roll back visibly.
- Player writes are validated, serialized, and atomic. Checkpoint advancement
  always requires an explicit action.

## Intentional limits

- Equipment is read-only until canonical character/slot compatibility exists.
- Monster Heart ownership is read-only because player state has no Heart field.
- Unknown rates, mastery costs, and unresolved evidence remain unknown.
- First use does not infer an existing save; enter only known state.

## Validation

Run `python scripts/build_kb.py` and
`python -m unittest discover -s tests -v`. When Node is installed, also run
`node --check web/app.js`.
