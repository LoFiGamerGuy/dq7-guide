#!/usr/bin/env python3
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "player" / "player_state.json"

def set_path(obj, dotted, value):
    parts = dotted.split(".")
    cur = obj
    for p in parts[:-1]:
        cur = cur[p]
    leaf = parts[-1]
    # Small convenience conversions
    if value.lower() == "null": parsed = None
    elif value.lower() in ("true","false"): parsed = value.lower()=="true"
    else:
        try: parsed = int(value)
        except:
            try: parsed = float(value)
            except: parsed = value
    cur[leaf] = parsed

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/update_state.py party.Hero.level 12")
        raise SystemExit(2)
    data = json.loads(STATE.read_text(encoding="utf-8"))
    set_path(data, sys.argv[1], " ".join(sys.argv[2:]))
    STATE.write_text(json.dumps(data, indent=2, ensure_ascii=False),encoding="utf-8")
    print(f"Updated {sys.argv[1]}")
