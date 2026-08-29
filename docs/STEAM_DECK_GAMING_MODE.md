# Steam Deck Gaming Mode phone flow

## One time in Desktop Mode

1. Put the Deck and phone on the same trusted Wi-Fi.
2. In this repository, run `./manage-steam-deck-guide.sh start`. Open the printed
   phone URL, confirm the guide loads, and bookmark it. Then run
   `./manage-steam-deck-guide.sh stop`.
3. In Steam, choose **Add a Game → Add a Non-Steam Game → Browse** and select
   `steam-deck/run-dq7-guide-gaming-mode.sh`. Name it **DQ7 Phone Guide**.

No root service, login item, or autostart is installed. The Non-Steam entry is an
optional Steam library shortcut to a script in this repository.

## Each play session

1. In Gaming Mode, launch **DQ7 Phone Guide** and leave it running.
2. Launch Dragon Quest VII, then use the Steam button to switch to it.
3. Open the saved guide bookmark on the phone. When finished, return to the guide
   shortcut and choose **Exit game** / **Stop**.

The Desktop and Gaming Mode launchers deliberately share the same private pairing
credential, so an ordinary restart does not require re-pairing. Use
`./manage-steam-deck-guide.sh rotate` in Desktop Mode only when the old phone access
must be revoked; then replace the bookmark.

## Progress safety

- **Backup:** Dashboard, Phone Setup, and Progress each link to a JSON download.
- **Restore:** Progress requires file selection and explicit confirmation.
- **Recovery:** before restore, the Deck retains a timestamped copy beside the
  player-state file. Downloaded backups are still needed for Deck loss or storage
  failure.
- **Disconnects:** writes fail visibly and are never queued. Do not repeat a change
  unless it still appears unsaved after reconnecting.

## SteamOS limits

SteamOS normally permits switching between running apps, but this repository cannot
guarantee that a secondary process survives suspend, reboot, low-memory termination,
network changes, session transitions, or future SteamOS updates. This is not an
autostart service: launch **DQ7 Phone Guide** each play session. If the bookmark no
longer connects, return to Desktop Mode, run `./manage-steam-deck-guide.sh doctor`
and `status`, restart if needed, and update the bookmark if the Wi-Fi address changed.
