# Interactive guide readiness

The local HTML guide is ready for an active playthrough. Launch it with
`start-guide.bat` on Windows or `./start-guide.sh` on macOS/Linux. Python 3.10+
is the only runtime dependency.

For Steam Deck + phone play, run `start-guide-phone.sh` in Desktop Mode and open
the printed phone URL. LAN access is opt-in, uses no external service, and ends
when its Konsole process is stopped. Use it only on trusted Wi-Fi because phone
mode includes the same validated progress-editing controls as the Deck browser.
The ordinary LAN URL is online-to-host only. Offline installation/caching requires
localhost or a secure HTTPS origin due to browser rules; cached data is visibly
read-only, and changes are never queued. Progress JSON can be exported from and
explicitly restored in the Progress view, with a pre-restore recovery copy retained.

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
- Install metadata, cache versioning, explicit offline/read-only behavior, and
  confirmed backup restore are covered by static/API tests.
- A clean-state HTTP workflow verifies the Prologue preview, early STOPs and
  citations, checkpoint selection, first-ten-hours guidance, and reversible
  action/medal/tablet/item/monster/Heart/vocation updates.

## Intentional limits

- Equipment writes are accessory-only: two slots per character, explicitly owned
  canonical items, verified compatibility, and distinct item IDs. Weapon, shield,
  head, and torso writes remain disabled; every disputed or single-source row stays visible.
- Monster Heart ownership is editable through a dedicated reversible ledger. An absent ledger remains unknown; route or checkpoint availability never implies ownership.
- Unknown rates, mastery costs, and unresolved evidence remain unknown.
- The Sources view exposes a dated five-gap audit with single-source, unsupported,
  and corroborated-but-unresolved tiers plus the exact evidence needed to close each gap.
- First use does not infer an existing save; enter only known state.

## Validation

Run `python scripts/build_kb.py` and
`python -m unittest discover -s tests -v`. When Node is installed, also run
`node --check web/app.js`.
The browser scopes farms to the checkpoint currently being viewed and classifies
Hearts as available, later, or unknown from that checkpoint rather than treating
every future-gated Heart as available now.
