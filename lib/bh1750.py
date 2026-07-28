# MicroPython BH1750 ambient light sensor driver (I2C, address 0x23).
#
#   from bh1750 import BH1750
#   light = BH1750(i2c)
#   lux = light.read()

import time

POWER_ON = 0x01
RESET = 0x07
CONT_HIRES = 0x10  # 1 lx resolution, ~120ms per measurement, continuous


class BH1750:
  def __init__(self, i2c, address=0x23):
    self.i2c = i2c
    self.address = address
    if address not in i2c.scan():
      raise OSError("BH1750 not found at 0x23")
    self._cmd(POWER_ON)
    self._cmd(RESET)
    self._cmd(CONT_HIRES)
    time.sleep_ms(180)  # first conversion

  def _cmd(self, b):
    self.i2c.writeto(self.address, bytes([b]))

  def read(self):
    """Returns illuminance in lux (float)."""
    d = self.i2c.readfrom(self.address, 2)
    return ((d[0] << 8) | d[1]) / 1.2
