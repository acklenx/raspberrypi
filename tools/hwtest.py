# hwtest.py - Maker Lab Kids Pico 2 W bring-up / self-test.
#
# A no-framework, run-it-and-read-it hardware check for the worm-bin
# "everything" build. It answers two questions a teacher actually has at
# the start of class:
#
#   1. Did my code actually land on this board, in a state that will BOOT?
#      (This is the part that has bitten us: stale .mpy files shadowing a
#       .py, port 80 still held from the last run, a missing driver, a
#       syntax error that bricks startup, the truth light never starting.)
#   2. Of the parts that ARE plugged in right now, is each one answering?
#
# It NEVER assumes all the hardware is present. The board might be a bare
# Pico or a fully loaded bin or anything between. A missing part is a SKIP
# (grey), not a failure. A part that is present but not answering is a
# FAIL (red) - that is the thing worth catching.
#
# Every single check is sandboxed: if a check itself blows up, that is
# reported as a FAIL and the run keeps going. The harness cannot take the
# board (or itself) down.
#
# RUN IT (over the lab rig, from the repo root):
#     mpremote run tools/hwtest.py
# or copy it on and `import hwtest`. It leaves nothing behind and does not
# start Wi-Fi, the AP, or the web server (it only CHECKS that port 80 is
# free). Servos and the relay are NOT driven unless you set ACTUATE=True.
#
# PREVIEW THE OUTPUT with no board at all (on your laptop):
#     python3 tools/hwtest.py
# prints a clearly-labelled SIMULATED report so you can see the format.

ACTUATE = False     # True: full servo sweep + a relay click (needs a strong supply)
MOVE_SERVOS = True  # gently wiggle servos to confirm them; False = never move them
USE_COLOR = True    # ANSI colour; set False for a plain-text terminal

# ---- the board we expect, as data (matches worm-bin/main.py) ---------
I2C_SDA, I2C_SCL = 0, 1            # default bus; overwritten by whatever pair we find
# Candidate I2C pairs (controller, SDA, SCL), same clean set picolab scans, so
# the self-test finds the sensor bank on whichever pair it is plugged into.
I2C_CANDIDATES = [
    (0, 0, 1), (0, 20, 21), (0, 4, 5), (0, 8, 9), (0, 12, 13),
    (1, 2, 3), (1, 6, 7), (1, 10, 11), (1, 18, 19),
]
KNOWN = [                          # addr, label (what SHOULD be at each addr)
    (0x3C, "OLED SSD1306"),
    (0x76, "BME280 in"),
    (0x77, "BME280 out"),
    (0x48, "ADS1115 analog bank"),
    (0x29, "VL53L0X distance"),
    (0x23, "BH1750 lux"),
]
MIC_PIN, LIGHT_PIN, PROBE_PIN = 27, 28, 22
SERVO_PINS, RELAY_PIN = (16, 17), 15
REQUIRED_FILES = ["main.py", "lib/picolab.py", "lib/ssd1306.py",
                  "lib/bme280.py", "lib/ads1115.py", "lib/vl53l0x.py",
                  "lib/bh1750.py"]
REQUIRED_IMPORTS = ["picolab", "ssd1306", "bme280", "ads1115",
                    "vl53l0x", "bh1750", "onewire", "ds18x20"]

# ---- status vocabulary ----------------------------------------------
PASS, FAIL, SKIP, WARN, INFO = "PASS", "FAIL", "SKIP", "WARN", "INFO"

_BADGE = {
    PASS: ("\x1b[1;42;30m ✓ \x1b[0m", "\x1b[32m", "[ OK ]"),
    FAIL: ("\x1b[1;41;97m ✗ \x1b[0m", "\x1b[1;31m", "[FAIL]"),
    SKIP: ("\x1b[1;100;97m · \x1b[0m", "\x1b[90m", "[skip]"),
    WARN: ("\x1b[1;43;30m ! \x1b[0m", "\x1b[33m", "[warn]"),
    INFO: ("\x1b[1;44;97m i \x1b[0m", "\x1b[36m", "[info]"),
}
# smaller glyphs for the nested sub-step lines under a test
_MINI = {PASS: "\x1b[32m✓\x1b[0m", FAIL: "\x1b[1;31m✗\x1b[0m",
         SKIP: "\x1b[90m·\x1b[0m", WARN: "\x1b[33m!\x1b[0m",
         INFO: "\x1b[36mi\x1b[0m"}
W = 66


def _c(code, s):
  return (code + s + "\x1b[0m") if USE_COLOR else s


class Report:
  """Collects results and prints them as a coloured ASCII run."""

  def __init__(self):
    self.rows = []       # (status, label, detail, child)
    self._notes = []     # top-level INFO rows, held back to the very end
    self._sec = None
    self.oled = None     # if an OLED is found, live progress is shown on it
    self.version = "?"   # the on-Pico software version (picolab.VERSION)

  def _screen(self, label):
    # Mirror progress onto the OLED so you can watch the run with no computer.
    o = self.oled
    if not o:
      return
    try:
      c = self.counts()
      sec = (self._sec or "").split("(")[0].strip()
      o.fill(0)
      o.text("SELF-TEST", 0, 0)
      o.text(sec[:16], 0, 13)
      o.text(str(label)[:16], 0, 26)
      o.text("ok %d  fail %d" % (c[PASS], c[FAIL]), 0, 44)
      o.show()
    except Exception:
      self.oled = None   # OLED went away, stop mirroring

  def section(self, title):
    self._sec = title
    bar = " " + title + " "
    fill = W - 2 - len(bar)
    print("\n" + _c("\x1b[1;36m", "┌─" + bar + "─" * max(0, fill - 1) + "┐"))
    self._screen("...")

  def add(self, status, label, detail="", child=False, last=True):
    self.rows.append((status, label, detail, child))
    # INFO is not a pass or a fail, it is a reading. Hold top-level INFO
    # rows back and print them, boxless, in one block at the very end so
    # a blue tile never sits in the pass/fail column looking like a verdict.
    if status == INFO and not child:
      self._notes.append((label, detail))
      return
    if child:
      # a nested sub-step: proof the parent test actually did this piece
      glyph = _MINI[status] if USE_COLOR else _BADGE[status][2]
      branch = "└─" if last else "├─"
      pad = " " * max(1, 28 - len(label))
      det = _c("\x1b[2m", detail) if detail else ""
      print("       %s %s %s%s%s" % (branch, glyph, label, pad, det))
      return
    box, fg, plain = _BADGE[status]
    badge = box if USE_COLOR else plain
    lbl = _c(fg, label)
    # pad on the PLAIN length so colour codes do not throw off alignment
    pad = " " * max(1, 40 - len(label))
    det = _c("\x1b[2m", detail) if detail else ""
    print("  %s  %s%s%s" % (badge, lbl, pad, det))

  def _rollup(self, subs):
    sts = [s[0] for s in subs]
    if FAIL in sts:
      return FAIL
    if WARN in sts:
      return WARN
    return PASS

  def _tick(self, label):
    # Print what we are ABOUT to run, no newline, and flush it. If the board
    # hard-crashes mid-test (a servo browns it out, USB drops), the LAST line
    # you see names the culprit. On success it is overwritten by the result.
    if USE_COLOR:
      print("\r  \x1b[2m>> running: %s\x1b[0m\x1b[K" % label, end="")
    else:
      print("  >> running: %s" % label)
    try:
      import sys as _sys
      _sys.stdout.flush()
    except Exception:
      pass

  def _untick(self):
    if USE_COLOR:
      print("\r\x1b[K", end="")     # erase the breadcrumb before the result

  def run(self, label, fn):
    """Run one check. fn() returns (status, detail) for a simple check, or
    (status, detail, substeps) where substeps is a list of (status, label,
    detail). Pass status=None to roll the parent up from the substeps, so
    if ONE sub-step fails the parent goes red but you see which piece.
    Any exception the check did not handle becomes a FAIL, run continues."""
    self._tick(label)
    try:
      res = fn()
    except Exception as e:
      self._untick()
      self.add(FAIL, label, "check crashed: %s: %s" % (type(e).__name__, e))
      return FAIL
    self._untick()
    subs = res[2] if len(res) > 2 else []
    status = res[0] if res[0] is not None else self._rollup(subs)
    self.add(status, label, res[1])
    for i, (st, lab, det) in enumerate(subs):
      self.add(st, lab, det, child=True, last=(i == len(subs) - 1))
    self._screen(label)
    return status

  def counts(self):
    c = {PASS: 0, FAIL: 0, SKIP: 0, WARN: 0, INFO: 0}
    for row in self.rows:
      if not row[3]:            # tally parents only; sub-steps are evidence
        c[row[0]] += 1
    return c

  def flush_notes(self):
    if not self._notes:
      return
    print("\n" + _c("\x1b[2m", "  notes and readings  (informational, nothing to pass or fail)"))
    for label, detail in self._notes:
      pad = " " * max(1, 34 - len(label))
      print(_c("\x1b[2m", "     - " + label + pad + detail))

  def verdict(self):
    self.flush_notes()
    c = self.counts()
    print("\n" + _c("\x1b[36m", "└" + "─" * (W - 2) + "┘"))
    tally = "  %d ok   %d fail   %d skipped   %d warn" % (
        c[PASS], c[FAIL], c[SKIP], c[WARN])
    print(tally)
    if c[FAIL]:
      msg = "  NOT READY: fix %d red item(s) before handing out boards  " % c[FAIL]
      code = "\x1b[1;41;97m"
    elif c[WARN]:
      msg = "  READY, WITH NOTES: skim the yellow items above  "
      code = "\x1b[1;43;30m"
    else:
      msg = "  READY FOR CLASS: this board is healthy  "
      code = "\x1b[1;42;30m"
    print("\n" + _c(code, msg + " " * max(0, W - len(msg))))
    print(_c("\x1b[2m", "  Pico software v" + self.version))
    if c[FAIL]:
      # Point at the repair tool. It backs the board up FIRST, then fixes,
      # then prints the exact restore-from-backup command to undo it.
      # NB: hwfix is a HOST shell script, run it in the terminal, NOT via
      # `mpremote run` (that would ship it to the board and it would not parse).
      print("\n" + _c("\x1b[2m", "  to back up and auto-repair, run this in the host shell"))
      print(_c("\x1b[2m", "  (a shell script, NOT `mpremote run`):"))
      print(_c("\x1b[1m", "      bash tools/hwfix.sh"))
    if self.oled:
      try:
        o = self.oled; o.fill(0)
        o.text("SELF-TEST DONE", 0, 0)
        o.text("ok %d  fail %d" % (c[PASS], c[FAIL]), 0, 14)
        o.text("READY!" if not c[FAIL] else "NOT READY", 0, 30)
        o.text(("fix %d red" % c[FAIL]) if c[FAIL] else ("sw v" + self.version), 0, 46)
        o.show()
      except Exception:
        pass


# =====================================================================
# The checks. Each returns (STATUS, "one-line detail").
# =====================================================================
def _fnv1a(data):
  """A tiny stable fingerprint of a byte string. New push => new number."""
  h = 0x811C9DC5
  for b in data:
    h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
  return h


def build_checks(rep, R):
  """R is a bundle of the platform bits (machine, os, ...) so the same
  code path is testable off-device. On the Pico R is the real thing."""
  machine, os, sys, gc, network, socket = (
      R["machine"], R["os"], R["sys"], R["gc"], R["network"], R["socket"])
  I2C, SoftI2C, Pin, ADC, PWM = (
      R["I2C"], R["SoftI2C"], R["Pin"], R["ADC"], R["PWM"])

  def _exists(path):
    try:
      os.stat(path)
      return True
    except Exception:
      return False

  def _listdir(path):
    try:
      return os.listdir(path)
    except Exception:
      return []

  def do(s, label, thunk):
    # Run one sub-step: record PASS + its detail, or FAIL with the reason,
    # and NEVER raise. So when one piece of a multi-step test fails, it
    # shows as a nested red line and the steps that DID pass still show.
    try:
      s.append((PASS, label, thunk()))
      return True
    except Exception as e:
      s.append((FAIL, label, "%s: %s" % (type(e).__name__, e)))
      return False

  # ---- locate the shared I2C bus on ANY clean pair, wake the OLED -------
  # Scan the same candidate pairs picolab uses, so the self-test finds the
  # sensor bank wherever it is plugged. If an OLED is on it, mirror progress.
  hw = {"bus": None, "found": set(), "pair": (0, 1), "ctl": 0}
  for ctl, sda, scl in I2C_CANDIDATES:
    try:
      b = I2C(ctl, sda=Pin(sda), scl=Pin(scl), freq=400000)
      f = set(b.scan())
    except Exception:
      continue
    if f:
      hw["bus"], hw["found"], hw["pair"], hw["ctl"] = b, f, (sda, scl), ctl
      break
  if hw["bus"] is None:
    try:
      hw["bus"] = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
    except Exception:
      pass
  if 0x3C in hw["found"]:
    try:
      import ssd1306
      rep.oled = ssd1306.SSD1306_I2C(128, 64, hw["bus"], addr=0x3C)
      rep.oled.fill(0)
      rep.oled.text("SELF-TEST", 0, 0)
      rep.oled.text("starting...", 0, 16)
      rep.oled.show()
    except Exception:
      rep.oled = None

  # ---- 1. FIRMWARE & RUNTIME ----------------------------------------
  rep.section("1. FIRMWARE & RUNTIME  (can this board run at all)")

  def c_mpy():
    v = ".".join(str(x) for x in sys.implementation.version[:3])
    return PASS, "MicroPython %s on %s" % (v, sys.platform)
  rep.run("MicroPython is running", c_mpy)

  def c_board():
    uid = "".join("%02x" % b for b in machine.unique_id())
    mhz = machine.freq() // 1000000
    ok = "rp2" in sys.platform or "RP2" in getattr(sys.implementation, "_machine", "")
    return (PASS if ok else WARN), "uid %s, %d MHz" % (uid, mhz)
  rep.run("Board identity (RP2 / Pico)", c_board)

  def c_ram():
    free = gc.mem_free()
    return (PASS if free > 40000 else WARN), "%d bytes free RAM" % free
  rep.run("Free RAM is healthy", c_ram)

  def c_flash():
    st = os.statvfs("/")
    free = st[0] * st[3]
    # A full flash silently makes the NEXT code push fail to write.
    return (PASS if free > 20000 else FAIL), "%d bytes free on flash" % free
  rep.run("Flash has room for a push", c_flash)

  def c_reset():
    rc = getattr(machine, "reset_cause", lambda: None)()
    names = {getattr(machine, n, -99): n for n in
             ("PWRON_RESET", "HARD_RESET", "WDT_RESET",
              "DEEPSLEEP_RESET", "SOFT_RESET")}
    label = names.get(rc, "cause %s" % rc)
    # A watchdog reset CAN mean a crash-on-startup loop, but it is also how
    # `mpremote run` soft-resets the board, so it is info, not an alarm:
    # only worry about WDT after a plain power-up boot.
    note = " (normal via mpremote; only odd on a cold boot)" if label == "WDT_RESET" else ""
    return INFO, "last reset: %s%s" % (label, note)
  rep.run("Last reset cause", c_reset)

  # ---- 2. DEPLOY / CODE-PUSH INTEGRITY ------------------------------
  rep.section("2. CODE PUSH  (did new code land in a bootable state)")

  def c_files():
    missing = [f for f in REQUIRED_FILES if not _exists(f)]
    if missing:
      return FAIL, "missing: " + ", ".join(missing)
    empty = [f for f in REQUIRED_FILES if os.stat(f)[6] == 0]
    if empty:
      return FAIL, "zero-byte (partial push): " + ", ".join(empty)
    return PASS, "%d required files present, non-empty" % len(REQUIRED_FILES)
  rep.run("Required files are all here", c_files)

  def c_mpy_shadow():
    # The classic: a leftover compiled .mpy sitting next to (or instead
    # of) the .py you just edited. import can load the STALE .mpy and your
    # change never runs. We ship .py only, so ANY .mpy is suspect.
    shipped = set(f.rsplit("/", 1)[-1][:-3] for f in REQUIRED_FILES
                  if f.endswith(".py"))
    shadow, stray = [], []
    for d in ("", "lib"):
      for n in _listdir(d or "/"):
        if n.endswith(".mpy"):
          stem = n[:-4]
          (shadow if stem in shipped else stray).append((d + "/" + n).lstrip("/"))
    if shadow:
      return FAIL, "stale .mpy shadows your source: " + ", ".join(shadow)
    if stray:
      return WARN, "stray .mpy files (delete if unexpected): " + ", ".join(stray)
    return PASS, "no compiled .mpy leftovers"
  rep.run("No stale .mpy shadowing .py", c_mpy_shadow)

  def c_scraps():
    scraps = []
    for d in ("", "lib"):
      for n in _listdir(d or "/"):
        if n.endswith("~") or n.endswith(".tmp") or n.endswith(".py.bak"):
          scraps.append((d + "/" + n).lstrip("/"))
    return (WARN, "editor/partial scraps: " + ", ".join(scraps)) if scraps \
        else (PASS, "no leftover backup/temp files")
  rep.run("No half-written / backup files", c_scraps)

  def c_imports():
    bad = []
    for m in REQUIRED_IMPORTS:
      try:
        __import__(m)
      except Exception as e:
        bad.append("%s (%s)" % (m, type(e).__name__))
    if bad:
      return FAIL, "import fails: " + ", ".join(bad)
    return PASS, "all %d modules import cleanly" % len(REQUIRED_IMPORTS)
  rep.run("Every library imports (no crash)", c_imports)

  def c_compile():
    # Syntax-check main.py WITHOUT running it (it is an infinite loop). A
    # syntax error here is exactly the "pushed bad code, board will not
    # boot" case, caught before you ever restart into it.
    try:
      with open("main.py") as f:
        src = f.read()
    except Exception as e:
      return FAIL, "cannot read main.py: %s" % e
    try:
      compile(src, "main.py", "exec")
    except SyntaxError as e:
      return FAIL, "main.py has a SyntaxError: %s" % e
    return PASS, "main.py compiles (would boot past import)"
  rep.run("main.py is syntactically bootable", c_compile)

  def c_fingerprint():
    try:
      with open("main.py", "rb") as f:
        data = f.read()
    except Exception as e:
      return FAIL, "no main.py: %s" % e
    fp = _fnv1a(data)
    # Read this out loud after a push: if it did not change, your push
    # did not land. Same number as last time == same old code.
    return INFO, "main.py = %d bytes, fingerprint %08X" % (len(data), fp)
  rep.run("Deployed-code fingerprint", c_fingerprint)

  def c_index():
    return (PASS, "index.html present (web page will serve)") if _exists("index.html") \
        else (WARN, "no index.html: sensors/screen work, web page will not")
  rep.run("Dashboard page present", c_index)

  # ---- 3. TRUTH LIGHT (the onboard LED) -----------------------------
  rep.section("3. TRUTH LIGHT  (the LED that proves code is running)")

  def c_led():
    led = Pin("LED", Pin.OUT)
    for _ in range(6):        # a visible wink so a human confirms it too
      led.on(); R["sleep_ms"](60); led.off(); R["sleep_ms"](60)
    return PASS, "onboard LED drives on/off (you should have seen it blink)"
  rep.run("Onboard LED responds", c_led)

  def c_statuslight():
    import picolab
    sl = picolab.StatusLight()
    sl.set_slots([True, False, True])   # a POST pattern
    for _ in range(40):                 # poll a short while, must not raise
      sl.poll(); R["sleep_ms"](5)
    sl.set_ok(False)
    if sl.led is None:
      return WARN, "StatusLight ran but found no LED pin"
    return PASS, "StatusLight POST engine polls cleanly"
  rep.run("StatusLight boot-signal works", c_statuslight)

  # ---- 4. NETWORK / PORT 80 -----------------------------------------
  rep.section("4. NETWORK  (the port-in-use bug from last run)")

  def c_port80():
    # The classroom headache: on a re-run the OLD web socket can still hold
    # port 80 and the app hits EADDRINUSE. Two things decide whether the NEXT
    # start whines: (a) is it free right now, and (b) does a server socket
    # RELEASE the port promptly when it closes. (b) is the predictive one: if
    # a just-closed server does not free the port, the next start collides.
    # We reproduce that with SO_REUSEADDR exactly as WebApp does.
    # NOTE: a full power-on / reset ALWAYS frees port 80; the only real risk
    # is a soft Stop+Run, which the app's retry/degrade also covers.
    s = []
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    def free_now():
      a = socket.socket(); a.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      try:
        a.bind(addr)
      finally:
        a.close()
      return "bindable this instant"
    def releases():
      a = socket.socket(); a.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      a.bind(addr); a.listen(1); a.close()      # a web server that just stopped
      b = socket.socket(); b.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      try:
        b.bind(addr)                            # can the NEXT start reclaim it?
      finally:
        b.close()
      return "frees cleanly, the next start will bind"
    if not do(s, "free right now", free_now):
      # already held even on this reset board: a genuinely stuck server
      s.append((FAIL, "diagnosis", "a stale server survived the reset, hard-reset the board"))
    do(s, "releases for the next start", releases)
    return None, "port 80 / address-in-use", s
  rep.run("Port 80 (address-in-use)", c_port80)

  def c_wifi():
    # A PASSIVE "is an AP up?" reading is meaningless here: the AP only
    # exists while your PROGRAM runs, but the self-test runs INSTEAD of your
    # program (mpremote soft-resets first), so normally no app AP is up, and
    # a soft reset clears leftover radio state only sometimes. So instead we
    # actively PROVE the radio: bring an AP up, confirm it activates, then
    # leave it the way we found it. This passes on any healthy board and
    # fails only if the Wi-Fi chip is genuinely dead.
    s = []; box = {}
    def bring_up():
      ap = network.WLAN(network.AP_IF)
      box["ap"] = ap
      box["was"] = ap.active()
      ap.active(True)
      for _ in range(20):
        if ap.active():
          return "AP interface active"
        R["sleep_ms"](100)
      raise OSError("AP did not activate (CYW43 fault?)")
    def restore():
      ap = box.get("ap")
      if ap and not box.get("was"):
        ap.active(False)           # put it back down if it was down
      return "radio released"
    do(s, "bring up an AP", bring_up)
    do(s, "release radio", restore)
    return None, "Wi-Fi radio (CYW43)", s
  rep.run("Wi-Fi AP radio", c_wifi)

  # ---- 5. I2C BUS HEALTH --------------------------------------------
  rep.section("5. I2C BUS  (auto-located pair)")

  def c_idle():
    # With an internal pull-up, a line that still reads LOW is being held
    # down by something: a device stuck in the wrong mode (a 6-pin BME280
    # with a floating CSB drops into SPI and HANGS the bus), or a short.
    sda_gp, scl_gp = hw["pair"]
    sp = Pin(sda_gp, Pin.IN, Pin.PULL_UP)
    cp = Pin(scl_gp, Pin.IN, Pin.PULL_UP)
    R["sleep_ms"](2)
    lo = [n for n, p in (("SDA/GP%d" % sda_gp, sp), ("SCL/GP%d" % scl_gp, cp)) if p.value() == 0]
    # we just muxed the bus pins to inputs; put the I2C peripheral back
    try:
      hw["bus"] = I2C(hw["ctl"], sda=Pin(sda_gp), scl=Pin(scl_gp), freq=400000)
    except Exception:
      pass
    if lo:
      return FAIL, "%s stuck LOW: a part is hanging the bus (floating-CSB BME280?)" % "+".join(lo)
    return PASS, "SDA/SCL on GP%d/GP%d idle high (bus not hung)" % (sda_gp, scl_gp)
  rep.run("Bus lines are not stuck low", c_idle)

  def c_hwscan():
    found = hw["found"]
    sda_gp, scl_gp = hw["pair"]
    where = "" if (sda_gp, scl_gp) == (0, 1) else " on GP%d/GP%d (not the default)" % (sda_gp, scl_gp)
    if not found:
      return WARN, "no I2C devices on any candidate pair (fine for a bare Pico)"
    known = ["0x%02x %s" % (a, n) for a, n in KNOWN if a in found]
    extra = ["0x%02x" % a for a in sorted(found) if a not in dict(KNOWN)]
    detail = "found%s: %s" % (where, ", ".join(known or ["(none known)"]))
    if extra:
      detail += "  + unknown " + ",".join(extra)
    return PASS, detail
  rep.run("Hardware I2C scan", c_hwscan)

  # ---- 6. EACH I2C PART THAT IS PRESENT -----------------------------
  rep.section("6. SENSORS  (only the ones plugged in; absent = skip)")

  def _present(addr):
    return addr in hw["found"]

  def _bme(addr, name):
    def c():
      if not _present(addr):
        return SKIP, "no device at 0x%02x (skip)" % addr, []
      s = []; box = {}
      def rid():
        cid = hw["bus"].readfrom_mem(addr, 0xD0, 1)[0]   # chip-id register
        if cid not in (0x60, 0x58):
          raise OSError("chip-id 0x%02x is not a BME/BMP280" % cid)
        return "0x%02x (%s)" % (cid, "BME280" if cid == 0x60 else "BMP280")
      def mk():
        from bme280 import BME280
        box["d"] = BME280(hw["bus"], address=addr)
        return "driver ready"
      def rd():
        t, p, h = box["d"].read()
        return "%.1f C, %.0f hPa, %s" % (t, p, "%.0f%%" % h if h is not None else "no-hum")
      if do(s, "responds at 0x%02x" % addr, lambda: "ack") \
          and do(s, "chip-id", rid) and do(s, "init driver", mk):
        do(s, "sample read", rd)
      return None, "%s air sensor" % name, s
    return c
  rep.run("BME280 in  (0x76)", _bme(0x76, "in"))
  rep.run("BME280 out (0x77)", _bme(0x77, "out"))

  def c_ads():
    if not _present(0x48):
      return SKIP, "no ADS1115 at 0x48 (skip)", []
    s = []; box = {}
    def cfg():
      b = hw["bus"].readfrom_mem(0x48, 1, 2)     # config register
      return "0x%02x%02x" % (b[0], b[1])
    def mk():
      from ads1115 import ADS1115
      box["d"] = ADS1115(hw["bus"]); return "driver ready"
    if do(s, "config register", cfg) and do(s, "init driver", mk):
      do(s, "A0 conversion", lambda: "%.3f V" % box["d"].read_volts(0))
      do(s, "A1 conversion", lambda: "%.3f V" % box["d"].read_volts(1))
    return None, "ADS1115 analog bank", s
  rep.run("ADS1115 analog bank (0x48)", c_ads)

  def c_vl():
    if not _present(0x29):
      return SKIP, "no VL53L0X at 0x29 (skip)", []
    s = []; box = {}
    def mid():
      m = hw["bus"].readfrom_mem(0x29, 0xC0, 1)[0]   # model id, expect 0xEE
      if m != 0xEE:
        raise OSError("model-id 0x%02x != 0xEE" % m)
      return "0x%02x" % m
    def mk():
      from vl53l0x import VL53L0X
      box["d"] = VL53L0X(hw["bus"]); return "init sequence ok"
    if do(s, "model-id", mid) and do(s, "init sensor", mk):
      do(s, "range ping", lambda: "%s mm" % box["d"].ping())
    return None, "VL53L0X distance", s
  rep.run("VL53L0X distance (0x29)", c_vl)

  def c_bh():
    if not _present(0x23):
      return SKIP, "no BH1750 at 0x23 (skip)", []
    s = []; box = {}
    def mk():
      from bh1750 import BH1750
      box["d"] = BH1750(hw["bus"]); return "powered + hi-res"
    if do(s, "power on", mk):
      do(s, "lux read", lambda: "%.1f lux" % box["d"].read())
    return None, "BH1750 lux", s
  rep.run("BH1750 lux (0x23)", c_bh)

  # ---- 7. THE OLED BIG-WRITE (pull-up stress) -----------------------
  rep.section("7. OLED STRESS  (the full-screen-write / pull-up bug)")

  def c_oled():
    if not _present(0x3C):
      return SKIP, "no OLED at 0x3C (skip)", []
    # A full frame is a ~1KB single write. WITHOUT proper pull-ups it is
    # the first thing to fail on hardware I2C, while a scan still passes.
    s = []; box = {}
    def mk():
      import ssd1306
      box["o"] = ssd1306.SSD1306_I2C(128, 64, hw["bus"], addr=0x3C)
      return "SSD1306 up"
    def big():
      box["o"].fill(1); box["o"].show()          # the ~1KB write
      R["sleep_ms"](150)
      return "1KB frame accepted (pull-ups fine)"
    def txt():
      o = box["o"]; o.fill(0)
      o.text("SELFTEST OK", 0, 0)
      o.text("MakerLabKids", 0, 12)
      o.show()
      return "wrote 'SELFTEST OK' to the screen"
    if do(s, "driver init", mk) and do(s, "full-frame write", big):
      do(s, "text + show", txt)
    return None, "OLED display", s
  rep.run("OLED full-frame write (0x3C)", c_oled)

  # ---- 8. HARDWARE I2C vs SOFTWARE I2C ------------------------------
  rep.section("8. HW vs SOFT I2C  (which bus mode actually works)")

  def c_soft():
    # Bit-banged SoftI2C tolerates weak pull-ups better than the hardware
    # peripheral. If SOFT sees devices the HARDWARE scan missed, the wiring
    # (pull-ups/timing) is marginal and hardware I2C, which the firmware
    # uses, will be flaky. This is the fallback diagnosis.
    sda_gp, scl_gp = hw["pair"]
    soft = SoftI2C(sda=Pin(sda_gp), scl=Pin(scl_gp), freq=100000)
    R["sleep_ms"](2)
    sfound = set(soft.scan())
    hfound = hw["found"]
    fmt = lambda a: ",".join("0x%02x" % x for x in sorted(a)) or "(none)"
    s = [(INFO, "hardware scan", "%d found: %s" % (len(hfound), fmt(hfound))),
         (INFO, "software scan", "%d found: %s" % (len(sfound), fmt(sfound)))]
    only_soft = sfound - hfound
    if not hfound and not sfound:
      s.append((SKIP, "compare", "bus empty on both (bare Pico)"))
      return SKIP, "nothing on the bus to compare", s
    if only_soft:
      s.append((FAIL, "compare", "soft-only %s: weak pull-ups / timing" % fmt(only_soft)))
    elif hfound - sfound:
      s.append((WARN, "compare", "hardware saw more than soft (recheck)"))
    else:
      s.append((PASS, "compare", "both buses agree"))
    return None, "hardware vs soft agreement", s
  rep.run("Hardware/soft I2C agree", c_soft)
  # hand the shared bus back to the hardware peripheral for anything after
  try:
    sda_gp, scl_gp = hw["pair"]
    hw["bus"] = I2C(hw["ctl"], sda=Pin(sda_gp), scl=Pin(scl_gp), freq=400000)
  except Exception:
    pass

  # ---- 9. NON-I2C PARTS ---------------------------------------------
  rep.section("9. DIRECT-WIRED PARTS  (blind pins: watch/listen to confirm)")

  def c_onewire():
    import onewire
    import ds18x20
    ds = ds18x20.DS18X20(onewire.OneWire(Pin(PROBE_PIN)))
    roms = ds.scan()
    if not roms:
      return SKIP, "no DS18B20 probe on GP%d" % PROBE_PIN
    ds.convert_temp()
    R["sleep_ms"](750)
    t = ds.read_temp(roms[0])
    return PASS, "%d probe(s), first = %.1f C" % (len(roms), t)
  rep.run("DS18B20 1-wire (GP22)", c_onewire)

  def _adc(pin, label):
    def c():
      a = ADC(pin)
      lo, hi = 65535, 0
      for _ in range(200):
        v = a.read_u16()
        lo = min(lo, v); hi = max(hi, v)
      # An ADC pin cannot tell "unplugged" from "quiet", so we only prove
      # it is sampling. A dead-flat rail at 0 or 65535 is suspicious.
      if lo == hi and lo in (0, 65535):
        return WARN, "%s reads a flat %d (open pin? nothing attached)" % (label, lo)
      return INFO, "%s sampling, span %d..%d /65535" % (label, lo, hi)
    return c
  rep.run("Mic ADC (GP27)", _adc(MIC_PIN, "mic"))
  rep.run("Light ADC (GP28)", _adc(LIGHT_PIN, "light"))

  def _servo(pin):
    def c():
      # A blind output pin: nothing here can tell the code a servo is even
      # attached, so this is WATCH-AND-CONFIRM. Pulse range matches main.py
      # (600..2400 us). A servo takes a POSITION, not a speed, so its first
      # move happens at the servo's own full speed and can spike a weak
      # supply, but we keep the excursion tiny and RAMP the wiggle in small
      # 2 deg steps so it is a series of little low-current nudges, not a
      # snap. A big high-current servo (MG995) on a marginal 5V can still
      # brown the board out here: set MOVE_SERVOS=False, or give it a cap /
      # its own supply. Full sweep only under ACTUATE.
      pwm = PWM(Pin(pin))
      pwm.freq(50)
      def write(deg):
        pwm.duty_u16(int((600 + (deg / 180.0) * 1800) * 65535 / 20000))
      if not MOVE_SERVOS:
        pwm.deinit()
        return INFO, "GP%d PWM ready (not moved, MOVE_SERVOS=False)" % pin
      def ramp(a, b):
        step = 2 if b >= a else -2
        d = a
        while (d - b) * step < 0:
          d += step
          write(min(max(d, min(a, b)), max(a, b)))
          R["sleep_ms"](25)
      lo, hi = (0, 180) if ACTUATE else (80, 100)
      write(90); R["sleep_ms"](120)            # centre once
      ramp(90, lo); ramp(lo, hi); ramp(hi, 90)  # gentle low-current wiggle
      pwm.deinit()
      return INFO, "watch GP%d: ramped %d..%d deg (board resets here = weak servo 5V)" % (pin, lo, hi)
    return c
  rep.run("Servo PWM (GP16)", _servo(16))
  rep.run("Servo PWM (GP17)", _servo(17))

  def c_relay():
    # Also blind. A brief click is the only confirmation, but the relay
    # switches a REAL load (the heat mat), so it stays behind ACTUATE.
    r = Pin(RELAY_PIN, Pin.OUT)
    r.value(0)
    if ACTUATE:
      r.value(1); R["sleep_ms"](250); r.value(0)
      return INFO, "listen GP%d: clicked once on/off" % RELAY_PIN
    return INFO, "GP%d ready, left OFF (set ACTUATE=True to click it)" % RELAY_PIN
  rep.run("Relay (GP15)", c_relay)


# =====================================================================
# Entry points: real hardware, or an off-device preview.
# =====================================================================
def _real_bundle():
  import machine, os, sys, gc, network, socket, time
  from machine import I2C, SoftI2C, Pin, ADC, PWM
  return {"machine": machine, "os": os, "sys": sys, "gc": gc,
          "network": network, "socket": socket, "I2C": I2C,
          "SoftI2C": SoftI2C, "Pin": Pin, "ADC": ADC, "PWM": PWM,
          "sleep_ms": time.sleep_ms}


def _header(rep, live):
  tag = "LIVE on hardware" if live else "SIMULATED PREVIEW (no board attached)"
  try:
    import picolab
    who = "%s   uid %s" % (picolab.station_name(), picolab.board_uid())
    rep.version = getattr(picolab, "VERSION", "?")
  except Exception:
    who = "board id unavailable"
  print(_c("\x1b[1;36m", "╔" + "═" * (W - 2) + "╗"))
  for ln in ("  MAKER LAB KIDS - PICO 2 W HARDWARE SELF-TEST",
             "  " + who, "  Pico software v" + rep.version + "   (" + tag + ")"):
    print(_c("\x1b[1;36m", "║") + ln + " " * max(0, W - 2 - len(ln)) + _c("\x1b[1;36m", "║"))
  print(_c("\x1b[1;36m", "╚" + "═" * (W - 2) + "╝"))
  print("  legend:  %s ok   %s fail   %s skip(absent)   %s warn   %s info"
        % (_BADGE[PASS][0] if USE_COLOR else "OK",
           _BADGE[FAIL][0] if USE_COLOR else "FAIL",
           _BADGE[SKIP][0] if USE_COLOR else "skip",
           _BADGE[WARN][0] if USE_COLOR else "warn",
           _BADGE[INFO][0] if USE_COLOR else "info"))


def main():
  rep = Report()
  try:
    bundle = _real_bundle()
    live = True
  except Exception:
    bundle = None
    live = False
  _header(rep, live)
  if live:
    build_checks(rep, bundle)
  else:
    _preview(rep)
  rep.verdict()


def _preview(rep):
  """Feed the reporter a realistic canned run so the format can be seen
  on a laptop. This does NOT touch hardware and is only for previewing;
  the true results come from running on the Pico."""
  demo = [
    ("1. FIRMWARE & RUNTIME  (can this board run at all)", [
      (PASS, "MicroPython is running", "MicroPython 1.24.1 on rp2"),
      (PASS, "Board identity (RP2 / Pico)", "uid e6614c311b7f2935, 150 MHz"),
      (PASS, "Free RAM is healthy", "191840 bytes free RAM"),
      (PASS, "Flash has room for a push", "704512 bytes free on flash"),
      (INFO, "Last reset cause", "last reset: PWRON_RESET")]),
    ("2. CODE PUSH  (did new code land in a bootable state)", [
      (PASS, "Required files are all here", "7 required files present, non-empty"),
      (FAIL, "No stale .mpy shadowing .py", "stale .mpy shadows your source: lib/picolab.mpy"),
      (PASS, "No half-written / backup files", "no leftover backup/temp files"),
      (PASS, "Every library imports (no crash)", "all 8 modules import cleanly"),
      (PASS, "main.py is syntactically bootable", "main.py compiles (would boot past import)"),
      (INFO, "Deployed-code fingerprint", "main.py = 11840 bytes, fingerprint 3AF19C02"),
      (PASS, "Dashboard page present", "index.html present (web page will serve)")]),
    ("3. TRUTH LIGHT  (the LED that proves code is running)", [
      (PASS, "Onboard LED responds", "you should have seen it blink"),
      (PASS, "StatusLight boot-signal works", "StatusLight POST engine polls cleanly")]),
    ("4. NETWORK  (the port-in-use bug from last run)", [
      (FAIL, "Port 80 (address-in-use)", "port 80 / address-in-use", [
        (PASS, "free right now", "bindable this instant"),
        (FAIL, "releases for the next start", "OSError: [Errno 98] EADDRINUSE - next start collides")]),
      (PASS, "Wi-Fi AP radio", "Wi-Fi radio (CYW43)", [
        (PASS, "bring up an AP", "AP interface active"),
        (PASS, "release radio", "radio released")])]),
    ("5. I2C BUS  (GP0/GP1, the shared sensor bus)", [
      (PASS, "Bus lines are not stuck low", "SDA and SCL idle high (bus not hung)"),
      (PASS, "Hardware I2C scan", "found: 0x3c OLED SSD1306, 0x76 BME280 in, 0x23 BH1750 lux")]),
    ("6. SENSORS  (only the ones plugged in; absent = skip)", [
      (PASS, "BME280 in  (0x76)", "in air sensor", [
        (PASS, "responds at 0x76", "ack"),
        (PASS, "chip-id", "0x60 (BME280)"),
        (PASS, "init driver", "driver ready"),
        (PASS, "sample read", "22.6 C, 1001 hPa, 46%")]),
      # a PARTIAL failure: the part answers, but a later step fails. The
      # parent goes red and the nested line pins the blame.
      (FAIL, "BME280 out (0x77)", "out air sensor", [
        (PASS, "responds at 0x77", "ack"),
        (FAIL, "chip-id", "OSError: chip-id 0xff is not a BME/BMP280")]),
      (SKIP, "ADS1115 analog bank (0x48)", "no ADS1115 at 0x48 (skip)"),
      (SKIP, "VL53L0X distance (0x29)", "no VL53L0X at 0x29 (skip)"),
      (PASS, "BH1750 lux (0x23)", "BH1750 lux", [
        (PASS, "power on", "powered + hi-res"),
        (PASS, "lux read", "134.2 lux")])]),
    ("7. OLED STRESS  (the full-screen-write / pull-up bug)", [
      (PASS, "OLED full-frame write (0x3C)", "OLED display", [
        (PASS, "driver init", "SSD1306 up"),
        (PASS, "full-frame write", "1KB frame accepted (pull-ups fine)"),
        (PASS, "text + show", "wrote 'SELFTEST OK' to the screen")])]),
    ("8. HW vs SOFT I2C  (which bus mode actually works)", [
      (PASS, "Hardware/soft I2C agree", "hardware vs soft agreement", [
        (INFO, "hardware scan", "3 found: 0x23,0x3c,0x76"),
        (INFO, "software scan", "3 found: 0x23,0x3c,0x76"),
        (PASS, "compare", "both buses agree")])]),
    ("9. DIRECT-WIRED PARTS  (ADC, 1-wire, actuators)", [
      (SKIP, "DS18B20 1-wire (GP22)", "no DS18B20 probe on GP22"),
      (INFO, "Mic ADC (GP27)", "mic sampling, span 244..61201 /65535"),
      (INFO, "Light ADC (GP28)", "light sampling, span 30112..30640 /65535"),
      (INFO, "Servo PWM (GP16)", "watch GP16: wiggled 90/70/110/90 deg"),
      (INFO, "Servo PWM (GP17)", "watch GP17: wiggled 90/70/110/90 deg"),
      (INFO, "Relay (GP15)", "GP15 ready, left OFF (set ACTUATE=True to click it)")]),
  ]
  for title, rows in demo:
    rep.section(title)
    for row in rows:
      st, label, detail = row[0], row[1], row[2]
      subs = row[3] if len(row) > 3 else []
      rep.add(st, label, detail)
      for i, (cst, clab, cdet) in enumerate(subs):
        rep.add(cst, clab, cdet, child=True, last=(i == len(subs) - 1))


main()
