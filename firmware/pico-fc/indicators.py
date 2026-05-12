from machine import Pin
import time


class Indicators:
    def __init__(self):
        self.green = Pin(15, Pin.OUT)
        self.purple = Pin(14, Pin.OUT)
        self.blue = Pin(13, Pin.OUT)
        self.red = Pin(12, Pin.OUT)
        self.white = Pin(11, Pin.OUT)
        self.last_blink_time = time.ticks_ms()
        self.blink_interval = 250  # ms
        self.current_state = None
        self.blink_state = False
        self.off()

    def off(self):
        self.green.off()
        self.purple.off()
        self.blue.off()
        self.red.off()
        self.white.off()

    def _blink_led(self, led):
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self.last_blink_time) > self.blink_interval:
            led.toggle()
            self.last_blink_time = current_time

    def update(self, state):
        if state != self.current_state:
            self.off()
            self.current_state = state
        
        if state == "CALIBRATING":
            self._blink_led(self.purple)
        elif state == "READY":
            self.blue.on()
        elif state == "ARMED":
            self.white.on()
        elif state == "RUNNING":
            self._blink_led(self.green)
        elif state == "FAILSAFE":
            self._blink_led(self.red)

