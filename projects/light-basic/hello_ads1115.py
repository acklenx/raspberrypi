# GL5528 on an ADS1115 channel: the same light divider as main.py, but
# read over I2C instead of a Pico ADC pin. This is the stepping stone to
# the worm-bin build, where the Pico's own ADC pins are spoken for and
# all the slow analog signals ride the ADS1115.
#
# Wiring: ADS1115 on the shared I2C bus (VDD=3V3, GND, SDA=GP0, SCL=GP1,
# ADDR to GND = 0x48). Divider: LDR from 3V3 to A0, 10k from A0 to GND.
# On the board: this file, plus lib/ads1115.py.
#
# The onboard LED is the truth light: ON means the ADS1115 is answering
# (so the I2C wiring is right), OFF means it is not. And unlike a bare
# Pico ADC pin, this setup DOES notice when the chip goes missing.

import time
from machine import I2C, Pin
from ads1115 import ADS1115


# ===== CONFIG =====
# Which ADS1115 input the divider middle point uses (default A0 = 0).
CHANNEL = 0
# ==================

led = Pin("LED", Pin.OUT)
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
adc = None

while True:
  try:
    if adc is None:
      adc = ADS1115(i2c)
    volts = adc.read_volts(CHANNEL)
    led.on()
    pct = max(0.0, min(100.0, volts / 3.3 * 100))
    print("Light: %5.1f %%   (%.2f V on A0)" % (pct, volts))
  except Exception as e:
    adc = None
    led.off()
    print("no ADS1115:", e)
  time.sleep(1)
