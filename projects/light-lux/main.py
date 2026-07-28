# BH1750 web demo: light level in real lux on the OLED, the terminal,
# and a live web dashboard.
#
# The Pico opens a Wi-Fi network named PicoLab-<N>. Join it and browse
# to http://192.168.4.1 (JSON at /data).
#
# Fault tolerant: runs with the sensor missing, the display missing, or
# both, and picks either up the moment it is plugged in. No restarts.
#
# On the board: main.py, index.html, lib/picolab.py, lib/bh1750.py,
# lib/ssd1306.py.

import gc

import picolab

sensor = None


def connect():
  from bh1750 import BH1750
  return BH1750(picolab.i2c())


def read(dev):
  return {"lux": round(dev.read(), 1)}


def data_fn():
  d = {"ok": sensor.ok, "ssid": app.ssid}
  if sensor.data:
    d.update(sensor.data)
  return d


sensor = picolab.Sensor("BH1750", connect, read)
display = picolab.Display()
app = picolab.WebApp()
heartbeat = picolab.Throttle(5000)

app.announce("BH1750 Lux Station Active!")

while True:
  data = sensor.poll()

  if data:
    display.show([
        app.ssid,
        "Lux: %7.1f" % data["lux"],
    ], bar=min(1.0, data["lux"] / 1000))
  else:
    display.show([
        app.ssid,
        "192.168.4.1",
        "no sensor...",
        "hot-plug ready",
    ])

  if heartbeat.ready():
    picolab.log("BH1750" if sensor.ok else "BH1750 (unplugged)", data)

  app.poll(data_fn)
  gc.collect()
