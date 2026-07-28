import time
from machine import Pin, I2C

class VL53L0X:
    def __init__(self, i2c, address=0x29):
        self.i2c = i2c
        self.address = address
        self.init_sensor()

    def _write_reg(self, reg, value):
        self.i2c.writeto_mem(self.address, reg, bytes([value]))

    def _read_reg(self, reg):
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def _read_reg_16(self, reg):
        data = self.i2c.readfrom_mem(self.address, reg, 2)
        return (data[0] << 8) | data[1]

    def init_sensor(self):
        # Basic power-on sequence and calibration defaults for VL53L0X
        self._write_reg(0x88, 0x00)
        self._write_reg(0x80, 0x01)
        self._write_reg(0xFF, 0x01)
        self._write_reg(0x00, 0x00)
        self._read_reg(0x91)
        self._write_reg(0x00, 0x01)
        self._write_reg(0xFF, 0x00)
        self._write_reg(0x80, 0x00)

    def ping(self):
        # Single-shot measurement call
        self._write_reg(0x00, 0x01)
        for _ in range(100):
            if not (self._read_reg(0x00) & 0x01):
                break
            time.sleep_ms(5)
        
        # Read range result from registers 0x1E and 0x1F
        dist = self._read_reg_16(0x1E)
        return dist