from machine import I2C, Pin
import BME280

class EnclosureSensor:

    def __init__(self, i2c):
        self.sensor = BME280.BME280(i2c=i2c)

    def read(self):
        temp, pressure, humidity = self.sensor.read_compensated_data()
        return {
            "temp_c":        round(temp, 2),
            "pressure_hpa":  round(self.convert_to_hectopascals(pressure), 2),  
            "humidity_pct":  round(humidity, 2)
        }


    def convert_to_hectopascals(self, pascals):
         hpa = pascals / 100
         return hpa
    

def init_bme280(sda_pin=6, scl_pin=7):
    i2c = I2C(1, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
    return EnclosureSensor(i2c)