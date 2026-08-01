#!/usr/bin/env bash
#
# hwfix.sh - back up a Pico (dated, deduplicated by content hash), then
# auto-repair the common breakages, then re-run the self-test.
#
# Run ON the machine the Pico is plugged into, from the repo root:
#     tools/hwfix.sh                 # backup, fix, verify
#     tools/hwfix.sh --dry-run       # show what it WOULD do, change nothing
#     tools/hwfix.sh --restore-backup backups/<DIR>   # UNDO: push a backup
#                                    # back onto the board, exactly as it was
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
RESTORE_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)        DRY=1 ;;
    --no-restore)     RESTORE=0 ;;
    --restore-backup) shift; RESTORE_DIR="${1:-}" ;;
    -h|--help)        sed -n '2,34p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1 (try --help)"; exit 2 ;;
  esac
  shift
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

# ------------------------------------------------------------- restore
# UNDO mode: push a saved backup straight back onto the board, then stop.
if [ -n "$RESTORE_DIR" ]; then
  [ -d "$RESTORE_DIR" ] || RESTORE_DIR="$REPO/$RESTORE_DIR"   # accept repo-relative
  if [ ! -d "$RESTORE_DIR" ]; then echo "  no such backup dir: $RESTORE_DIR"; exit 1; fi
  say "RESTORING board from: ${RESTORE_DIR#$REPO/}"
  ( cd "$RESTORE_DIR" && find . -type d ) | sed 's#^\./##' | while IFS= read -r d; do
    if [ -z "$d" ] || [ "$d" = "." ]; then continue; fi
    conn fs mkdir ":$d" >/dev/null 2>&1 || true
  done
  ( cd "$RESTORE_DIR" && find . -type f ! -name HASH ) | sed 's#^\./##' | while IFS= read -r f; do
    [ -n "$f" ] || continue
    say "restore $f"
    act conn fs cp "$RESTORE_DIR/$f" ":$f"
  done
  say "restore complete."
  if [ "$DRY" = 0 ]; then echo; say "re-running self-test:"; conn run "$SCRIPT_DIR/hwtest.py" || true; fi
  exit 0
fi

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
DUP=""; BACKUP_DIR=""
for d in "$BKROOT"/*/; do
  [ -f "${d}HASH" ] || continue
  if [ "$(cat "${d}HASH")" = "$HASH" ]; then DUP="$d"; break; fi
done
if [ -n "$DUP" ]; then
  BACKUP_DIR="${DUP%/}"
  say "identical to backup $(basename "$DUP") -> no new backup needed"
elif [ "$DRY" = 1 ]; then
  say "[dry-run] would save a NEW backup (hash ${HASH:0:12})"
else
  BK="$BKROOT/$(date -u +%Y-%m-%dT%H-%M-%SZ)_${SERIAL:-board}_${HASH:0:8}"
  mkdir -p "$BK"
  cp -a "$TMP/." "$BK/"
  printf '%s\n' "$HASH" > "$BK/HASH"
  BACKUP_DIR="$BK"
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

# Always show the undo, whether or not anything was changed this run, so the
# restore-from-backup command is right there if a fix ever makes things worse.
if [ -n "$BACKUP_DIR" ]; then
  echo
  say "UNDO - restore this board exactly as it was before this run:"
  say "    tools/hwfix.sh --restore-backup '${BACKUP_DIR#$REPO/}'"
fi

# -------------------------------------------------------------- verify
if [ "$DRY" = 1 ]; then
  say "[dry-run] done (self-test skipped)"
else
  echo
  say "re-running the self-test to confirm:"
  conn run "$SCRIPT_DIR/hwtest.py" || true
fi
