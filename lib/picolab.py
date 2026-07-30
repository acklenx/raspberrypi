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
#   * Web demos open an access point named PicoLab<N> (N is picked once
#     per board and remembered in node_id.txt), serve index.html at
#     http://192.168.4.1 and JSON at /data.

import json
import random
import socket
import time
from machine import I2C, Pin

_i2c = None


def i2c():
  """The shared I2C0 bus: SDA=GP0, SCL=GP1, 400kHz."""
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

  If code is running, the light is doing something. If a part is in
  trouble, the light says so. Two modes:

    set_ok(bool)    Simplest demos: solid ON means working, OFF means not.
    set_slots(list) POST blinks: one blink per entry, in a fixed order,
                    then a pause, then repeat. Short blink = that part is
                    OK. Long blink = that part is in trouble. So with five
                    probes, ". . . _ ." means probe 4 has a problem. No
                    blinking at all means the code is not running.

  Call poll() every trip through the main loop (50 ms or faster keeps the
  blinks crisp). Changes from set_slots() take effect at the next cycle.
  """

  SHORT_MS = 100
  LONG_MS = 600
  GAP_MS = 250
  PAUSE_MS = 1400

  def __init__(self):
    try:
      self.led = Pin("LED", Pin.OUT)
      self.led.off()
    except Exception:
      self.led = None
    self._solid = None
    self._slots = [True]
    self._cycle = None
    self._i = 0
    self._lit = False
    self._until = time.ticks_ms()

  def set_ok(self, ok):
    self._solid = bool(ok)

  def set_slots(self, slots):
    self._solid = None
    self._slots = [bool(s) for s in slots] or [False]

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
      self._i += 1
      if self._cycle is None or self._i >= len(self._cycle):
        self._cycle = None
        self._until = time.ticks_add(now, self.PAUSE_MS)
      else:
        self._until = time.ticks_add(now, self.GAP_MS)
    else:
      if self._cycle is None:
        self._cycle = self._slots[:]
        self._i = 0
      self.led.on()
      self._lit = True
      self._until = time.ticks_add(
          now, self.SHORT_MS if self._cycle[self._i] else self.LONG_MS)


class Display:
  """SSD1306 wrapper that never raises. Retries the display every 3 s."""

  def __init__(self, addr=0x3C):
    self.addr = addr
    self.oled = None
    self._retry = Throttle(3000)
    self._was_ok = False

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
# Web app: access point + tiny webserver (the pattern from the ToF
# distance station: static-ish SSID per board, minimal collisions).
# ---------------------------------------------------------------------
NODE_ID_FILE = "node_id.txt"
BANNED_IDS = set(range(1, 10)).union({67, 158})

HEADER_HTML = b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n"
HEADER_JSON = b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n"


def node_id():
  try:
    with open(NODE_ID_FILE, "r") as f:
      val = int(f.read().strip())
      if val not in BANNED_IDS:
        return val
  except Exception:
    pass
  val = random.choice(list(set(range(10, 254)) - BANNED_IDS))
  try:
    with open(NODE_ID_FILE, "w") as f:
      f.write(str(val))
  except Exception:
    pass
  return val


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
    self.ssid = "PicoLab" + str(node_id())

    self.ap = network.WLAN(network.AP_IF)
    self.ap.active(True)
    self.ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
    self.ap.config(essid=self.ssid, security=0)
    while not self.ap.active():
      time.sleep(0.1)

    self.server = None
    self._init_server()

  def _init_server(self):
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    self.server = socket.socket()
    self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
      self.server.bind(addr)
    except OSError as e:
      if e.errno == 98:
        log("Port 80 busy! Recycling Wi-Fi stack...")
        self.ap.active(False)
        time.sleep(0.5)
        self.ap.active(True)
        self.ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
        self.server.close()
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(addr)
      else:
        raise
    self.server.listen(2)
    self.server.settimeout(0.05)

  def announce(self, title):
    banner(title, [
        "SSID:       " + self.ssid,
        "Dashboard:  http://192.168.4.1",
    ])

  def poll(self, data_fn, routes=None):
    """Serve one pending request, if any. Never raises.

    data_fn() -> dict, served as JSON at /data.
    routes: optional list of (prefix, handler); handler(req) -> dict,
    also served as JSON. Use for actions like /set?angle=90.
    """
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
          payload = json.dumps(data_fn()).encode("utf-8")
        except Exception as e:
          payload = json.dumps({"error": str(e)}).encode("utf-8")
        cl.sendall(HEADER_JSON + payload)
        handled = True

      if not handled:
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
