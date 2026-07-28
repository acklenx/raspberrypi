# Capacitive soil moisture bench demo: moisture percent on the OLED and
# terminal. No Wi-Fi. Fault tolerant: runs with the display missing and
# picks it up the moment it is plugged in. No restarts needed.
#
# NOTE: an analog pin cannot tell if the sensor is unplugged. With
# nothing on GP26 the pin floats and the numbers are noise. The I2C
# demos can detect a missing part; analog demos cannot.
#
# Wiring: VCC=3V3, GND=GND, AOUT=GP26 (ADC0).
# On the board: this file (as main.py or run it from the IDE),
# lib/picolab.py, lib/ssd1306.py.

import gc
import time

from machine import ADC

import picolab

# Calibration (typical values at 3V3). To calibrate YOUR sensor:
# watch the raw value with the probe dry in air (that is DRY_RAW),
# then in a cup of water up to the marked line (that is WET_RAW),
# and edit these two numbers.
DRY_RAW = 44000
WET_RAW = 18000

picolab.banner("Soil Moisture Bench Demo", [
    "Wiring: AOUT=GP26 (ADC0), VCC=3V3, GND",
    "Capacitive sensor v1.2, OLED at 0x3C",
    "Analog pin: no unplug detection",
])


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


sensor = picolab.Sensor("Soil moisture", connect, read)
display = picolab.Display()
heartbeat = picolab.Throttle(5000)

while True:
  data = sensor.poll()

  if data:
    display.show([
        "Soil Moisture",
        "Soil: %5.1f %%" % data["moisture_pct"],
        "raw: %5d" % data["raw"],
    ], bar=data["moisture_pct"] / 100.0)
  else:
    display.show([
        "Soil Moisture",
        "starting...",
    ])

  if heartbeat.ready():
    picolab.log("Soil", data)

  time.sleep_ms(200)
  gc.collect()
