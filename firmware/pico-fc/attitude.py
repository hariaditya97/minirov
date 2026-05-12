import time
import math

class AttitudeEstimator:
    def __init__(self, alpha = 0.98):
        self.alpha = alpha
        self.roll = 0.0
        self.pitch = 0.0
        self.last_time = 0.0
        self.bias_gx = 0.0
        self.bias_gy = 0.0
        self.bias_gz = 0.0

    
    def set_gyro_bias(self, bx, by, bz):  # part of CALIBRATION
        self.bias_gx = bx
        self.bias_gy = by
        self.bias_gz = bz

    def update (self, imu_data):
        now = time.ticks_ms()
        dt = time.ticks_diff(now, self.last_time) / 1000.0  
        self.last_time = time.ticks_ms()
        ax = imu_data['ax']
        ay = imu_data['ay']
        az = imu_data['az']
        gx = imu_data['gx'] - self.bias_gx
        gy = imu_data['gy'] - self.bias_gy
        # gz = imu_data['gz']

        accel_roll = math.atan2(ay,az)
        accel_pitch = math.atan2 (-ax, az)
        
        self.roll  = self.alpha * (self.roll  + gx * dt) + (1 - self.alpha) * math.degrees(accel_roll)
        self.pitch = self.alpha * (self.pitch + gy * dt) + (1 - self.alpha) * math.degrees(accel_pitch)
        self.roll  = max(-180.0, min(180.0, self.roll))
        self.pitch = max(-90.0,  min(90.0,  self.pitch))
        
        return self.roll, self.pitch    