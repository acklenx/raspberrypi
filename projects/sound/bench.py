# MAX9814 bench demo: sound level meter on the OLED and terminal.
# No Wi-Fi. Fault tolerant: runs with the display missing and picks it
# up the moment it is plugged in. No restarts needed.
#
# The MAX9814 outputs audio centered around ~1.25V. Loudness is the size
# of the wiggle, not the average, so each reading samples the ADC flat
# out for 25ms and takes max minus min.
#
# Wiring: VDD=3V3, GND=GND, OUT=GP27 (ADC1). GAIN floating = 60dB.
# Note: an ADC pin cannot tell if the mic is unplugged; a floating pin
# just reads electrical noise.
#
# On the board: this file (as main.py or run it from the IDE),
# lib/picolab.py, lib/ssd1306.py.

import gc
import time

import picolab

picolab.banner("MAX9814 Sound Bench Demo", [
    "Wiring: VDD=3V3 GND=GND OUT=GP27",
    "GAIN floating = 60dB (fine)",
    "OLED optional at 0x3C",
])

peak = [0.0]


def connect():
  from machine import ADC
  return ADC(27)


def read(dev):
  lo = 65535
  hi = 0
  start = time.ticks_ms()
  while time.ticks_diff(time.ticks_ms(), start) < 25:
    v = dev.read_u16()
    if v < lo:
      lo = v
    if v > hi:
      hi = v
  level = hi - lo if hi > lo else 0
  level_pct = round(level / 65535 * 100, 1)
  peak[0] = max(peak[0] * 0.95, level_pct)
  return {
      "level_pct": level_pct,
      "peak_pct": round(peak[0], 1),
  }


sensor = picolab.Sensor("MAX9814", connect, read)
display = picolab.Display()
heartbeat = picolab.Throttle(5000)

while True:
  data = sensor.poll()

  if data:
    display.show([
        "MAX9814  sound",
        "Level: %5.1f %%" % data["level_pct"],
        "Peak:  %5.1f %%" % data["peak_pct"],
    ], bar=data["level_pct"] / 100)
  else:
    display.show([
        "MAX9814  sound",
        "starting...",
    ])

  if heartbeat.ready():
    picolab.log("MAX9814", data)

  time.sleep_ms(200)
  gc.collect()
