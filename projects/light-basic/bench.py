# GL5528 LDR bench demo: basic light level on the OLED and terminal.
# No Wi-Fi. Fault tolerant: runs with the display missing and picks it
# up the moment it is plugged in. No restarts needed.
#
# Wiring: LDR from 3V3 to GP28, 10k resistor from GP28 to GND.
# More light = lower LDR resistance = higher voltage on GP28.
# Note: an ADC pin cannot tell if the divider is unplugged; a floating
# pin just reads electrical noise. So here the truth light (the onboard
# LED, short blink every cycle) mostly proves the CODE is running; no
# blinking at all means it is not.
#
# On the board: this file (as main.py or run it from the IDE),
# lib/picolab.py, lib/ssd1306.py.

import gc
import time

import picolab

# ===== CONFIG =====
# The pin reading the divider middle point (default GP28 = ADC2,
# physical pin 34). Native ADC pins only: GP26, GP27, GP28.
LDR_PIN = 28
# ==================

picolab.banner("GL5528 Light Bench Demo", [
    "Wiring: LDR 3V3 to GP28,",
    "10k GP28 to GND (ADC2)",
    "OLED optional at 0x3C",
])


def connect():
  from machine import ADC
  return ADC(LDR_PIN)


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
light = picolab.StatusLight()
tick = picolab.Throttle(250)
heartbeat = picolab.Throttle(5000)

while True:
  if not tick.ready():
    light.poll()
    time.sleep_ms(20)
    continue

  data = sensor.poll()
  light.set_slots([sensor.ok])

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

  light.poll()
  gc.collect()
