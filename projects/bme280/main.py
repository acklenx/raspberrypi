# BME280 web demo: temperature, humidity, and pressure on the OLED, the
# terminal, and a live web dashboard.
#
# The Pico opens a Wi-Fi network named PicoLab-<N>. Join it and browse
# to http://192.168.4.1 (JSON at /data).
#
# Fault tolerant: runs with the sensor missing, the display missing, or
# both, and picks either up the moment it is plugged in. No restarts.
#
# On the board: main.py, index.html, lib/picolab.py, lib/bme280.py,
# lib/ssd1306.py.

import gc

import picolab

sensor = None


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


def data_fn():
  d = {"ok": sensor.ok, "ssid": app.ssid}
  if sensor.data:
    d.update(sensor.data)
  return d


sensor = picolab.Sensor("BME280", connect, read)
display = picolab.Display()
app = picolab.WebApp()
heartbeat = picolab.Throttle(5000)

app.announce("BME280 Station Active!")

while True:
  data = sensor.poll()

  if data:
    hum = "no hum" if data["hum_pct"] is None else "%5.1f %%" % data["hum_pct"]
    display.show([
        app.ssid,
        "T: %5.1f C" % data["temp_c"],
        "H: %s" % hum,
        "P: %6.1f hPa" % data["press_hpa"],
    ])
  else:
    display.show([
        app.ssid,
        "192.168.4.1",
        "no sensor...",
        "hot-plug ready",
    ])

  if heartbeat.ready():
    picolab.log("BME280" if sensor.ok else "BME280 (unplugged)", data)

  app.poll(data_fn)
  gc.collect()
