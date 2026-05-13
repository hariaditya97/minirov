# ms5837.py — MicroPython driver for MS5837 (Bar02/Bar30)
# Adapted from Blue Robotics Python library
import time

MS5837_ADDR        = 0x76
MS5837_02BA        = 0
MS5837_30BA        = 1
MS5837_DENSITY_FRESHWATER  = 997
MS5837_DENSITY_SALTWATER   = 1029

CMD_RESET          = 0x1E
CMD_ADC_READ       = 0x00
CMD_PROM_READ      = 0xA0
CMD_CONVERT_D1     = 0x40
CMD_CONVERT_D2     = 0x50
OSR_256            = 0

class MS5837:
    def __init__(self, model, i2c):
        self._model = model
        self._i2c = i2c
        self._pressure    = 0
        self._temperature = 0
        self._fluidDensity = MS5837_DENSITY_FRESHWATER
        self._C = []
        self._init()

    def _init(self):
        self._i2c.writeto(MS5837_ADDR, bytes([CMD_RESET]))
        time.sleep_ms(10)
        for i in range(7):
            data = self._i2c.readfrom_mem(MS5837_ADDR, CMD_PROM_READ + i*2, 2)
            self._C.append((data[0] << 8) | data[1])

    def read(self, oversampling=OSR_256):
        self._i2c.writeto(MS5837_ADDR, bytes([CMD_CONVERT_D1 + oversampling*2]))
        time.sleep_ms(3)
        raw = self._i2c.readfrom_mem(MS5837_ADDR, CMD_ADC_READ, 3)
        D1 = raw[0] << 16 | raw[1] << 8 | raw[2]

        self._i2c.writeto(MS5837_ADDR, bytes([CMD_CONVERT_D2 + oversampling*2]))
        time.sleep_ms(3)
        raw = self._i2c.readfrom_mem(MS5837_ADDR, CMD_ADC_READ, 3)
        D2 = raw[0] << 16 | raw[1] << 8 | raw[2]

        self._calculate(D1, D2)

    def _calculate(self, D1, D2):
        dT   = D2 - self._C[5] * 256
        TEMP = 2000 + dT * self._C[6] / 8388608

        OFF  = self._C[2] * 65536 + (self._C[4] * dT) / 128
        SENS = self._C[1] * 32768 + (self._C[3] * dT) / 256
        P    = (D1 * SENS / 2097152 - OFF) / 8192

        self._temperature = TEMP / 100.0
        self._pressure    = P / 10.0  # mbar

    def pressure(self):
        return self._pressure

    def temperature(self):
        return self._temperature

    def depth(self):
        return (self._pressure * 100 - 101300) / (
            self._fluidDensity * 9.80665)

    def setFluidDensity(self, density):
        self._fluidDensity = density