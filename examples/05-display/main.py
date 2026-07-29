# Your first breadboard circuit: an OLED display on the I2C bus.
#
# Up to now the Pico needed nothing but a USB cable. This is the first
# time wires can be wrong, so this program is built to tell you the truth
# about them.
#
# Wiring (the same 4 wires every I2C part in this repo uses):
#
#   | OLED pin | Pico |
#   | -------- | ---- |
#   | VCC      | 3V3 (pin 36) |
#   | GND      | GND (any GND pin, e.g. 38) |
#   | SDA      | GP0 (pin 1) |
#   | SCL      | GP1 (pin 2) |
#
# On the board: this file, plus lib/ssd1306.py.
#
# The onboard LED is the truth light. ON means the display is wired right
# and answering. OFF means check the wires. You never have to guess.

import time
from machine import I2C, Pin
import ssd1306

led = Pin("LED", Pin.OUT)
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
oled = None
count = 0

while True:
  try:
    if oled is None:
      oled = ssd1306.SSD1306_I2C(128, 64, i2c)
      print("Display found at", [hex(a) for a in i2c.scan()])
    oled.fill(0)
    oled.text("It's alive!", 0, 0)
    oled.text("Maker Lab Kids", 0, 16)
    oled.text("count: %d" % count, 0, 32)
    oled.show()
    led.on()
  except Exception as e:
    oled = None
    led.off()
    print("no display:", e, "- check SDA=GP0, SCL=GP1, 3V3, GND")
  count += 1
  time.sleep(1)

# Things to try:
#   1. Change the message. Add a fourth line at y=48.
#   2. Pull the SDA wire mid-run. Watch the truth light. Put it back.
#   3. Draw: oled.rect(x, y, w, h, 1) and oled.fill_rect(...) work too.
