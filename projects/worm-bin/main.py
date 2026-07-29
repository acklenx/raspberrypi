# WORM BIN COMMAND CENTER: every sensor in the toolbox, and the
# actuators, running off ONE Pico at the same time.
#
#   2x BME280 (0x76 inside the bin, 0x77 outside)
#   DS18B20 waterproof probes on GP22 (as many as you own, one wire)
#   ADS1115 analog bank at 0x48: A0 + A1 soil moisture, A2 light divider
#   MAX9814 mic on GP27 (native ADC: it needs the fast sampling)
#   VL53L0X distance at 0x29 (lid-open / harvest-level detector)
#   Big servo GP16, small servo GP17, relay GP15
#   OLED 0x3C, rotating status pages
#
# The Pico opens a Wi-Fi network named PicoLab<N>. Join it and browse
# to http://192.168.4.1 (JSON at /data, actuators at /set).
#
# Everything is optional and hot-pluggable. The truth light runs POST
# codes, one blink per part IN THE ORDER OF THE PARTS LIST BELOW, then
# one slot per DS18B20 probe (always last, so adding a probe grows the
# tail of the pattern without renumbering anything). Short blink = OK,
# long blink = trouble, dark = code not running. Comment out the line of
# any part your bin does not have and its slot disappears.
#
# On the board: main.py, index.html, and from lib/: picolab.py,
# ssd1306.py, bme280.py, ads1115.py, vl53l0x.py.

import gc
import time

from machine import ADC, PWM, Pin

import picolab

# Moisture calibration in VOLTS (ADS1115 reads volts, not Pico counts).
# Calibrate: watch volts with the probe dry in air (DRY), then in a cup
# of water up to the marked line (WET), and edit these two numbers.
MOIST_DRY_V = 2.22
MOIST_WET_V = 0.91


def bme(name, addr):
  def connect():
    from bme280 import BME280
    return BME280(picolab.i2c(), address=addr)

  def read(dev):
    temp_c, press_hpa, hum_pct = dev.read()
    return {
        name + "_temp_c": round(temp_c, 1),
        name + "_press_hpa": round(press_hpa, 1),
        name + "_hum_pct": None if hum_pct is None else round(hum_pct, 1),
    }

  return picolab.Sensor("BME280 %s (0x%02x)" % (name, addr), connect, read)


def analog_bank():
  """ADS1115: two moisture probes and the light divider, one part."""

  def connect():
    from ads1115 import ADS1115
    return ADS1115(picolab.i2c())

  def moisture_pct(v):
    pct = (MOIST_DRY_V - v) * 100.0 / (MOIST_DRY_V - MOIST_WET_V)
    return round(max(0.0, min(100.0, pct)), 1)

  def read(dev):
    m1 = dev.read_volts(0)
    m2 = dev.read_volts(1)
    lv = dev.read_volts(2)
    return {
        "moist1_pct": moisture_pct(m1), "moist1_v": round(m1, 2),
        "moist2_pct": moisture_pct(m2), "moist2_v": round(m2, 2),
        "light_pct": round(max(0.0, min(100.0, lv / 3.3 * 100)), 1),
    }

  return picolab.Sensor("ADS1115 bank (0x48)", connect, read)


def microphone():
  """MAX9814 on GP27. An ADC pin cannot detect an unplugged mic, so
  this slot mostly proves the code is sampling."""

  def connect():
    return ADC(27)

  def read(dev):
    lo, hi = 65535, 0
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < 25:
      v = dev.read_u16()
      if v < lo:
        lo = v
      if v > hi:
        hi = v
    return {"sound_pct": round((hi - lo) / 65535 * 100, 1)}

  return picolab.Sensor("MAX9814 mic (GP27)", connect, read)


def distance():
  def connect():
    from vl53l0x import VL53L0X
    tof = VL53L0X(picolab.i2c())
    tof.init_sensor()
    return tof

  def read(dev):
    return {"dist_mm": dev.ping()}

  return picolab.Sensor("VL53L0X (0x29)", connect, read)


def probe_bus():
  """DS18B20 array on GP22, same live-rescan engine as soil-temperature:
  one bad probe faults alone, added probes appear by themselves."""

  def connect():
    import onewire
    import ds18x20

    ds = ds18x20.DS18X20(onewire.OneWire(Pin(22)))
    roms = ds.scan()
    if not roms:
      raise OSError("no DS18B20 found on GP22")
    ds.convert_temp()
    time.sleep_ms(750)
    return {"ds": ds, "roms": roms, "due": time.ticks_ms(), "temps": None}

  def read(dev):
    now = time.ticks_ms()
    if time.ticks_diff(now, dev["due"]) >= 0:
      temps = []
      for rom in dev["roms"]:
        try:
          temps.append(round(dev["ds"].read_temp(rom), 1))
        except Exception:
          temps.append(None)
      if dev["roms"] and all(t is None for t in temps):
        raise OSError("all probes lost")
      try:
        roms = dev["ds"].scan()
        if roms:
          dev["roms"] = roms
      except Exception:
        pass
      dev["ds"].convert_temp()
      dev["due"] = time.ticks_add(now, 750)
      dev["temps"] = temps
    temps = dev["temps"] or []
    good = [t for t in temps if t is not None]
    return {
        "probes": len(temps),
        "probe_count": len(good),
        "probe_ok": [t is not None for t in temps],
        "probe_temps_c": temps,
    }

  return picolab.Sensor("DS18B20 bus (GP22)", connect, read)


# ---------------------------------------------------------------------
# THE PARTS LIST. Slot order on the truth light = this order, then one
# slot per DS18B20 probe. Comment out what your bin does not have.
# ---------------------------------------------------------------------
PARTS = [
    bme("in", 0x76),
    bme("out", 0x77),
    analog_bank(),
    microphone(),
    distance(),
]
DS = probe_bus()   # dynamic slots, always last


# ---- actuators ------------------------------------------------------
class Servo:
  def __init__(self, pin_num, min_us=600, max_us=2400):
    self.pwm = PWM(Pin(pin_num))
    self.pwm.freq(50)
    self.angle = 90.0
    self.min_us = min_us
    self.max_us = max_us
    self.write(self.angle)

  def write(self, angle):
    self.angle = max(0.0, min(180.0, float(angle)))
    us = self.min_us + (self.angle / 180.0) * (self.max_us - self.min_us)
    self.pwm.duty_u16(int(us * 65535 / 20000))


servo_big = Servo(16)     # MG995: its own 5V supply, grounds joined!
servo_small = Servo(17)   # SG90: VBUS is fine
relay = Pin(15, Pin.OUT)
relay.value(0)


def set_handler(req):
  a = picolab.query_int(req, "big")
  if a is not None:
    servo_big.write(a)
    picolab.log("Web: big servo ->", int(servo_big.angle))
  a = picolab.query_int(req, "small")
  if a is not None:
    servo_small.write(a)
    picolab.log("Web: small servo ->", int(servo_small.angle))
  a = picolab.query_int(req, "relay")
  if a is not None:
    relay.value(1 if a else 0)
    picolab.log("Web: relay ->", relay.value())
  return {"big": int(servo_big.angle), "small": int(servo_small.angle),
          "relay": relay.value()}


def data_fn():
  d = {"ok": True, "ssid": app.ssid}
  status = []
  for s in PARTS:
    status.append({"name": s.name, "ok": s.ok})
    if s.data:
      d.update(s.data)
  status.append({"name": DS.name, "ok": DS.ok})
  if DS.data:
    d.update(DS.data)
  d["parts"] = status
  d["big"] = int(servo_big.angle)
  d["small"] = int(servo_small.angle)
  d["relay"] = relay.value()
  return d


# ---- OLED pages -----------------------------------------------------
def fmt(val, pattern="%s"):
  return "--" if val is None else pattern % val


def page_lines(page, d):
  if page == 0:
    dt = None
    if d.get("in_temp_c") is not None and d.get("out_temp_c") is not None:
      dt = d["in_temp_c"] - d["out_temp_c"]
    return [
        "AIR   in / out",
        "T %s / %s" % (fmt(d.get("in_temp_c"), "%.1f"), fmt(d.get("out_temp_c"), "%.1f")),
        "H %s / %s" % (fmt(d.get("in_hum_pct"), "%.0f%%"), fmt(d.get("out_hum_pct"), "%.0f%%")),
        "dT %s" % fmt(dt, "%+.1f C"),
    ]
  if page == 1:
    lines = ["PROBES %s/%s" % (d.get("probe_count", 0), d.get("probes", 0))]
    for idx, t in enumerate((d.get("probe_temps_c") or [])[:3]):
      lines.append("%d: %s" % (idx + 1, "fault!" if t is None else "%5.1f C" % t))
    return lines
  if page == 2:
    return [
        "SOIL + LIGHT",
        "M1 %s" % fmt(d.get("moist1_pct"), "%.0f%%"),
        "M2 %s" % fmt(d.get("moist2_pct"), "%.0f%%"),
        "Lt %s  Snd %s" % (fmt(d.get("light_pct"), "%.0f%%"),
                           fmt(d.get("sound_pct"), "%.0f%%")),
    ]
  return [
      "ACT + DIST",
      "dist %s" % fmt(d.get("dist_mm"), "%d mm"),
      "servo %d / %d" % (int(servo_big.angle), int(servo_small.angle)),
      "relay %s" % ("ON" if relay.value() else "off"),
  ]


picolab.banner("WORM BIN COMMAND CENTER", [
    "Parts: " + ", ".join(s.name for s in PARTS),
    "Plus: " + DS.name + " (slots at the end)",
    "LED POST: short=OK long=trouble",
])

display = picolab.Display()
light = picolab.StatusLight()
app = picolab.WebApp()
tick = picolab.Throttle(500)
heartbeat = picolab.Throttle(5000)

app.announce("Worm Bin Command Center Active!")

while True:
  light.poll()
  app.poll(data_fn, routes=[("/set", set_handler)])
  if not tick.ready():
    continue

  for s in PARTS:
    s.poll()
  DS.poll()

  slots = [s.ok for s in PARTS]
  dsd = DS.data
  if dsd and dsd.get("probes"):
    slots.extend(dsd["probe_ok"])
  else:
    slots.append(DS.ok)
  light.set_slots(slots)

  d = data_fn()
  page = (time.ticks_ms() // 3000) % 4
  lines = [app.ssid + " p%d/4" % (page + 1)] + page_lines(page, d)
  display.show(lines[:5])

  if heartbeat.ready():
    bad = [s.name for s in PARTS if not s.ok] + ([] if DS.ok else [DS.name])
    picolab.log("all parts OK" if not bad else "TROUBLE: " + ", ".join(bad))

  gc.collect()
