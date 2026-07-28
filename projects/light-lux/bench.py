# BH1750 bench demo: light level in real lux on the OLED and terminal.
# No Wi-Fi. Fault tolerant: runs with the sensor missing, the display
# missing, or both, and picks either up the moment it is plugged in.
# No restarts needed.
#
# Wiring (shared I2C bus): SDA=GP0, SCL=GP1, 3V3, GND.
# On the board: this file (as main.py or run it from the IDE),
# lib/picolab.py, lib/bh1750.py, lib/ssd1306.py.

import gc
import time

import picolab

picolab.banner("BH1750 Lux Bench Demo", [
    "Wiring: I2C0 SDA=GP0 SCL=GP1",
    "BH1750 at 0x23, OLED at 0x3C",
    "Both parts optional + hot-pluggable",
])


def connect():
  from bh1750 import BH1750
  return BH1750(picolab.i2c())


def read(dev):
  return {"lux": round(dev.read(), 1)}


sensor = picolab.Sensor("BH1750", connect, read)
display = picolab.Display()
heartbeat = picolab.Throttle(5000)

while True:
  data = sensor.poll()

  if data:
    display.show([
        "BH1750  live",
        "Lux: %7.1f" % data["lux"],
    ], bar=min(1.0, data["lux"] / 1000))
  else:
    display.show([
        "BH1750",
        "no sensor...",
        "check SDA=GP0",
        "      SCL=GP1",
    ])

  if heartbeat.ready():
    picolab.log("BH1750" if sensor.ok else "BH1750 (unplugged)", data)

  time.sleep_ms(200)
  gc.collect()
