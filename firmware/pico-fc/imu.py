import struct
from machine import I2C, Pin

class MPU6050: 
    MPU_ADDR       = 0x68
    REG_PWR_MGMT_1 = 0x6B
    REG_ACCEL_XOUT = 0x3B
    ACCEL_SCALE    = 16384.0
    GYRO_SCALE     = 131.0

    def __init__ (self, i2c):
        self.i2c = i2c
        i2c.writeto_mem(self.MPU_ADDR, self.REG_PWR_MGMT_1, bytes([0])) # Wake up the MPU6050
    
    def read_all(self):
        data = self.i2c.readfrom_mem(self.MPU_ADDR, self.REG_ACCEL_XOUT, 14)
        ax_raw, ay_raw, az_raw, _, gx_raw, gy_raw, gz_raw = struct.unpack('>hhhhhhh', data)
        ax = ax_raw / self.ACCEL_SCALE  # gives g
        ay = ay_raw / self.ACCEL_SCALE 
        az = az_raw / self.ACCEL_SCALE  
        gx = gx_raw / self.GYRO_SCALE    # gives degrees/second
        gy = gy_raw / self.GYRO_SCALE    
        gz = gz_raw / self.GYRO_SCALE
        return {'ax': ax, 'ay': ay, 'az': az, 'gx': gx, 'gy': gy, 'gz': gz}
  

def init_imu(sda_pin=4, scl_pin=5):
    i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
    return MPU6050(i2c)
