# Wipe every user file off a Pico, back to bare MicroPython. Use when a
# board is "stuck": stale .mpy shadowing new code, an old main.py that
# fights you at boot, a leftover wifi.json / name.txt / cal.json, or just
# mystery behavior. Keeps the firmware (MicroPython itself); removes
# everything you ever put on the filesystem.
#
# Run it one of two ways:
#   * Viper IDE: open this file, click Run.
#   * mpremote:  mpremote connect <port> run tools/wipe.py
#
# After a wipe, reinstall from Viper (the one-click project links) and
# the board is factory-clean but still flashed. For a TRUE factory reset
# (wipes firmware too) hold BOOTSEL and drop the .uf2 instead.

import os

KEEP = ()  # nothing is sacred; add filenames here to spare them


def _wipe(path):
  removed = 0
  try:
    entries = os.listdir(path)
  except OSError:
    return 0
  for name in entries:
    full = path.rstrip("/") + "/" + name
    if name in KEEP:
      continue
    try:
      os.remove(full)
      removed += 1
    except OSError:
      removed += _wipe(full)
      try:
        os.rmdir(full)
        removed += 1
      except OSError:
        pass
  return removed


print("Wiping the board...")
n = _wipe("/")
print("Removed", n, "items. What's left:", os.listdir("/"))
print("Board is bare MicroPython. Reinstall a project from Viper IDE.")
