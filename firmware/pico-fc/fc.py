import time
import json
from imu import init_imu
from attitude_estimator import AttitudeEstimator
from controller import ThrusterController

WATCHDOG_MS = 500

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
            "state":    State.INIT,
            "roll":     0.0,
            "pitch":    0.0,
            "heading":  0.0,
            "surge":    0.0,
            "yaw":      0.0,
            "depth":    0.0,
            "armed":    False,
        }
        self.state = State.INIT
        self._last_cmd_time = time.ticks_ms()
        self._cal_count = 0
        self._cal_gx = 0.0
        self._cal_gy = 0.0
        self._cal_gz = 0.0

        print('{"event": "INIT", "msg": "minirov pico-fc starting"}')

        try:
            self.imu = init_imu()
            self.estimator = AttitudeEstimator()
            self.controller = ThrusterController()
            print('{"event": "INIT", "msg": "hardware ok"}')
        except Exception as e:
            self._enter_failsafe("hardware init failed: " + str(e))
            return

    def update(self, dt):

        if self.state == State.INIT:
            self.state = State.CALIBRATING
            self._update_vehicle("state", State.CALIBRATING)
            print('{"event": "CALIBRATING", "msg": "collecting gyro bias"}')

        elif self.state == State.CALIBRATING:
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

        elif self.state == State.READY:
            # waiting for ARM command — do nothing except read IMU passively
            imu_data = self.imu.read_all()
            roll, pitch = self.estimator.update(imu_data)
            self._update_vehicle("roll", roll)
            self._update_vehicle("pitch", pitch)

        elif self.state == State.ARMED:
            if time.ticks_diff(time.ticks_ms(), self._last_cmd_time) > WATCHDOG_MS:
                self._enter_failsafe("watchdog: no command for 500ms")
                return
            imu_data = self.imu.read_all()
            roll, pitch = self.estimator.update(imu_data)
            self._update_vehicle("roll", roll)
            self._update_vehicle("pitch", pitch)

        elif self.state == State.RUNNING:
            if time.ticks_diff(time.ticks_ms(), self._last_cmd_time) > WATCHDOG_MS:
                self._enter_failsafe("watchdog: no command for 500ms")
                return
            imu_data = self.imu.read_all()
            roll, pitch = self.estimator.update(imu_data)
            self._update_vehicle("roll", roll)
            self._update_vehicle("pitch", pitch)
            self.controller.update(
                roll=roll,
                dt=dt,
                surge=self.vehicle["surge"],
                yaw=self.vehicle["yaw"],
                depth=self.vehicle["depth"]
            )
            self._print_telemetry()

        elif self.state == State.FAILSAFE:
            pass

    def handle_command(self, cmd):

        if self.state == State.FAILSAFE:
            print('{"event": "IGNORED", "msg": "in failsafe, reboot required"}')
            return

        if cmd == "ARM":
            if self.state == State.READY:
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
        self._update_vehicle("state", State.FAILSAFE)
        self._update_vehicle("armed", False)
        print('{"event": "FAILSAFE", "reason": "' + reason + '"}')

    def _print_telemetry(self):
        print(json.dumps({
            "roll":    round(self.vehicle["roll"],  2),
            "pitch":   round(self.vehicle["pitch"], 2),
            "state":   self.vehicle["state"],
            "armed":   self.vehicle["armed"],
            "surge":   self.vehicle["surge"],
            "yaw":     self.vehicle["yaw"],
            "depth":   self.vehicle["depth"],
        }))