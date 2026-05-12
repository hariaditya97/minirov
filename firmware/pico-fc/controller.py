import time
from machine import PWM, Pin

class PID: 
    def __init__(self, kp, ki, kd, limit = 100.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd 
        self.limit = limit
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, error, dt):
        self._integral += error * dt
        self._integral = max(-self.limit, min(self.limit, self._integral))
        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        self._prev_error = error
        output = (self.kp * error + (self.ki * self._integral) + (self.kd * derivative))
        return output

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0

class ThrusterController:
    def __init__(self):
        self.thruster_map = {
            'HL': PWM(Pin(0), freq=50),
            'HR': PWM(Pin(1), freq=50),
            'VL': PWM(Pin(2), freq=50),
            'VR': PWM(Pin(3), freq=50),
        }
        self._armed = False
        self._stop_all()
        self.pid_roll = PID(kp=1.2, ki=0.05, kd=0.3)

    def arm(self):
        self._stop_all()
        time.sleep(2)  
        self._armed = True

    def disarm(self):
        self._armed = False
        self._stop_all()

    def _us_to_duty(self, us):
        return int((us / 20000) * 65535)

    def _stop_all(self):
        for name, pwm in self.thruster_map.items():
            pwm.duty_u16(self._us_to_duty(1500))

    def _set(self, name, value):
        if self._armed:
            value = max(-100.0, min(100.0, value))
            us = int(1500 + (value / 100.0) * 400)
            self.thruster_map[name].duty_u16(self._us_to_duty(us))

    def update(self, roll, dt, surge=0.0, yaw=0.0, depth=0.0):
        if not self._armed:
            return

        roll_correction = self.pid_roll.compute(roll, dt)     #PID controller functioning
        self._set('VL', depth - roll_correction)
        self._set('VR', depth + roll_correction)
        self._set('HL', surge - yaw)
        self._set('HR', surge + yaw)
