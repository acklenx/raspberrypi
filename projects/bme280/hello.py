# BME280 "hello, world": the fewest lines that prove the sensor works.
#
# Wiring (shared I2C bus): SDA=GP0, SCL=GP1, 3V3, GND.
# On the board: this file, plus lib/bme280.py.
#
# The onboard LED is the truth light. ON means we just got a good
# reading. OFF means wiring or sensor trouble. No guessing about whether
# 3V3 is shorted or the bus is dead: if the light is on, we are talking.

import time
from machine import I2C, Pin
from bme280 import BME280

led = Pin("LED", Pin.OUT)
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
sensor = None

while True:
  try:
    if sensor is None:
      sensor = BME280(i2c)
    temp_c, press_hpa, hum_pct = sensor.read()
    led.on()
    hum = "n/a" if hum_pct is None else "%.1f %%" % hum_pct
    print("T: %5.1f C   H: %s   P: %6.1f hPa" % (temp_c, hum, press_hpa))
  except Exception as e:
    sensor = None
    led.off()
    print("no reading:", e)
  time.sleep(1)
