import time
from machine import I2C, Pin
import ssd1306

DISPLAY_ADDR = 0x3C
WIDTH  = 128
HEIGHT = 64

class Display:

    def __init__(self, i2c):
        self.oled = ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)
        self._last_update = time.ticks_ms()
        self._update_interval = 200
        self.oled.fill(0)
        self.oled.show()

    def update(self, vehicle):
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_update) < self._update_interval:
            return
        self._last_update = now

        self.oled.fill(0)

        self.oled.text("ST:{}".format(vehicle["state"]),    0, 0)
        self.oled.text("R:{:.1f} P:{:.1f}".format(
            vehicle["roll"], vehicle["pitch"]),              0, 16)
        self.oled.text("S:{} Y:{} D:{}".format(
            int(vehicle["surge"]),
            int(vehicle["yaw"]),
            int(vehicle["depth"])),                          0, 32)
        self.oled.text("{}  T:{:.1f}C".format(
            "ARMED" if vehicle["armed"] else "DISARMED",
            vehicle.get("temp_c", 0.0)),                     0, 48)

        self.oled.show()

    def clear(self):
        self.oled.fill(0)
        self.oled.show()


def init_display(sda_pin=4, scl_pin=5):
    i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
    return Display(i2c)