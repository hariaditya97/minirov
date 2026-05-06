import math

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
        derivative = (error - self._prev_error) / dt
        self._prev_error = error
        output = (self.kp * error + (self.ki * self._integral) + (self.kd * derivative))
        return output

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0

class ThrusterController:
    def __init__(self):
        pass 


