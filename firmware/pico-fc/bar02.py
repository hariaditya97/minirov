from machine import I2C, Pin
from ms5837 import MS5837, MS5837_02BA, MS5837_DENSITY_FRESHWATER

class DepthSensor:

    def __init__(self, i2c):
        self.sensor = MS5837(MS5837_02BA, i2c)
        self.sensor.setFluidDensity(MS5837_DENSITY_FRESHWATER)

    def read(self):
        self.sensor.read()
        return {
            "depth_m":   round(self.sensor.depth(),       3),
            "pressure":  round(self.sensor.pressure(),    2),
            "water_temp": round(self.sensor.temperature(), 2)
        }


def init_bar02(sda_pin=4, scl_pin=5):
    i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
    return DepthSensor(i2c)