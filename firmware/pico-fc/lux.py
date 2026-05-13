from machine import I2C, Pin
from bh1750 import BH1750

class LuxSensor:

    def __init__(self, i2c):
        self.sensor = BH1750(i2c)

    def read(self):
        return {
            "lux": round(self.sensor.read_lux(), 1)
        }


def init_lux(sda_pin=4, scl_pin=5):
    i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
    return LuxSensor(i2c)