# picolab.py - shared plumbing for Maker Lab Kids Pico 2 W demos.
#
# Every demo follows the same rules:
#   * Nothing crashes because a part is missing or flaky.
#   * The OLED is optional. If it is absent (or dies) the demo keeps going
#     and quietly retries it every few seconds.
#   * Sensors are optional AND hot-pluggable: plug one in mid-run and it
#     starts reporting within a couple of seconds, no restart needed.
#   * Terminal logging: a startup banner and first readings immediately,
#     then a slow heartbeat so the terminal stays readable.
#   * The onboard LED is a truth light (StatusLight): if code is running
#     the light is active, and blink codes say which part is unhappy.
#   * Each board has a PERMANENT identity from its hardware serial:
#     name "PicoLab<4hex>" (or name.txt), reported with its IP at /data.
#   * Web demos either JOIN a network (wifi.json, with a rescue ladder)
#     or open their own access point, serving index.html and /data.

import json
import socket
import time
from machine import I2C, Pin, unique_id

_i2c = None


def i2c():
  """The shared I2C0 bus: SDA=GP0, SCL=GP1, 400kHz. (Hardware I2C is fine;
  the "displays down" bug was never here -- see the port-80 handling.)"""
  global _i2c
  if _i2c is None:
    _i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
  return _i2c


def _uptime():
  return time.ticks_ms() // 1000


def log(*args):
  print("[%4ds]" % _uptime(), *args)


def banner(title, lines=()):
  print("\n" + "=" * 40)
  print(title)
  for ln in lines:
    print("  " + ln)
  print("=" * 40)


class Throttle:
  """True at most once every interval_ms. First call is True immediately."""

  def __init__(self, interval_ms):
    self.interval = interval_ms
    self._next = time.ticks_ms()

  def ready(self):
    now = time.ticks_ms()
    if time.ticks_diff(now, self._next) >= 0:
      self._next = time.ticks_add(now, self.interval)
      return True
    return False


class StatusLight:
  """The onboard LED as a truth light. Poll it; it never blocks.

  If code is running, the light is doing something. Modes:

    set_ok(bool)    Simplest demos: solid ON means working, OFF means not.
    set_slots(list) POST blinks: one blink per entry, in a fixed order,
                    then a pause, then repeat. Short blink = that part is
                    OK. Long blink = that part is in trouble. So with five
                    probes, ". . . _ ." means probe 4 has a problem.
    set_number(n)   Blink a number 0-999 by place, so a board with NO
                    display can still tell you its address. LONG blinks =
                    hundreds, MEDIUM = tens, SHORT = ones, a zero place is
                    skipped, and the blink SPEED tells you the place so
                    skipping is never ambiguous. 203 = two long, (skip),
                    three short. 42 = four medium, two short. Big pause
                    between repeats. Read the last octet of the IP this
                    way and you can browse straight to the station.

  No blinking at all means the code is not running. Call poll() every
  trip through the main loop (50 ms or faster keeps the blinks crisp).
  """

  SHORT_MS = 110
  MED_MS = 330
  LONG_MS = 640
  GAP_MS = 240          # between blinks within one place
  GROUP_GAP_MS = 780    # between places (hundreds -> tens -> ones)
  PAUSE_MS = 1400       # between repeats of a slot pattern
  NUM_PAUSE_MS = 2600   # longer, so a number's repeat boundary is obvious

  def __init__(self):
    try:
      self.led = Pin("LED", Pin.OUT)
      self.led.off()
    except Exception:
      self.led = None
    self._solid = None
    # A schedule is a list of (on_ms, gap_after_ms) pulses, played in
    # order, then _pause, then repeat. set_slots/set_number build one.
    self._sched = [(self.SHORT_MS, self.GAP_MS)]
    self._pause = self.PAUSE_MS
    self._cycle = None
    self._i = 0
    self._lit = False
    self._until = time.ticks_ms()

  def set_ok(self, ok):
    self._solid = bool(ok)

  def set_slots(self, slots):
    self._solid = None
    sl = [bool(s) for s in slots] or [False]
    self._sched = [(self.SHORT_MS if s else self.LONG_MS, self.GAP_MS) for s in sl]
    self._pause = self.PAUSE_MS

  def set_number(self, n):
    self._solid = None
    n = max(0, min(999, int(n)))
    sched = []
    for count, dur in ((n // 100, self.LONG_MS),
                       (n // 10 % 10, self.MED_MS),
                       (n % 10, self.SHORT_MS)):
      for k in range(count):
        gap = self.GROUP_GAP_MS if k == count - 1 else self.GAP_MS
        sched.append((dur, gap))
    self._sched = sched or [(self.SHORT_MS, self.GAP_MS)]  # 0 -> a lone blip
    self._pause = self.NUM_PAUSE_MS

  def poll(self):
    if not self.led:
      return
    if self._solid is not None:
      self.led.value(1 if self._solid else 0)
      return
    now = time.ticks_ms()
    if time.ticks_diff(now, self._until) < 0:
      return
    if self._lit:
      self.led.off()
      self._lit = False
      _, gap = self._cycle[self._i]
      self._i += 1
      if self._i >= len(self._cycle):
        self._cycle = None
        self._until = time.ticks_add(now, self._cyclepause)
      else:
        self._until = time.ticks_add(now, gap)
    else:
      if self._cycle is None:
        self._cycle = self._sched[:]      # snapshot so mid-play edits are clean
        self._cyclepause = self._pause
        self._i = 0
      on, _ = self._cycle[self._i]
      self.led.on()
      self._lit = True
      self._until = time.ticks_add(now, on)


class Display:
  """SSD1306 wrapper that never raises. Retries the display every 3 s."""

  def __init__(self, addr=0x3C):
    self.addr = addr
    self.oled = None
    self._retry = Throttle(3000)
    self._was_ok = False

  @property
  def present(self):
    return self.oled is not None

  def _connect(self):
    try:
      import ssd1306

      o = ssd1306.SSD1306_I2C(128, 64, i2c(), addr=self.addr)
      # Clear display RAM snow and wake charge pump
      o.poweroff()
      time.sleep_ms(50)
      o.poweron()
      time.sleep_ms(50)
      o.fill(0)
      o.show()
      self.oled = o
      if not self._was_ok:
        log("OLED connected.")
      self._was_ok = True
    except Exception:
      self.oled = None

  def show(self, lines, bar=None):
    """Draw up to 5 text rows plus an optional 0.0-1.0 bar at the bottom."""
    if not self.oled and self._retry.ready():
      self._connect()
    if not self.oled:
      return
    try:
      o = self.oled
      o.fill(0)
      for idx, text in enumerate(lines[:5]):
        o.text(str(text)[:16], 0, idx * 11)
      if bar is not None:
        width = int(min(1.0, max(0.0, bar)) * 128)
        o.rect(0, 58, 128, 6, 1)
        o.fill_rect(0, 58, width, 6, 1)
      o.show()
    except Exception as e:
      log("OLED lost:", e)
      self.oled = None


class Sensor:
  """Hot-pluggable sensor wrapper.

  connect() must return a device object (raise if the part is absent).
  read(dev) must return a dict of values (raise if the part vanished).
  poll() keeps .data fresh and never raises; .ok says if the part is alive.
  """

  def __init__(self, name, connect, read, retry_ms=2000):
    self.name = name
    self._connect = connect
    self._read = read
    self.dev = None
    self.data = None
    self._retry = Throttle(retry_ms)

  @property
  def ok(self):
    return self.dev is not None

  def poll(self):
    if self.dev is None:
      if not self._retry.ready():
        return self.data
      try:
        self.dev = self._connect()
      except Exception:
        self.dev = None
        return self.data
      try:
        self.data = self._read(self.dev)
        log(self.name, "connected. First reading:", self.data)
      except Exception:
        self.data = None
      return self.data
    try:
      self.data = self._read(self.dev)
    except Exception as e:
      log(self.name, "lost:", e)
      self.dev = None
      self.data = None
    return self.data


class Placements:
  """Labels + positions for probes, persisted on the board.

  Any probe with a stable id can be placed: a DS18B20's ROM serial
  (burned in at the factory, survives rewiring), an ADS1115 channel
  ("A0"), whatever. The file (default placements.json) maps
  id -> {"label": str, "pos": [x, y, z] or None} and can be edited
  from a dashboard (see handle()) or by hand in the Viper file panel,
  so a sticky label on the wire stays in sync either way.
  """

  def __init__(self, path="placements.json"):
    self.path = path
    try:
      with open(path) as f:
        self.data = json.load(f)
    except Exception:
      self.data = {}

  def get(self, pid):
    ent = self.data.get(pid, {})
    return ent.get("label") or pid[-4:], ent.get("pos")

  def save(self):
    try:
      with open(self.path, "w") as f:
        json.dump(self.data, f)
    except Exception as e:
      log("placements save failed:", e)

  def handle(self, req):
    """Route handler for /place?id=X&label=Y&x=0&y=1&z=2 (label and
    position each optional; empty x clears the position)."""
    pid = query_str(req, "id")
    if not pid:
      return {"error": "no id"}
    ent = self.data.get(pid, {})
    label = query_str(req, "label")
    if label is not None:
      ent["label"] = label
    xs = query_str(req, "x")
    if xs is not None:
      try:
        ent["pos"] = [float(query_str(req, a, "0") or 0) for a in "xyz"]
      except ValueError:
        ent["pos"] = None
      if xs == "":
        ent["pos"] = None
    self.data[pid] = ent
    self.save()
    log("placed", pid, "->", ent)
    return {"ok": True, "id": pid, "ent": ent}


class Calibration:
  """Per-sensor linear calibration, persisted on the board (cal.json).

  value = raw * scale + offset, applied AT THE SOURCE so the OLED, the
  JSON, and every dashboard agree. Keyed by the same permanent ids as
  Placements. Two-point (ice slurry = 0, boiling = 100) or one-point
  (offset to a known-true value), and resettable. The file is read at
  boot; no file = no correction.
  """

  def __init__(self, path="cal.json"):
    self.path = path
    try:
      with open(path) as f:
        self.data = json.load(f)
    except Exception:
      self.data = {}

  def apply(self, pid, raw, digits=2):
    if raw is None:
      return None
    ent = self.data.get(pid)
    if not ent:
      return raw
    return round(raw * ent.get("scale", 1.0) + ent.get("offset", 0.0), digits)

  def save(self):
    try:
      with open(self.path, "w") as f:
        json.dump(self.data, f)
    except Exception as e:
      log("cal save failed:", e)

  def handle(self, req):
    """Route handler. /cal?id=X&reset=1 clears. Two-point:
    /cal?id=X&raw1=..&act1=..&raw2=..&act2=..  One-point offset:
    /cal?id=X&raw1=<reading>&act1=<true value>."""
    pid = query_str(req, "id")
    if not pid:
      return {"error": "no id"}
    if query_str(req, "reset") is not None:
      self.data.pop(pid, None)
      self.save()
      log("cal reset", pid)
      return {"ok": True, "id": pid, "cal": None}
    try:
      r1 = float(query_str(req, "raw1"))
      a1 = float(query_str(req, "act1"))
    except (TypeError, ValueError):
      return {"error": "need raw1 and act1"}
    r2s = query_str(req, "raw2")
    a2s = query_str(req, "act2")
    if r2s and a2s:
      try:
        r2 = float(r2s)
        a2 = float(a2s)
      except ValueError:
        return {"error": "bad raw2/act2"}
      if r2 == r1:
        return {"error": "two points need different raw readings"}
      scale = (a2 - a1) / (r2 - r1)
      offset = a1 - scale * r1
    else:
      scale = 1.0
      offset = a1 - r1
    self.data[pid] = {"scale": round(scale, 6), "offset": round(offset, 4)}
    self.save()
    log("cal", pid, "->", self.data[pid])
    return {"ok": True, "id": pid, "cal": self.data[pid]}


# ---------------------------------------------------------------------
# Web app + board identity.
# ---------------------------------------------------------------------
NAME_FILE = "name.txt"

HEADER_HTML = b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n"
HEADER_JSON = b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n"

_CTYPES = {"js": "application/javascript", "css": "text/css", "html": "text/html",
           "svg": "image/svg+xml", "json": "application/json", "txt": "text/plain"}


def _req_path(req):
  """Pull the path out of a raw 'GET /path HTTP/1.0' request."""
  try:
    text = req.decode() if isinstance(req, bytes) else req
    parts = text.split(" ", 2)
    return parts[1] if len(parts) > 1 else None
  except Exception:
    return None


def _static_header(name):
  ext = name.rsplit(".", 1)[-1] if "." in name else ""
  ct = _CTYPES.get(ext, "application/octet-stream")
  return ("HTTP/1.0 200 OK\r\nContent-Type: " + ct
          + "\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n").encode()


def _try_join(sta, ssid, password, attempts=2, wait_s=12):
  """Try to join one network a couple of times. Returns True on success.
  Two tries because a single attempt at weak signal is a coin flip."""
  for _ in range(attempts):
    try:
      sta.connect(ssid, password)
      for _ in range(wait_s * 2):
        if sta.isconnected():
          return True
        time.sleep_ms(500)
    except Exception:
      pass
    if sta.isconnected():
      return True
    try:
      sta.disconnect()
    except Exception:
      pass
    time.sleep(1)
  return sta.isconnected()


def status(light, slots, display, app):
  """Drive the truth light for a web station. Normally POST codes for the
  parts (slots). But if the OLED is MISSING, the light instead blinks the
  board's locator number (IP octet, or AP number) so you can still reach
  the web interface. Sensors do not matter if you can't find the page."""
  if display.present:
    light.set_slots(slots)
  else:
    light.set_number(app.locate())


def board_uid():
  """The board's PERMANENT, globally-unique id: the factory-burned flash
  serial (16 hex chars). Same every boot, survives a re-flash and a
  wiped filesystem. This is the identity to TRUST when it must be
  unique. It is long, so it is not what you read off the screen."""
  return "".join("%02x" % b for b in unique_id())


def board_num():
  """A SHORT, stable number (0-999) derived from the permanent uid: the
  friendly tag you read off the OLED and type into a rescue-hotspot
  name. Same forever (survives re-flash). Not guaranteed unique in a
  big room (a collision or two among 50 boards is possible); when it
  matters, board_uid() is the unique id and name.txt lets you rename."""
  return int(board_uid()[-6:], 16) % 1000


def station_name():
  """A short, STABLE, human-friendly name for this board.

  Default: 'PicoLab' + board_num(), e.g. 'PicoLab742'. Same forever, no
  file needed. To give a board a real name, write it into name.txt on
  the board (Viper file panel): 'Bin-P3-4' becomes its name everywhere."""
  try:
    with open(NAME_FILE) as f:
      custom = f.read().strip()
      if custom:
        return custom
  except Exception:
    pass
  return "PicoLab" + str(board_num())


def query_str(req, key, default=None):
  """Pull ?key=some%20text out of a raw request, urldecoded. Matches the
  whole key only (?key= or &key=), so 'label' never matches 'xlabel'."""
  try:
    text = req.decode() if isinstance(req, bytes) else req
    idx = -1
    for lead in ("?", "&"):
      try:
        idx = text.index(lead + key + "=")
        break
      except ValueError:
        pass
    if idx < 0:
      return default
    start = idx + len(key) + 2
    end = start
    while end < len(text) and text[end] not in "& \r\n":
      end += 1
    raw = text[start:end].replace("+", " ")
    out = ""
    i = 0
    while i < len(raw):
      if raw[i] == "%" and i + 2 < len(raw) + 1:
        try:
          out += chr(int(raw[i + 1:i + 3], 16))
          i += 3
          continue
        except ValueError:
          pass
      out += raw[i]
      i += 1
    return out
  except Exception:
    return default


def query_int(req, key, default=None):
  """Pull ?key=123 out of a raw request. Returns default on any trouble."""
  try:
    marker = key + "="
    text = req.decode() if isinstance(req, bytes) else req
    start = text.index(marker) + len(marker)
    end = start
    while end < len(text) and (text[end].isdigit() or text[end] == "-"):
      end += 1
    return int(text[start:end])
  except Exception:
    return default


class WebApp:
  def __init__(self, import_network=True, index="index.html"):
    import network

    # Where this app's dashboard lives. Under the EVERYTHING install a
    # project's files sit in their own folder (bme280/index.html); when
    # a project is installed alone, its index.html is at the root. We
    # try the given path first and fall back to the root copy.
    self.index = index
    # Identity: uid is the permanent hardware serial, name is the stable
    # human-friendly handle (both survive re-flashing). ssid = name.
    self.uid = board_uid()
    self.name = station_name()
    self.ssid = self.name
    self.ip = "192.168.4.1"
    self.ap = None
    self.joined = None
    self.rescue_target = None

    # Mission-control mode: if wifi.json exists on the board
    # ({"ssid": "WormHole", "password": "supersecret"}), JOIN that
    # network so every station lives on one router and an aggregator
    # can find them all. No file, the file is bad, or the join fails
    # after retries: open our own AP, so a board is ALWAYS reachable
    # one way or the other. Delete wifi.json to force AP mode.
    creds = None
    try:
      with open("wifi.json") as f:
        creds = json.load(f)
    except Exception:
      pass
    if creds and creds.get("ssid"):
      try:
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        password = creds.get("password", "")

        # The join ladder, highest priority first. rescue nets share the
        # password and let a teacher intervene: bring up "wormmaster<X>"
        # (X = this board's 4-hex tag) and ONLY this board hops over;
        # bring up plain "wormmaster" (a phone hotspot) and EVERY board
        # hops over. Neither present: join the real classroom network.
        rescue = creds.get("rescue", "wormmaster")
        tag = str(board_num())
        ladder = []
        if rescue:
          ladder.append(rescue + tag)   # 1: just me
          ladder.append(rescue)         # 2: all boards (phone hotspot)
        ladder.append(creds["ssid"])    # 3: the real network
        self.rescue_target = (rescue + tag) if rescue else None

        # Scan so we only dial networks that actually exist (blind-
        # dialing dead SSIDs would waste ~30 s each before the fallback).
        present = None
        try:
          seen = set(s[0].decode() for s in sta.scan() if s[0])
          present = [n for n in ladder if n in seen]
        except Exception:
          present = ladder      # scan failed: just try them all in order

        for name in present:
          if _try_join(sta, name, password):
            self.joined = name
            self.ip = sta.ifconfig()[0]
            log("Joined", name, "as", self.ip, "- browse http://" + self.ip)
            break
          log("could not join", name, "- next in the ladder...")
        if not self.joined:
          log("no network joined - opening own AP instead.")
          sta.active(False)
      except Exception as e:
        log("Wi-Fi join errored (" + str(e) + ") - opening own AP instead.")

    if not self.joined:
      self.ap = network.WLAN(network.AP_IF)
      self.ap.active(True)
      self.ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
      self.ap.config(essid=self.ssid, security=0)
      while not self.ap.active():
        time.sleep(0.1)
      self.ip = "192.168.4.1"

    self.server = None
    self._init_server()

  def _init_server(self):
    # Re-running a program (Viper: Stop then Run) can leave the OLD web
    # socket still holding port 80 for a few seconds. So retry with a
    # growing wait, freeing memory each time. And if it truly will not
    # bind, DO NOT crash: the station keeps running with its screen,
    # sensors, and light -- only the web page is missing. A dead screen
    # is never worth an unbindable port.
    import gc
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    for attempt in range(6):
      try:
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(addr)
        self.server.listen(2)
        self.server.settimeout(0.05)
        return
      except OSError as e:
        try:
          self.server.close()
        except Exception:
          pass
        self.server = None
        if e.errno != 98:      # not "address in use": a real problem
          log("Web server error:", e, "- station runs without the web page.")
          return
        gc.collect()
        if self.ap:
          log("Port 80 busy, recycling Wi-Fi (try %d)..." % (attempt + 1))
          try:
            self.ap.active(False)
            time.sleep(0.5)
            self.ap.active(True)
            self.ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
            self.ap.config(essid=self.ssid, security=0)
          except Exception:
            pass
        else:
          log("Port 80 busy, waiting for the old socket to free (try %d)..." % (attempt + 1))
        time.sleep(1 + attempt)   # 1, 2, 3, 4, 5 s
    log("Port 80 stayed busy - station is running WITHOUT the web page")
    log("(the screen and sensors work; do a full reset to get the web page back).")
    self.server = None

  def locate(self):
    """The number that finds this board when it has no screen: the last
    octet of its IP when joined (browse to it), or its PicoLab number
    when hosting its own AP (join that SSID). StatusLight blinks it."""
    if self.joined:
      try:
        return int(self.ip.rsplit(".", 1)[-1])
      except Exception:
        return 0
    return board_num()

  def identity(self):
    """Who this board is, for the dashboard and the wall to label by."""
    return {
        "id": self.uid,                       # permanent hardware serial
        "name": self.name,                    # stable friendly name
        "ip": self.ip,                        # where to browse right now
        "ssid": self.ssid,
        "mode": "joined" if self.joined else "ap",
        "net": self.joined or self.ssid,
    }

  def announce(self, title):
    if self.joined:
      lines = [
          "Name:   " + self.name,
          "Board:  " + self.uid,
          "On:     " + self.joined,
          "Browse: http://" + self.ip,
      ]
      if self.rescue_target:
        lines.append("Rescue: " + self.rescue_target)
      banner(title, lines)
    else:
      lines = [
          "Name:   " + self.name,
          "Board:  " + self.uid,
          "Wi-Fi:  join '" + self.ssid + "'",
          "Browse: http://192.168.4.1",
      ]
      if self.rescue_target:
        lines.append("Rescue net: " + self.rescue_target)
      banner(title, lines)

  def poll(self, data_fn, routes=None):
    """Serve one pending request, if any. Never raises.

    data_fn() -> dict, served as JSON at /data.
    routes: optional list of (prefix, handler); handler(req) -> dict,
    also served as JSON. Use for actions like /set?angle=90.
    """
    if not self.server:      # port 80 never opened; run without the web page
      return
    try:
      cl, _ = self.server.accept()
    except OSError:
      return
    try:
      cl.settimeout(0.5)
      req = b""
      try:
        req = cl.recv(512)
      except Exception:
        pass

      handled = False
      if routes:
        for prefix, handler in routes:
          if prefix.encode() in req:
            try:
              payload = json.dumps(handler(req)).encode("utf-8")
            except Exception as e:
              payload = json.dumps({"error": str(e)}).encode("utf-8")
            cl.sendall(HEADER_JSON + payload)
            handled = True
            break

      if not handled and b"/data" in req:
        try:
          data = data_fn()
          # Every station reports its identity for free, so the wall
          # and any kid can tell boards apart and know where to browse.
          ident = self.identity()
          for k in ident:
            if k not in data:
              data[k] = ident[k]
          payload = json.dumps(data).encode("utf-8")
        except Exception as e:
          payload = json.dumps({"error": str(e)}).encode("utf-8")
        cl.sendall(HEADER_JSON + payload)
        handled = True

      if not handled:
        # Serve a real static file if the request names one (e.g.
        # /cal.js, the shared calibration widget). Anything else falls
        # back to the dashboard page.
        path = _req_path(req)
        static = None
        if path and path != "/" and "." in path and ".." not in path:
          static = path.lstrip("/")
        if static:
          try:
            with open(static, "rb") as f:
              cl.sendall(_static_header(static))
              while True:
                chunk = f.read(512)
                if not chunk:
                  break
                cl.sendall(chunk)
            cl.close()
            return
          except Exception:
            # The request named a real file (e.g. /cal.js) that isn't on
            # the board. Answer with an honest 404, NOT the dashboard
            # HTML: a <script src> or <link> that receives HTML fails in
            # confusing ways (undefined globals) instead of failing clean.
            try:
              cl.sendall(b"HTTP/1.0 404 Not Found\r\nConnection: close\r\n\r\nnot found")
              cl.close()
            except Exception:
              pass
            return
        cl.sendall(HEADER_HTML)
        served = False
        for page in (self.index, "index.html"):
          try:
            with open(page, "rb") as f:
              while True:
                chunk = f.read(512)
                if not chunk:
                  break
                cl.sendall(chunk)
            served = True
            break
          except Exception:
            continue
        if not served:
          cl.sendall(b"<h1>404: File Not Found</h1>")
      cl.close()
    except Exception:
      try:
        cl.close()
      except Exception:
        pass
