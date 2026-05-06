import time
import math

class AttitudeEstimator:
    def __init__(self, alpha = 0.98):
        self.alpha = alpha
        self.roll = 0.0
        self.pitch = 0.0
        self.last_time = 0.0

    def update (self, imu_data):
        now = time.ticks_ms()
        dt = time.ticks_diff(now, self.last_time) / 1000.0  
        self.last_time = now
        ax = imu_data['ax']
        ay = imu_data['ay']
        az = imu_data['az']
        gx = imu_data['gx']
        gy = imu_data['gy']
        # gz = imu_data['gz']

        accel_roll = math.atan2(ay,az)
        accel_pitch = math.atan2 (-ax, az)
        
        self.roll  = self.alpha * (self.roll  + gx * dt) + (1 - self.alpha) * math.degrees(accel_roll)
        self.pitch = self.alpha * (self.pitch + gy * dt) + (1 - self.alpha) * math.degrees(accel_pitch)

        return self.roll, self.pitch    

