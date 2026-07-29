# GL5528 LDR web demo: basic light level on the OLED, the terminal, and
# a live web dashboard.
#
# The Pico opens a Wi-Fi network named PicoLab<N>. Join it and browse
# to http://192.168.4.1 (JSON at /data).
#
# Wiring: LDR from 3V3 to GP28, 10k resistor from GP28 to GND.
# Note: an ADC pin cannot tell if the divider is unplugged; a floating
# pin just reads electrical noise. So here the truth light (the onboard
# LED, short blink every cycle) mostly proves the CODE is running; no
# blinking at all means it is not.
#
# On the board: main.py, index.html, lib/picolab.py, lib/ssd1306.py.

import gc

import picolab

sensor = None


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


def data_fn():
  d = {"ok": sensor.ok, "ssid": app.ssid}
  if sensor.data:
    d.update(sensor.data)
  return d


sensor = picolab.Sensor("GL5528", connect, read)
display = picolab.Display()
light = picolab.StatusLight()
app = picolab.WebApp()
tick = picolab.Throttle(250)
heartbeat = picolab.Throttle(5000)

app.announce("GL5528 Light Station Active!")

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
        "Light: %5.1f %%" % data["light_pct"],
        "Raw:   %5d" % data["raw"],
    ], bar=data["light_pct"] / 100)
  else:
    display.show([
        app.ssid,
        "192.168.4.1",
        "starting...",
    ])

  if heartbeat.ready():
    picolab.log("GL5528", data)

  gc.collect()
