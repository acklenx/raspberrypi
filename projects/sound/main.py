# MAX9814 web demo: sound level meter on the OLED, the terminal, and a
# live web dashboard. Clap and watch the bars jump.
#
# The Pico opens a Wi-Fi network named PicoLab<N>. Join it and browse
# to http://192.168.4.1 (JSON at /data).
#
# The MAX9814 outputs audio centered around ~1.25V. Loudness is the size
# of the wiggle, not the average, so each reading samples the ADC flat
# out for 25ms and takes max minus min.
#
# Wiring: VDD=3V3, GND=GND, OUT=GP27 (ADC1). GAIN floating = 60dB.
# Note: an ADC pin cannot tell if the mic is unplugged, so here the
# truth light (the onboard LED, short blink every cycle) mostly proves
# the CODE is running; no blinking at all means it is not.
#
# On the board: main.py, index.html, lib/picolab.py, lib/ssd1306.py.

import gc
import time

import picolab

sensor = None
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


def data_fn():
  d = {"ok": sensor.ok, "ssid": app.ssid}
  if sensor.data:
    d.update(sensor.data)
  return d


sensor = picolab.Sensor("MAX9814", connect, read)
display = picolab.Display()
light = picolab.StatusLight()
app = picolab.WebApp()
tick = picolab.Throttle(100)  # fast: keeps the level meter lively
heartbeat = picolab.Throttle(5000)

app.announce("MAX9814 Sound Station Active!")

while True:
  light.poll()
  app.poll(data_fn)
  if not tick.ready():
    continue

  data = sensor.poll()
  light.set_slots([sensor.ok])

  if data:
    display.show([
        app.ssid,
        "Level: %5.1f %%" % data["level_pct"],
        "Peak:  %5.1f %%" % data["peak_pct"],
    ], bar=data["level_pct"] / 100)
  else:
    display.show([
        app.ssid,
        "192.168.4.1",
        "starting...",
    ])

  if heartbeat.ready():
    picolab.log("MAX9814", data)

  gc.collect()
