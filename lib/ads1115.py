# MicroPython ADS1115 driver (I2C): 16-bit, 4-channel analog-to-digital
# converter. The Pico only has three ADC pins (and the Pi Zero has none),
# so this chip is how a project grows more analog inputs: it rides the
# same two I2C wires as everything else.
#
#   from ads1115 import ADS1115
#   adc = ADS1115(i2c)            # default address 0x48
#   volts = adc.read_volts(0)     # single-ended, channel 0..3
#
# Address pin: ADDR->GND = 0x48 (default), ADDR->VDD = 0x49,
# ADDR->SDA = 0x4A, ADDR->SCL = 0x4B. Four chips fit on one bus.

import struct
import time

REG_CONVERSION = 0
REG_CONFIG = 1

# PGA (gain) setting -> full-scale volts. The default 4.096 comfortably
# covers 3.3V sensors; never feed an input more than VDD + 0.3V.
_FS = (6.144, 4.096, 2.048, 1.024, 0.512, 0.256)


class ADS1115:
  def __init__(self, i2c, address=0x48, pga=1):
    self.i2c = i2c
    self.address = address
    self.pga = pga
    self.fs = _FS[pga]
    # Probe now so a missing chip fails fast (hot-plug wrappers rely on it)
    self.i2c.readfrom_mem(self.address, REG_CONFIG, 2)

  def read_raw(self, channel):
    """One single-shot, single-ended conversion on channel 0..3."""
    if not 0 <= channel <= 3:
      raise ValueError("channel must be 0..3")
    config = (0x8000                        # start a single conversion
              | (0x4000 | (channel << 12))  # MUX: AINx vs GND
              | (self.pga << 9)
              | 0x0100                      # single-shot mode
              | 0x0080                      # 128 samples/sec (~8 ms)
              | 0x0003)                     # comparator off
    self.i2c.writeto_mem(self.address, REG_CONFIG, struct.pack(">H", config))
    for _ in range(10):
      time.sleep_ms(2)
      cfg = struct.unpack(">H", self.i2c.readfrom_mem(self.address, REG_CONFIG, 2))[0]
      if cfg & 0x8000:  # OS bit returns high when the conversion is done
        break
    return struct.unpack(">h", self.i2c.readfrom_mem(self.address, REG_CONVERSION, 2))[0]

  def read_volts(self, channel):
    return self.read_raw(channel) * self.fs / 32767
