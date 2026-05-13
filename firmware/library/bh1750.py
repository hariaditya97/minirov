# bh1750.py — MicroPython driver for BH1750
# Source: github.com/flrrth/pico-bh1750 (simplified)
from machine import I2C
import time

class BH1750:
    ADDR_LOW  = 0x23
    ADDR_HIGH = 0x5C
    CONT_HIGH = 0x10

    def __init__(self, addr, i2c):
        self.addr = addr
        self.i2c  = i2c
        self.i2c.writeto(self.addr, bytes([self.CONT_HIGH]))
        time.sleep_ms(180)

    @property
    def measurement(self):
        data = self.i2c.readfrom(self.addr, 2)
        return (data[0] << 8 | data[1]) / 1.2