# BME280 multi-sensor demo: TWO hot-swappable BME280s on one bus, for
# example one inside the worm bin and one outside. Still just BME280s
# plus the display, but with the full grown-up treatment.
#
# A BME280 is 0x76 or 0x77 depending on its SDO pad (many boards have a
# solder jumper or an SDO pin: SDO->GND = 0x76, SDO->3V3 = 0x77). Sensor
# slot "IN" is 0x76 and slot "OUT" is 0x77 here; relabel to taste.
#
# The onboard LED runs POST codes: one blink per sensor, in order, then a
# pause. Short blink = OK, long blink = trouble. ". ." is both happy,
# "_ ." means IN (0x76) is unhappy. No blinking = code is not running.
#
# Wiring (shared I2C bus): SDA=GP0, SCL=GP1, 3V3, GND for every device.
# On the board: this file (as main.py or run from the IDE), plus from
# lib/: picolab.py, bme280.py, ssd1306.py.

import gc
import time

import picolab

STATIONS = (("IN", 0x76), ("OUT", 0x77))

picolab.banner("BME280 x%d Multi Demo" % len(STATIONS), [
    "I2C0 SDA=GP0 SCL=GP1, OLED at 0x3C",
    "Slots: " + ", ".join("%s=0x%02x" % s for s in STATIONS),
    "All parts optional + hot-pluggable",
    "LED POST: short=OK long=trouble",
])


def make_sensor(name, addr):
  def connect():
    from bme280 import BME280
    return BME280(picolab.i2c(), address=addr)

  def read(dev):
    temp_c, press_hpa, hum_pct = dev.read()
    return {
        "temp_c": round(temp_c, 1),
        "press_hpa": round(press_hpa, 1),
        "hum_pct": None if hum_pct is None else round(hum_pct, 1),
    }

  return picolab.Sensor("%s (0x%02x)" % (name, addr), connect, read)


sensors = [make_sensor(name, addr) for name, addr in STATIONS]
display = picolab.Display()
light = picolab.StatusLight()
tick = picolab.Throttle(500)
heartbeat = picolab.Throttle(5000)


def row(name, data):
  if not data:
    return "%-3s ---.- C --%%" % name
  hum = " --%" if data["hum_pct"] is None else "%3.0f%%" % data["hum_pct"]
  return "%-3s %5.1f C %s" % (name, data["temp_c"], hum)


while True:
  if tick.ready():
    for s in sensors:
      s.poll()
    light.set_slots([s.ok for s in sensors])

    lines = ["BME280 x%d" % len(sensors)]
    for (name, _), s in zip(STATIONS, sensors):
      lines.append(row(name, s.data))
    both = [s.data["temp_c"] for s in sensors if s.data]
    if len(both) == 2:
      lines.append("dT: %+5.1f C" % (both[0] - both[1]))
    display.show(lines)

    if heartbeat.ready():
      for s in sensors:
        picolab.log(s.name if s.ok else s.name + " (unplugged)", s.data)
    gc.collect()

  light.poll()
  time.sleep_ms(20)
