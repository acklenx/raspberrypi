# MicroPython VL53L1X driver (I2C, address 0x29). Long-range time of
# flight: up to ~4 m, vs ~1.2 m for the VL53L0X.
#
# Adapted from drakxtwo/vl53l1x_pico (MIT license), itself based on the
# Pololu VL53L1X Arduino library and the ST VL53L1X ultra lite driver.
# Changes for this repo: time.sleep_ms instead of machine.lightsleep
# (lightsleep disturbs the Pico W radio), a fast bus scan so a missing
# sensor fails immediately (hot-plug friendly), a boot-state wait, and
# read() also returns the range status so demos can show "no target".
#
#   from vl53l1x import VL53L1X
#   tof = VL53L1X(i2c)
#   mm, valid = tof.read()

import time

MODEL_ID = 0xEACC

# ST default configuration for registers 0x2D..0x87. Includes
# "clear interrupt" (0x86=0x01) and "start ranging" (0x87=0x40), so the
# sensor free-runs as soon as this blob is written.
_DEFAULT_CONFIG = bytes([
    0x00, 0x00, 0x00, 0x01, 0x02, 0x00, 0x02, 0x08, 0x00, 0x08,
    0x10, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00, 0x0F,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x0B, 0x00, 0x00, 0x02,
    0x0A, 0x21, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00, 0xC8,
    0x00, 0x00, 0x38, 0xFF, 0x01, 0x00, 0x08, 0x00, 0x00, 0x01,
    0xDB, 0x0F, 0x01, 0xF1, 0x0D, 0x01, 0x68, 0x00, 0x80, 0x08,
    0xB8, 0x00, 0x00, 0x00, 0x00, 0x0F, 0x89, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x01, 0x0F, 0x0D, 0x0E, 0x0E, 0x00,
    0x00, 0x02, 0xC7, 0xFF, 0x9B, 0x00, 0x00, 0x00, 0x01, 0x01,
    0x40,
])

# Range status 9 = valid; 8 = valid but clipped at minimum range.
VALID_STATUSES = (9, 8)


class VL53L1X:
  def __init__(self, i2c, address=0x29):
    self.i2c = i2c
    self.address = address
    if address not in i2c.scan():
      raise OSError("VL53L1X not found at 0x29")

    self._reset()
    time.sleep_ms(1)
    if self._read16(0x010F) != MODEL_ID:
      raise OSError("not a VL53L1X (bad model id)")

    # Wait for firmware boot (FIRMWARE__SYSTEM_STATUS bit 0)
    deadline = time.ticks_add(time.ticks_ms(), 1000)
    while not (self._read8(0x00E5) & 0x01):
      if time.ticks_diff(time.ticks_ms(), deadline) > 0:
        raise OSError("VL53L1X boot timeout")
      time.sleep_ms(10)

    self.i2c.writeto_mem(self.address, 0x2D, _DEFAULT_CONFIG, addrsize=16)

    # The ST API applies this once ranging starts (MM1/MM2 disabled):
    # outer offset = inner offset * 4
    self._write16(0x001E, self._read16(0x0022) * 4)
    time.sleep_ms(200)

  def _write8(self, reg, value):
    self.i2c.writeto_mem(self.address, reg, bytes([value]), addrsize=16)

  def _write16(self, reg, value):
    self.i2c.writeto_mem(
        self.address, reg, bytes([(value >> 8) & 0xFF, value & 0xFF]),
        addrsize=16)

  def _read8(self, reg):
    return self.i2c.readfrom_mem(self.address, reg, 1, addrsize=16)[0]

  def _read16(self, reg):
    d = self.i2c.readfrom_mem(self.address, reg, 2, addrsize=16)
    return (d[0] << 8) | d[1]

  def _reset(self):
    self._write8(0x0000, 0x00)
    time.sleep_ms(100)
    self._write8(0x0000, 0x01)

  def read(self):
    """Returns (distance_mm, valid). Sensor free-runs at ~10 Hz."""
    d = self.i2c.readfrom_mem(self.address, 0x0089, 17, addrsize=16)
    status = d[0] & 0x1F
    mm = (d[13] << 8) | d[14]
    return mm, status in VALID_STATUSES
