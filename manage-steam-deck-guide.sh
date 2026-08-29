#!/usr/bin/env sh
set -eu
umask 077

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runtime_dir=${DQ7_GUIDE_RUNTIME_DIR:-"$repo_dir/.guide-runtime"}
pid_file="$runtime_dir/server.pid"
log_file="$runtime_dir/server.log"
pairing_file=${DQ7_GUIDE_PAIRING_FILE:-"$runtime_dir/phone-pairing-token"}
state_file=${DQ7_GUIDE_STATE_FILE:-"$repo_dir/player/ryan-save-state.json"}
server_port=${DQ7_GUIDE_PORT:-8765}
shortcut_template="$repo_dir/steam-deck/DQ7 Guide.desktop.in"

desktop_dir() { if command -v xdg-user-dir >/dev/null 2>&1; then xdg-user-dir DESKTOP; else printf '%s/Desktop\n' "$HOME"; fi; }
read_pid() { [ -f "$pid_file" ] || return 1; pid=$(sed -n '1p' "$pid_file"); case "$pid" in *[!0-9]*|'') return 1 ;; esac; printf '%s\n' "$pid"; }
is_guide_process() { check_pid=$1; [ -r "/proc/$check_pid/cmdline" ] || return 1; [ "$(readlink "/proc/$check_pid/cwd" 2>/dev/null || true)" = "$repo_dir" ] || return 1; tr '\000' ' ' < "/proc/$check_pid/cmdline" | grep -Fq 'scripts/guide_server.py'; }
is_running() { running_pid=$(read_pid) || return 1; kill -0 "$running_pid" 2>/dev/null && is_guide_process "$running_pid"; }
require_python() { command -v python3 >/dev/null 2>&1 || { echo "Python 3.10 or newer is required." >&2; exit 1; }; python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' || { echo "Python 3.10 or newer is required." >&2; exit 1; }; }
show_access() { [ -f "$log_file" ] || return 0; sed -n '/DQ7 guide (this device):/p; /DQ7 guide (phone):/p; /Phone address unavailable/p' "$log_file"; }
pairing_requirement() { if [ "${DQ7_GUIDE_FORCE_PAIRING:-0}" = "1" ]; then printf '%s\n' --require-pairing-everywhere; fi; }

start_server() {
  require_python
  if is_running; then echo "DQ7 phone guide is already running (PID $running_pid)."; show_access; return 0; fi
  mkdir -p "$runtime_dir"; chmod 700 "$runtime_dir"; : > "$log_file"; chmod 600 "$log_file"; cd "$repo_dir"
  pairing_option=$(pairing_requirement)
  if [ "${1:-}" = "rotate" ]; then
    nohup python3 -u scripts/guide_server.py --lan --port "$server_port" --state "$state_file" --pairing-file "$pairing_file" $pairing_option --rotate-pairing >"$log_file" 2>&1 &
  else
    nohup python3 -u scripts/guide_server.py --lan --port "$server_port" --state "$state_file" --pairing-file "$pairing_file" $pairing_option >"$log_file" 2>&1 &
  fi
  server_pid=$!; printf '%s\n' "$server_pid" > "$pid_file"; chmod 600 "$pid_file"; attempts=0
  while [ "$attempts" -lt 20 ]; do
    if ! kill -0 "$server_pid" 2>/dev/null; then echo "The guide stopped during startup:" >&2; sed -n '1,80p' "$log_file" >&2; exit 1; fi
    if grep -q 'DQ7 guide (this device):' "$log_file"; then break; fi
    attempts=$((attempts + 1)); sleep 0.1
  done
  if ! grep -q 'DQ7 guide (this device):' "$log_file"; then
    kill "$server_pid" 2>/dev/null || true; rm -f "$pid_file"
    echo "The guide did not become ready. Run '$0 logs' for details." >&2
    exit 1
  fi
  echo "DQ7 phone guide started in the background (PID $server_pid)."; show_access
  echo "Keep the pairing URL private. Use '$0 status', '$0 stop', or '$0 restart'."
  echo "It can survive closing this terminal while Desktop Mode remains active."
}

stop_server() {
  if ! is_running; then echo "DQ7 phone guide is not running."; rm -f "$pid_file"; return 0; fi
  kill "$running_pid"; attempts=0
  while kill -0 "$running_pid" 2>/dev/null && [ "$attempts" -lt 30 ]; do attempts=$((attempts + 1)); sleep 0.1; done
  if kill -0 "$running_pid" 2>/dev/null; then echo "The guide did not stop cleanly; PID $running_pid is still running." >&2; return 1; fi
  rm -f "$pid_file"; echo "DQ7 phone guide stopped. Its bookmarked pairing URL remains valid after a normal restart."
}

show_status() {
  if is_running; then echo "DQ7 phone guide is running (PID $running_pid)."; show_access
  else echo "DQ7 phone guide is stopped."; [ -f "$log_file" ] && { echo "Last log: $log_file"; sed -n '1,12p' "$log_file"; }; fi
  return 0
}

show_logs() { if [ -f "$log_file" ]; then echo "Private pairing URLs may appear below; do not share this output."; tail -n 60 "$log_file"; else echo "No manager log exists yet."; fi; }

doctor() {
  echo "DQ7 phone guide checks"
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then echo "OK  Python 3.10+"; else echo "FAIL  Python 3.10+ is required"; fi
  if [ -r "$repo_dir/data/dq7_reimagined.sqlite" ]; then echo "OK  knowledge database readable"; else echo "FAIL  data/dq7_reimagined.sqlite is missing or unreadable"; fi
  if is_running; then echo "OK  server running (PID $running_pid)"; show_access; else echo "INFO  server stopped"; fi
  echo "If the phone cannot connect: use trusted Wi-Fi, disable phone VPN/cellular fallback, and allow Python on the private-network firewall."
}

install_shortcut() {
  command -v konsole >/dev/null 2>&1 || { echo "Konsole is required for the Steam Deck shortcut." >&2; exit 1; }
  target_dir=$(desktop_dir); [ -d "$target_dir" ] || { echo "Desktop folder not found: $target_dir" >&2; exit 1; }
  target="$target_dir/DQ7 Phone Guide.desktop"; escaped_repo=$(printf '%s' "$repo_dir" | sed 's/[&|]/\\&/g')
  sed "s|@REPO@|$escaped_repo|g" "$shortcut_template" > "$target"; chmod 755 "$target"
  echo "Created: $target"; echo "This is the only setup change. Delete it or run '$0 remove-shortcut' to undo."
}

remove_shortcut() { target="$(desktop_dir)/DQ7 Phone Guide.desktop"; if [ -f "$target" ]; then rm -f "$target"; echo "Removed: $target"; else echo "Shortcut is not installed."; fi; }

foreground_server() {
  require_python
  if is_running; then
    echo "The Desktop background guide is already running (PID $running_pid). Stop it before launching the Gaming Mode shortcut." >&2
    exit 1
  fi
  mkdir -p "$runtime_dir"; chmod 700 "$runtime_dir"; cd "$repo_dir"
  pairing_option=$(pairing_requirement)
  echo "Starting the phone guide for Gaming Mode. Use Steam's Stop/Exit when finished."
  exec python3 -u scripts/guide_server.py --lan --port "$server_port" \
    --state "$state_file" --pairing-file "$pairing_file" $pairing_option
}

command_name=${1:-status}
case "$command_name" in
  start) start_server ;; stop) stop_server ;; restart) stop_server; start_server ;; rotate) stop_server; start_server rotate ;; status) show_status ;; logs) show_logs ;; doctor) doctor ;;
  foreground) foreground_server ;;
  install-shortcut) install_shortcut ;; remove-shortcut) remove_shortcut ;;
  *) echo "Usage: $0 {start|stop|restart|rotate|status|logs|doctor|foreground|install-shortcut|remove-shortcut}" >&2; exit 2 ;;
esac
