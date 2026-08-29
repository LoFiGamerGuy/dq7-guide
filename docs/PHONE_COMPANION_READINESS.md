# Phone companion readiness

| Requirement | Evidence | Status |
|---|---|---|
| Cold start | Three steps in README and Phone Setup; manager validates Python and starts LAN mode | Ready |
| Keep running | Repo-local `nohup` manager with validated PID, status, stop, and restart | Ready within one Desktop Mode session |
| Phone access | Private persistent pairing URL; normal restart preserves bookmark; explicit rotation revokes it; a server marker keeps header- and cookie-authenticated API data network-only, and cache v10 purges older snapshots | Ready on trusted LAN |
| Live play | Responsive walkthrough, thumb controls, direct validated writes, visible save failures and undo | Ready |
| Backup | Download link on Dashboard, Phone Setup, and Progress | Ready while host is reachable |
| Restore/recovery | File validation, explicit confirmation, atomic replacement, timestamped pre-restore copy | Ready; recovery files stay on host |
| Diagnostics | Startup readiness timeout plus `status`, `logs`, and `doctor`; in-app connection/security/write status requires actual host reachability before reporting direct writes | Ready |
| Cleanup | `stop`, removable shortcut, ignored repo-local runtime files, no root/service/autostart | Ready |
| Offline/PWA | Service worker only on secure origins; paired player data is always network-only, while the cached shell contains no authorized API snapshot; LAN HTTP is explicitly online-only | Intentional privacy/browser limitation |
| SteamOS lifecycle | Suspend, reboot, network change, or Desktop/Gaming Mode transition may require restart | Platform limitation |
| Gaming Mode flow | One-time manual Non-Steam wrapper plus foreground server reusing the Desktop pairing identity | Tested; secondary-app survival remains SteamOS-dependent |

Residual operational needs: keep the Deck awake and reachable, use trusted Wi-Fi,
allow Python through a private-network firewall if one is enabled, and retain a
downloaded progress backup somewhere outside the Deck for device-loss protection.
