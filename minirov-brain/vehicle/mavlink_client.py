# This is  the only part of the codebase that speaks MAVLink. Everything else in the system talks to this class. 
# Nothing else imports pymavlink directly. That boundary matters because MAVLink is complex and low-level. 

from pymavlink import mavutil
from config import HEARTBEAT_TIMEOUT, MAVLINK_BAUD, MAVLINK_CONNECTION, MODE_MANUAL, MODE_STABILIZE, MODE_DEPTH_HOLD, MODE_AUTO, RC_CHANNEL_AUX1, RC_CHANNEL_AUX2, RC_CHANNEL_FORWARD, RC_CHANNEL_LATERAL, RC_CHANNEL_PITCH, RC_CHANNEL_ROLL, RC_CHANNEL_THROTTLE, RC_CHANNEL_YAW, RC_NEUTRAL
from datetime import datetime
import threading
import os
os.environ['MAVLINK20'] = '1'  # Ensure MAVLink 2.0 is used for better message parsing and features

class MAVLinkClient:
    def __init__(self):
        self.master = mavutil.mavlink_connection(MAVLINK_CONNECTION, baud=MAVLINK_BAUD, dialect='ardupilotmega') # create a connection
        self.last_heartbeat = None
        self._lock = threading.Lock()
        self.master.wait_heartbeat() # block until heartbeat received
        # print("Heartbeat from system (system %u component %u)" % (self.master.target_system, self.master.target_component))

    def arm(self):
        with self._lock:
            self._check_connection()
        # MANUAL mode enables raw RC passthrough. Whatever RC override values your code sends go directly to the ESCs with zero processing, zero stabilisation, and no safety filtering from ArduSub.
            msg = self.master.recv_match (type='HEARTBEAT', blocking=True, timeout=3)
            if msg is None:
            # print("No heartbeat received — check ArduSub connection")
                return
            mode = mavutil.mode_string_v10(msg)
            if mode == "MANUAL":
            # print (f"Vehicle is in {mode} mode. Arming not permitted in MANUAL mode. Switch to STABILIZED mode and retry")
                return
            self.master.arducopter_arm()
        # print ("Arming command sent.")

    def disarm(self):
        with self._lock:
            self._check_connection()
            self.master.arducopter_disarm()
        # print ("Disarm command sent.")
    
    def set_mode(self, mode):
        self._check_connection()
        try: 
            mode_id = self.master.mode_mapping()[mode]
            self.master.set_mode(mode_id)
            # print (f"Set mode command sent: {mode}")
        except KeyError:
            # print(f"Invalid mode: {mode}. Valid modes: {list(self.master.mode_mapping().keys())}")
            return

    def send_rc_override(self, channels: dict):
        with self._lock:
            self._check_connection()
            print(f"DEBUG RC: sending override {channels}")
            self.master.mav.rc_channels_override_send(
            self.master.target_system,
            self.master.target_component,
                channels.get(RC_CHANNEL_PITCH, RC_NEUTRAL), # pitch
                channels.get(RC_CHANNEL_ROLL, RC_NEUTRAL), # roll
                channels.get(RC_CHANNEL_THROTTLE, RC_NEUTRAL), # throttle
                channels.get(RC_CHANNEL_YAW, RC_NEUTRAL), # yaw
                channels.get(RC_CHANNEL_FORWARD, RC_NEUTRAL), # forward
                channels.get(RC_CHANNEL_LATERAL, RC_NEUTRAL), # lateral
                channels.get(RC_CHANNEL_AUX1, RC_NEUTRAL), # auxiliary (not used)
                channels.get(RC_CHANNEL_AUX2, RC_NEUTRAL)  # auxiliary (not used)
            )
        # print (f"RC override sent: {channels}")

    def get_attitude(self):
        with self._lock:
            msg = self.master.recv_match(type='ATTITUDE', blocking=True, timeout=3)
            if msg is None:
            # print("No ATTITUDE message received")
                return None
            return {
                'roll': self._rads_to_degrees(msg.roll), # convert from radians
                'pitch': self._rads_to_degrees(msg.pitch), 
                'yaw': self._rads_to_degrees(msg.yaw)   
            }

    def get_armed_status(self):
        with self._lock:
            msg = self.master.recv_match(type='HEARTBEAT', blocking=True, timeout=3)
            if msg is None:
                return None
            return (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0

    def get_mode(self):
        with self._lock:
            msg = self.master.recv_match (type='HEARTBEAT', blocking=True, timeout=3)
            if msg is None:
            # print("No heartbeat received — check ArduSub connection")
                return None
            return mavutil.mode_string_v10(msg)

    def get_depth(self):
        with self._lock:
            msg = self.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=3)
            if msg is None:
            # print("No GLOBAL_POSITION_INT message received")
                return None
            return msg.relative_alt / 1000.0 # convert from millimeters to meters
    
    def get_battery_voltage(self):
        with self._lock:
            msg = self.master.recv_match(type='SYS_STATUS', blocking=True, timeout=3)
            if msg is None:
                # print("No SYS_STATUS message received")
                return None
            return msg.voltage_battery / 1000.0 # convert from millivolts to volts

    def _check_connection(self):
        if self.last_heartbeat is None:
            raise ConnectionError("No heartbeat received yet. Check ArduSub connection.")
        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        if elapsed > HEARTBEAT_TIMEOUT:
            raise ConnectionError(f"Heartbeat lost — last received {elapsed:.1f}s ago")

    def _rads_to_degrees(self, radians: float) -> float:
        return radians * 57.2958