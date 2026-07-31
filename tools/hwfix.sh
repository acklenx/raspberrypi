#!/usr/bin/env bash
#
# hwfix.sh - back up a Pico (dated, deduplicated by content hash), then
# auto-repair the common breakages, then re-run the self-test.
#
# Run ON the machine the Pico is plugged into, from the repo root:
#     tools/hwfix.sh                 # backup, fix, verify
#     tools/hwfix.sh --dry-run       # show what it WOULD do, change nothing
#     PORT=id:c6c7...  tools/hwfix.sh    # pick a board by serial
#     MP=~/.local/bin/mpremote tools/hwfix.sh   # if mpremote is not on PATH
#
# It ALWAYS backs up before it touches anything, and the backup is
# de-duplicated: if the board is byte-for-byte identical to a backup you
# already have, no new copy is made. So it is safe to run repeatedly.
#
# What it repairs (all reversible - the backup is taken FIRST):
#   * stale compiled .mpy shadowing our .py source   (the #1 breakage)
#   * half-written scraps: *.py~  *.tmp  *.bak
#   * missing or corrupt CODE files, restored from THIS repo
#     (lib/*.py, main.py, index.html, cal.js). Assumes the worm-bin /
#     everything layout; pass --no-restore for a board running something else.
# What it NEVER touches (your board-local state, backed up but not changed):
#   name.txt  wifi.json  cal.json  placements.json  node_id.txt
#
set -euo pipefail

MP="${MP:-mpremote}"
PORT="${PORT:-}"
DRY=0
RESTORE=1
for a in "$@"; do
  case "$a" in
    --dry-run)    DRY=1 ;;
    --no-restore) RESTORE=0 ;;
    -h|--help)    sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown arg: $a (try --help)"; exit 2 ;;
  esac
done

conn() { if [ -n "$PORT" ]; then "$MP" connect "$PORT" "$@"; else "$MP" "$@"; fi; }
say()  { printf '  %s\n' "$*"; }
act()  { if [ "$DRY" = 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
BKROOT="$REPO/backups"

echo "== hwfix =="
if ! conn eval 'True' >/dev/null 2>&1; then
  echo "  no board found. Plugged in? Thonny closed? (try: $MP devs)"
  exit 1
fi
# NB: mpremote `eval` takes an EXPRESSION; multi-statement code needs `exec`.
SERIAL="$(conn exec 'import machine,ubinascii;print(ubinascii.hexlify(machine.unique_id()).decode())' 2>/dev/null | tr -d '\r\n ' || true)"
DRYTAG=""; [ "$DRY" = 1 ] && DRYTAG="  (dry-run)"
say "board serial: ${SERIAL:-unknown}${DRYTAG}"

# ---------------------------------------------------------------- list
# Walk the board and print every file path (reliable, no cp -r layout guesses).
LIST="$(conn exec '
import os
def walk(d):
    try: names = os.listdir(d or "/")
    except Exception: return
    for n in names:
        p = (d + "/" + n) if d else n
        try: mode = os.stat(p)[0]
        except Exception: continue
        if mode & 0x4000: walk(p)      # directory
        else: print(p)
walk("")' 2>/dev/null | tr -d '\r')"
if [ -z "$LIST" ]; then echo "  could not list board files"; exit 1; fi

# --------------------------------------------------------------- backup
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
NFILES="$(printf '%s\n' "$LIST" | sed '/^$/d' | wc -l | tr -d ' ')"
say "reading $NFILES files off the board..."
while IFS= read -r f; do
  [ -n "$f" ] || continue
  mkdir -p "$TMP/$(dirname "$f")"
  conn fs cp ":$f" "$TMP/$f" >/dev/null 2>&1 || say "(warn) could not read $f"
done <<< "$LIST"

# Content hash of the whole tree, for dedup.
HASH="$(cd "$TMP" && find . -type f | LC_ALL=C sort | xargs -r sha256sum | sha256sum | cut -d' ' -f1)"
say "board content hash: ${HASH:0:16}"

mkdir -p "$BKROOT"
DUP=""
for d in "$BKROOT"/*/; do
  [ -f "${d}HASH" ] || continue
  if [ "$(cat "${d}HASH")" = "$HASH" ]; then DUP="$d"; break; fi
done
if [ -n "$DUP" ]; then
  say "identical to backup $(basename "$DUP") -> no new backup needed"
elif [ "$DRY" = 1 ]; then
  say "[dry-run] would save a NEW backup (hash ${HASH:0:12})"
else
  BK="$BKROOT/$(date -u +%Y-%m-%dT%H-%M-%SZ)_${SERIAL:-board}_${HASH:0:8}"
  mkdir -p "$BK"
  cp -a "$TMP/." "$BK/"
  printf '%s\n' "$HASH" > "$BK/HASH"
  say "backup saved: ${BK#$REPO/}"
fi

# ----------------------------------------------------------------- fix
changed=0

# 1) stale .mpy and editor/partial scraps
while IFS= read -r f; do
  case "$f" in
    *.mpy|*.py~|*.tmp|*.bak) say "remove junk: $f"; act conn fs rm ":$f"; changed=1 ;;
  esac
done <<< "$LIST"

# 2) restore code files from the repo, but only the ones missing or changed
if [ "$RESTORE" = 1 ]; then
  while IFS='|' read -r onboard src; do
    [ -n "$onboard" ] || continue
    full="$REPO/$src"
    if [ ! -f "$full" ]; then say "repo missing $src (skip restore)"; continue; fi
    if [ ! -f "$TMP/$onboard" ] || ! cmp -s "$full" "$TMP/$onboard"; then
      say "restore $onboard from repo"; act conn fs cp "$full" ":$onboard"; changed=1
    fi
  done <<'MAP'
lib/picolab.py|lib/picolab.py
lib/ssd1306.py|lib/ssd1306.py
lib/bme280.py|lib/bme280.py
lib/ads1115.py|lib/ads1115.py
lib/vl53l0x.py|lib/vl53l0x.py
lib/bh1750.py|lib/bh1750.py
main.py|projects/worm-bin/main.py
index.html|projects/worm-bin/index.html
cal.js|web/cal.js
MAP
fi

[ "$changed" = 0 ] && say "nothing needed fixing."

# -------------------------------------------------------------- verify
if [ "$DRY" = 1 ]; then
  say "[dry-run] done (self-test skipped)"
else
  echo
  say "re-running the self-test to confirm:"
  conn run "$SCRIPT_DIR/hwtest.py" || true
fi
