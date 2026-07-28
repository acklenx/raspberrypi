# GL5528 LDR bench demo: basic light level on the OLED and terminal.
# No Wi-Fi. Fault tolerant: runs with the display missing and picks it
# up the moment it is plugged in. No restarts needed.
#
# Wiring: LDR from 3V3 to GP28, 10k resistor from GP28 to GND.
# More light = lower LDR resistance = higher voltage on GP28.
# Note: an ADC pin cannot tell if the divider is unplugged; a floating
# pin just reads electrical noise.
#
# On the board: this file (as main.py or run it from the IDE),
# lib/picolab.py, lib/ssd1306.py.

import gc
import time

import picolab

picolab.banner("GL5528 Light Bench Demo", [
    "Wiring: LDR 3V3 to GP28,",
    "10k GP28 to GND (ADC2)",
    "OLED optional at 0x3C",
])


def connect():
  from machine import ADC
  return ADC(28)


def read(dev):
  total = 0
  for _ in range(16):
    total += dev.read_u16()
  raw = total // 16
  return {
      "raw": raw,
      "light_pct": round(raw / 65535 * 100, 1),
  }


sensor = picolab.Sensor("GL5528", connect, read)
display = picolab.Display()
heartbeat = picolab.Throttle(5000)

while True:
  data = sensor.poll()

  if data:
    display.show([
        "LDR  light",
        "Light: %5.1f %%" % data["light_pct"],
        "Raw:   %5d" % data["raw"],
    ], bar=data["light_pct"] / 100)
  else:
    display.show([
        "LDR  light",
        "starting...",
    ])

  if heartbeat.ready():
    picolab.log("GL5528", data)

  time.sleep_ms(200)
  gc.collect()
