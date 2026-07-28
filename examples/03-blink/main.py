# Blink: the "hello world" of hardware.
#
# The Pico 2 W has an onboard LED wired to a pin named "LED".
# No wiring needed for this one. Run it and watch the board.

import time
from machine import Pin

led = Pin("LED", Pin.OUT)

while True:
  led.on()
  time.sleep(0.5)
  led.off()
  time.sleep(0.5)

# Things to try:
#   1. Make it blink faster. How fast until it just looks "on"?
#   2. Blink SOS: three short, three long, three short.
#   3. Wire an external LED (long leg to GP15 through a 330 ohm
#      resistor, short leg to GND) and use Pin(15, Pin.OUT).
#
# Press Ctrl+C in the terminal to stop the loop.
