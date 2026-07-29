# BME280 bench demo: temperature, humidity, pressure on the OLED and
# terminal. No Wi-Fi. Fault tolerant: runs with the sensor missing, the
# display missing, or both, and picks either up the moment it is plugged
# in. No restarts needed.
#
# The onboard LED is the truth light: a short blink every cycle means the
# sensor is happy, a long blink means it is missing or misbehaving, and
# no blinking at all means the code is not running.
#
# Wiring (shared I2C bus): SDA=GP0, SCL=GP1, 3V3, GND.
# On the board: this file (as main.py or run it from the IDE),
# lib/picolab.py, lib/bme280.py, lib/ssd1306.py.

import gc
import time

import picolab

picolab.banner("BME280 Bench Demo", [
    "Wiring: I2C0 SDA=GP0 SCL=GP1",
    "BME280 at 0x76/0x77, OLED at 0x3C",
    "Both parts optional + hot-pluggable",
])


def connect():
  from bme280 import BME280
  return BME280(picolab.i2c())


def read(dev):
  temp_c, press_hpa, hum_pct = dev.read()
  return {
      "temp_c": round(temp_c, 1),
      "press_hpa": round(press_hpa, 1),
      "hum_pct": None if hum_pct is None else round(hum_pct, 1),
  }


sensor = picolab.Sensor("BME280", connect, read)
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
    hum = "n/a (BMP280)" if data["hum_pct"] is None else "%5.1f %%" % data["hum_pct"]
    display.show([
        "BME280  live",
        "T: %5.1f C" % data["temp_c"],
        "H: %s" % hum,
        "P: %6.1f hPa" % data["press_hpa"],
    ])
  else:
    display.show([
        "BME280",
        "no sensor...",
        "check SDA=GP0",
        "      SCL=GP1",
    ])

  if heartbeat.ready():
    picolab.log("BME280" if sensor.ok else "BME280 (unplugged)", data)

  light.poll()
  gc.collect()
