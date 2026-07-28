# Capacitive soil moisture web demo: moisture percent on the OLED, the
# terminal, and a live web dashboard.
#
# The Pico opens a Wi-Fi network named PicoLab-<N>. Join it and browse
# to http://192.168.4.1 (JSON at /data).
#
# NOTE: an analog pin cannot tell if the sensor is unplugged. With
# nothing on GP26 the pin floats and the numbers are noise. The I2C
# demos can detect a missing part; analog demos cannot.
#
# Wiring: VCC=3V3, GND=GND, AOUT=GP26 (ADC0).
# On the board: main.py, index.html, lib/picolab.py, lib/ssd1306.py.

import gc

from machine import ADC

import picolab

# Calibration (typical values at 3V3). To calibrate YOUR sensor:
# watch the raw value with the probe dry in air (that is DRY_RAW),
# then in a cup of water up to the marked line (that is WET_RAW),
# and edit these two numbers.
DRY_RAW = 44000
WET_RAW = 18000

sensor = None


def connect():
  return ADC(26)


def read(dev):
  total = 0
  for _ in range(16):
    total += dev.read_u16()
  raw = total // 16
  pct = (DRY_RAW - raw) * 100.0 / (DRY_RAW - WET_RAW)
  pct = max(0.0, min(100.0, pct))
  return {"moisture_pct": round(pct, 1), "raw": raw}


def data_fn():
  d = {"ok": sensor.ok, "ssid": app.ssid}
  if sensor.data:
    d.update(sensor.data)
  return d


sensor = picolab.Sensor("Soil moisture", connect, read)
display = picolab.Display()
app = picolab.WebApp()
heartbeat = picolab.Throttle(5000)

app.announce("Soil Moisture Station Active!")

while True:
  data = sensor.poll()

  if data:
    display.show([
        app.ssid,
        "Soil: %5.1f %%" % data["moisture_pct"],
        "raw: %5d" % data["raw"],
    ], bar=data["moisture_pct"] / 100.0)
  else:
    display.show([
        app.ssid,
        "192.168.4.1",
        "starting...",
    ])

  if heartbeat.ready():
    picolab.log("Soil", data)

  app.poll(data_fn)
  gc.collect()
