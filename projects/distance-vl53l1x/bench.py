# VL53L1X long-range distance bench demo: up to ~4 meters on the OLED
# and terminal. No Wi-Fi. This is the big sibling of the VL53L0X; same
# idea, four times the reach.
#
# Fault tolerant: runs with the sensor missing, the display missing, or
# both, and picks either up the moment it is plugged in. No restarts.
#
# Wiring (shared I2C bus): VIN=3V3, GND=GND, SDA=GP0, SCL=GP1.
# NOTE: the VL53L1X uses I2C address 0x29, the SAME address as the
# VL53L0X. Only one of the two can be on the bus at a time.
#
# On the board: this file, lib/picolab.py, lib/vl53l1x.py,
# lib/ssd1306.py.

import gc
import time

import picolab

picolab.banner("VL53L1X Bench Demo", [
    "Wiring: I2C0 SDA=GP0 SCL=GP1",
    "VL53L1X at 0x29 (not with a VL53L0X!)",
    "OLED at 0x3C, both optional",
])


def connect():
  from vl53l1x import VL53L1X
  return VL53L1X(picolab.i2c())


def read(dev):
  mm, valid = dev.read()
  return {
      "dist_mm": mm if valid else None,
      "valid": valid,
  }


sensor = picolab.Sensor("VL53L1X", connect, read)
display = picolab.Display()
heartbeat = picolab.Throttle(5000)

while True:
  data = sensor.poll()

  if data and data["valid"]:
    display.show([
        "VL53L1X  live",
        "%4d mm" % data["dist_mm"],
        "%5.2f m" % (data["dist_mm"] / 1000.0),
    ], bar=min(1.0, data["dist_mm"] / 4000.0))
  elif data:
    display.show([
        "VL53L1X  live",
        "no target...",
        "(0.04 - 4 m)",
    ])
  else:
    display.show([
        "VL53L1X",
        "no sensor...",
        "check SDA=GP0",
        "      SCL=GP1",
    ])

  if heartbeat.ready():
    picolab.log("VL53L1X" if sensor.ok else "VL53L1X (unplugged)", data)

  time.sleep_ms(200)
  gc.collect()
