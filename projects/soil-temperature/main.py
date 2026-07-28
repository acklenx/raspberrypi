# DS18B20 soil temperature web demo: waterproof probe temps on the OLED,
# the terminal, and a live web dashboard.
#
# The Pico opens a Wi-Fi network named PicoLab-<N>. Join it and browse
# to http://192.168.4.1 (JSON at /data).
#
# Fault tolerant: runs with the probes missing, the display missing, or
# both, and picks either up the moment it is plugged in. No restarts.
# Replugging rescans the wire, which also discovers newly added probes.
#
# Wiring: red=3V3, black=GND, yellow (data)=GP22, and a REQUIRED 4.7k
# ohm resistor from GP22 to 3V3 (the pullup). Several probes can share
# the same three wires; the demo reads them all.
#
# On the board: main.py, index.html, lib/picolab.py, lib/ssd1306.py.
# (onewire and ds18x20 are built into MicroPython.)

import gc
import time

from machine import Pin

import picolab

sensor = None


def connect():
  import onewire
  import ds18x20

  ow = onewire.OneWire(Pin(22))
  ds = ds18x20.DS18X20(ow)
  roms = ds.scan()
  if not roms:
    raise OSError("no DS18B20 found on GP22")
  # First conversion is blocking once, so the first reading is real.
  ds.convert_temp()
  time.sleep_ms(750)
  return {"ds": ds, "roms": roms, "due": time.ticks_ms(), "temps": None}


def read(dev):
  # DS18B20 needs 750ms between convert and read. Instead of blocking
  # the loop, read the finished conversion and start the next one.
  now = time.ticks_ms()
  if time.ticks_diff(now, dev["due"]) >= 0:
    temps = []
    for rom in dev["roms"]:
      temps.append(round(dev["ds"].read_temp(rom), 1))
    dev["ds"].convert_temp()
    dev["due"] = time.ticks_add(now, 750)
    dev["temps"] = temps
  temps = dev["temps"] or []
  return {
      "count": len(temps),
      "temps_c": temps,
      "temp_c": temps[0] if temps else None,
  }


def data_fn():
  d = {"ok": sensor.ok, "ssid": app.ssid}
  if sensor.data:
    d.update(sensor.data)
  return d


sensor = picolab.Sensor("DS18B20", connect, read)
display = picolab.Display()
app = picolab.WebApp()
heartbeat = picolab.Throttle(5000)

app.announce("Soil Temperature Station Active!")

while True:
  data = sensor.poll()

  if data and data["count"] > 0:
    lines = [app.ssid, "probes: %d" % data["count"]]
    for idx, t in enumerate(data["temps_c"][:3]):
      lines.append("%d: %5.1f C" % (idx + 1, t))
    display.show(lines)
  else:
    display.show([
        app.ssid,
        "192.168.4.1",
        "no probes...",
        "4.7k pullup?",
    ])

  if heartbeat.ready():
    picolab.log("DS18B20" if sensor.ok else "DS18B20 (unplugged)", data)

  app.poll(data_fn)
  gc.collect()
