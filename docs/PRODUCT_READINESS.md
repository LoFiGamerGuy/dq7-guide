# Interactive guide readiness

See `PHONE_COMPANION_READINESS.md` for the requirement-level Steam Deck/phone
cold-start, recovery, and platform-limit audit.

The local HTML guide is ready for an active playthrough. Launch it with
`start-guide.bat` on Windows or `./start-guide.sh` on macOS/Linux. Python 3.10+
is the only runtime dependency.

For Steam Deck + phone play, run `start-guide-phone.sh` in Desktop Mode and open
the printed pairing URL. LAN access is opt-in, uses no external service, and ends
when its Konsole process is stopped. A random private pairing identity stored outside
the repository prevents unpaired Wi-Fi clients from reading or editing the guide and
keeps the phone bookmark useful across restarts. Run the phone launcher with
`--rotate-pairing` to revoke all prior pairings. Still use trusted Wi-Fi and keep the
pairing URL private.

Gaming Mode is supported through the repo-contained
`steam-deck/run-dq7-guide-gaming-mode.sh` wrapper, manually added to Steam once as a
Non-Steam Game. It runs the server in Steam's foreground, shares the same persistent
Desktop pairing/bookmark, and exits when the shortcut is stopped. It does not edit
Steam configuration or install a service. SteamOS updates may change whether a second
running app is suspended; Desktop Mode remains the reliable fallback.
The ordinary LAN URL is online-to-host only. Offline installation/caching requires
localhost or a secure HTTPS origin due to browser rules; cached data is visibly
read-only, and changes are never queued. Progress JSON can be exported from and
explicitly restored in the Progress view, with a pre-restore recovery copy retained.
The Phone Setup view diagnoses those conditions from the active browser rather than
claiming that manifest presence alone makes insecure LAN HTTP installable.
An optional repo-contained Steam Deck manager supports background start, status,
stop, restart, and an explicitly installed/removable Desktop shortcut. It makes no
root, service, or autostart changes. It is only guaranteed within the current
Desktop Mode session; suspend, reboot, network changes, and Gaming Mode transitions
may require a restart. Normal restarts retain the bookmarked pairing; only explicit
rotation revokes it, while a Wi-Fi address change requires updating the bookmark.
Backup is linked from Dashboard, Phone
Setup, and Progress; restore remains confirmation-gated under Progress.

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
  motion support. Portrait and landscape phone layouts keep a thumb bar visible;
  Current returns to the saved checkpoint while Prev/Next only browse. Long
  details wrap safely and restore confirmation is keyboard reachable. Failed
  checkbox saves roll back visibly.
- Phone pairing, reloads, and home-screen launches open the saved checkpoint's
  Play view. STOP and open actions stay first; completed actions remain hidden
  and six secondary checkpoint ledgers start collapsed on phones.
- Player writes are validated, serialized, and atomic. Checkpoint advancement
  and STOP clearance require explicit confirmation. Reversible live-play writes
  offer a compact Undo action, ignore duplicate taps while saving, and retain the
  viewed checkpoint, scroll position, and focus.
- Install metadata, cache versioning, explicit offline/read-only behavior, and
  confirmed backup restore are covered by static/API tests.
- A clean-state HTTP workflow verifies the Prologue preview, early STOPs and
  citations, checkpoint selection, first-ten-hours guidance, and reversible
  action/medal/tablet/item/monster/Heart/vocation updates.

## Intentional limits

- Equipment writes require explicit ownership, the corroborated slot layout, matching
  item category, and verified character compatibility. Weapons, shields, helmets,
  armour, and two distinct accessories are reversible; unsupported duplicate/stacking
  behavior remains constrained and every disagreeing source claim stays visible.
- Monster Heart ownership is editable through a dedicated reversible ledger. An absent ledger remains unknown; route or checkpoint availability never implies ownership.
- Unknown encounter/drop/farm rates, repeatable Heart routes, duplicate-effect
  stacking, and other unresolved evidence remain unknown.
- The Sources view exposes a dated eight-gap audit with single-source, unsupported,
  and corroborated-but-unresolved tiers plus the exact evidence needed to close each gap.
- First use does not infer an existing save; enter only known state.

## Validation

Run `python scripts/build_kb.py` and
`python -m unittest discover -s tests -v`. When Node is installed, also run
`node --check web/app.js`.
The browser scopes farms to the checkpoint currently being viewed and classifies
Hearts as available, later, or unknown from that checkpoint rather than treating
every future-gated Heart as available now.

Rendered mobile screenshots are not part of the current automated evidence: the
workspace has no Chrome, Chromium, Edge, Firefox, Playwright, Puppeteer, Selenium,
or equivalent browser runtime installed. Phone behavior is covered by HTTP tests,
JavaScript syntax validation, and DOM/CSS contracts at the 360px portrait and
coarse-pointer landscape breakpoints. A real-device visual pass remains useful;
the repository does not claim pixel-level rendered verification.
