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
# just reads electrical noise. So here the truth light (the onboard LED,
# short blink every cycle) mostly proves the CODE is running; no
# blinking at all means it is not.
#
# On the board: this file (as main.py or run it from the IDE),
# lib/picolab.py, lib/ssd1306.py.

import gc
import time

import picolab

# ===== CONFIG =====
# MIC_PIN: the MAX9814 OUT pin; must be a native ADC pin (default GP27).
# SAMPLE_MS: how long each loudness reading listens flat-out. Longer =
#   smoother, shorter = snappier (default 25 ms).
# PEAK_FALL: how fast the peak marker decays each reading, 0..1
#   (default 0.95; closer to 1 makes the peak linger longer).
MIC_PIN = 27
SAMPLE_MS = 25
PEAK_FALL = 0.95
# ==================

picolab.banner("MAX9814 Sound Bench Demo", [
    "Wiring: VDD=3V3 GND=GND OUT=GP27",
    "GAIN floating = 60dB (fine)",
    "OLED optional at 0x3C",
])

peak = [0.0]


def connect():
  from machine import ADC
  return ADC(MIC_PIN)


def read(dev):
  lo = 65535
  hi = 0
  start = time.ticks_ms()
  while time.ticks_diff(time.ticks_ms(), start) < SAMPLE_MS:
    v = dev.read_u16()
    if v < lo:
      lo = v
    if v > hi:
      hi = v
  level = hi - lo if hi > lo else 0
  level_pct = round(level / 65535 * 100, 1)
  peak[0] = max(peak[0] * PEAK_FALL, level_pct)
  return {
      "level_pct": level_pct,
      "peak_pct": round(peak[0], 1),
  }


sensor = picolab.Sensor("MAX9814", connect, read)
display = picolab.Display()
light = picolab.StatusLight()
tick = picolab.Throttle(100)  # fast: keeps the level meter lively
heartbeat = picolab.Throttle(5000)

while True:
  if not tick.ready():
    light.poll()
    time.sleep_ms(10)
    continue

  data = sensor.poll()
  light.set_slots([sensor.ok])

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

  light.poll()
  gc.collect()
