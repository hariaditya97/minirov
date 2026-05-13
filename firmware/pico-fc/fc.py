import time
import json
from imu import init_imu
from attitude import AttitudeEstimator
from controller import ThrusterController
from indicators import Indicators
from display import init_display
from lux import init_lux
# from bme280 import init_bme280  # uncomment when hardware available
# from bar02 import init_bar02    # uncomment when hardware available

WATCHDOG_MS = 5000

class State:
    INIT        = "INIT"
    CALIBRATING = "CALIBRATING"
    READY       = "READY"
    ARMED       = "ARMED"
    RUNNING     = "RUNNING"
    FAILSAFE    = "FAILSAFE"


class FlightController:

    def __init__(self):
        self.vehicle = {
            "state":        State.INIT,
            "roll":         0.0,
            "pitch":        0.0,
            "heading":      0.0,
            "surge":        0.0,
            "yaw":          0.0,
            "depth":        0.0,
            "armed":        False,
            "lux":          0.0,
            "temp_c":       0.0,
            "humidity_pct": 0.0,
            "pressure_hpa": 0.0,
        }
        self.state          = State.INIT
        self._last_cmd_time = time.ticks_ms()
        self._cal_count     = 0
        self._cal_gx        = 0.0
        self._cal_gy        = 0.0
        self._cal_gz        = 0.0
        self._dt            = 0.0

        print('{"event": "INIT", "msg": "minirov pico-fc starting"}')

        try:
            self.imu        = init_imu()
            self.estimator  = AttitudeEstimator()
            self.controller = ThrusterController()
            self.indicators = Indicators()
            self.display    = init_display()
            self.lux        = init_lux()
            # self.enclosure = init_bme280()
            # self.depth     = init_bar02()
            print('{"event": "INIT", "msg": "hardware ok"}')
        except Exception as e:
            self._enter_failsafe("hardware init failed: " + str(e))
            return

    # ----------------------------------------------------------------
    # Main update — called every loop tick
    # ----------------------------------------------------------------

    def update(self, dt):
        self._dt = dt

        if self.state == State.INIT:
            self.state = State.CALIBRATING
            self._update_vehicle("state", State.CALIBRATING)
            print('{"event": "CALIBRATING", "msg": "collecting gyro bias"}')

        elif self.state == State.CALIBRATING:
            self._calibrate()

        elif self.state == State.READY:
            self._sense()
            self._report()

        elif self.state == State.ARMED:
            if self._watchdog_expired():
                self._enter_failsafe("watchdog: no command for 500ms")
                return
            self._sense()
            self._report()

        elif self.state == State.RUNNING:
            if self._watchdog_expired():
                self._enter_failsafe("watchdog: no command for 500ms")
                return
            self._sense()
            self._act()
            self._report()

        elif self.state == State.FAILSAFE:
            self._report()

    # ----------------------------------------------------------------
    # Sense / Act / Report
    # ----------------------------------------------------------------

    def _sense(self):
        imu_data = self.imu.read_all()
        roll, pitch = self.estimator.update(imu_data)
        self._update_vehicle("roll",  roll)
        self._update_vehicle("pitch", pitch)

        lux_data = self.lux.read()
        self._update_vehicle("lux", lux_data["lux"])

        # enclosure = self.enclosure.read()
        # self._update_vehicle("temp_c",       enclosure["temp_c"])
        # self._update_vehicle("humidity_pct", enclosure["humidity_pct"])
        # self._update_vehicle("pressure_hpa", enclosure["pressure_hpa"])

        # depth_data = self.depth.read()
        # self._update_vehicle("depth", depth_data["depth_m"])

    def _act(self):
        self.controller.update(
            roll=self.vehicle["roll"],
            dt=self._dt,
            surge=self.vehicle["surge"],
            yaw=self.vehicle["yaw"],
            depth=self.vehicle["depth"]
        )

    def _report(self):
        if self.state == State.RUNNING:
            self._print_telemetry()
        self.display.update(self.vehicle)
        self.indicators.update(self.state)

    # ----------------------------------------------------------------
    # Calibration
    # ----------------------------------------------------------------

    def _calibrate(self):
        imu_data = self.imu.read_all()
        self._cal_gx += imu_data['gx']
        self._cal_gy += imu_data['gy']
        self._cal_gz += imu_data['gz']
        self._cal_count += 1

        if self._cal_count >= 100:
            self.estimator.set_gyro_bias(
                self._cal_gx / self._cal_count,
                self._cal_gy / self._cal_count,
                self._cal_gz / self._cal_count
            )
            self.state = State.READY
            self._update_vehicle("state", State.READY)
            print('{"event": "READY", "msg": "calibration complete, send ARM"}')

    # ----------------------------------------------------------------
    # Watchdog
    # ----------------------------------------------------------------

    def _watchdog_expired(self):
        return time.ticks_diff(
            time.ticks_ms(), self._last_cmd_time
        ) > WATCHDOG_MS

    # ----------------------------------------------------------------
    # Pre-arm checks
    # ----------------------------------------------------------------

    def _pre_arm_checks(self):
        failures = []

        # Check 1 — IMU sanity
        imu_data = self.imu.read_all()
        az = imu_data['az']
        if not (0.8 < abs(az) < 1.2):
            failures.append("IMU az out of range: {:.2f}g".format(az))

        # Check 2 — gyro bias quality
        bias = abs(self._cal_gx / self._cal_count) if self._cal_count else 99
        if bias > 5.0:
            failures.append("gyro bias excessive: {:.2f}".format(bias))

        # Check 3 — I2C bus scan
        devices = self.imu.i2c.scan()
        if 0x68 not in devices:
            failures.append("primary IMU not found on I2C bus")

        # Check 4 — enclosure humidity (when BME280 available)
        # enclosure = self.enclosure.read()
        # if enclosure["humidity_pct"] > 80.0:
        #     failures.append("humidity too high: {:.1f}%".format(
        #         enclosure["humidity_pct"]))

        if failures:
            for f in failures:
                print('{{"event": "PRE_ARM_FAIL", "msg": "{}"}}'.format(f))
            return False

        print('{"event": "PRE_ARM_OK", "msg": "all checks passed"}')
        return True

    # ----------------------------------------------------------------
    # Command handling
    # ----------------------------------------------------------------

    def handle_command(self, cmd):

        if self.state == State.FAILSAFE:
            if cmd == "RESET":
                self.controller.pid_roll.reset()
                self.state = State.READY
                self._update_vehicle("state", State.READY)
                self._update_vehicle("armed", False)
                self._last_cmd_time = time.ticks_ms()
                print('{"event": "READY", "msg": "reset from failsafe, send ARM"}')
            else:
                print('{"event": "IGNORED", "msg": "in failsafe — send RESET"}')
            return

        if cmd == "ARM":
            if self.state == State.READY:
                if not self._pre_arm_checks():
                    return
                self.controller.arm()
                self.state = State.ARMED
                self._update_vehicle("state", State.ARMED)
                self._update_vehicle("armed", True)
                self._last_cmd_time = time.ticks_ms()
                print('{"event": "ARMED"}')
            else:
                print('{"event": "IGNORED", "msg": "ARM only valid in READY state"}')

        elif cmd == "DISARM":
            self._enter_failsafe("operator disarm")

        elif isinstance(cmd, dict) and cmd.get("heartbeat"):
            self._last_cmd_time = time.ticks_ms()

        elif isinstance(cmd, dict):
            if self.state not in (State.ARMED, State.RUNNING):
                print('{"event": "IGNORED", "msg": "commands only valid when ARMED or RUNNING"}')
                return
            if not self._validate_cmd(cmd):
                print('{"event": "ERROR", "msg": "invalid command format"}')
                return
            self.vehicle["surge"] = float(cmd["surge"])
            self.vehicle["yaw"]   = float(cmd["yaw"])
            self.vehicle["depth"] = float(cmd["depth"])
            self._last_cmd_time = time.ticks_ms()
            if self.state == State.ARMED:
                self.state = State.RUNNING
                self._update_vehicle("state", State.RUNNING)

        else:
            print('{"event": "ERROR", "msg": "unknown command"}')

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _validate_cmd(self, cmd):
        for key in ("surge", "yaw", "depth"):
            if key not in cmd:
                return False
            try:
                val = float(cmd[key])
                if val < -100.0 or val > 100.0:
                    return False
            except (TypeError, ValueError):
                return False
        return True

    def _update_vehicle(self, key, value):
        self.vehicle[key] = value

    def _enter_failsafe(self, reason):
        if hasattr(self, 'controller'):
            self.controller.disarm()
        self.state = State.FAILSAFE
        self._update_vehicle("state",  State.FAILSAFE)
        self._update_vehicle("armed",  False)
        print('{"event": "FAILSAFE", "reason": "' + reason + '"}')

    def _print_telemetry(self):
        print(json.dumps({
            "roll":         round(self.vehicle["roll"],         2),
            "pitch":        round(self.vehicle["pitch"],        2),
            "state":        self.vehicle["state"],
            "armed":        self.vehicle["armed"],
            "surge":        self.vehicle["surge"],
            "yaw":          self.vehicle["yaw"],
            "depth":        self.vehicle["depth"],
            "lux":          self.vehicle["lux"],
            "temp_c":       self.vehicle["temp_c"],
            "humidity_pct": self.vehicle["humidity_pct"],
            "pressure_hpa": self.vehicle["pressure_hpa"],
        }))