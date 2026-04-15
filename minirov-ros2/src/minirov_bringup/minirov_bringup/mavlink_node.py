#!/usr/bin/env python3
"""
mavlink_node.py — ROS 2 node bridging MAVLink (ArduSub/Pixhawk) to ROS 2 topics.

Publishes:
    /minirov/state      (minirov_msgs/VehicleState)  — vehicle telemetry at 2Hz
    /minirov/heartbeat  (std_msgs/Bool)               — connection status at 1Hz

Subscribes:
    /minirov/commands   (minirov_msgs/VehicleCommand) — executes RC overrides

Parameters:
    connection_string   (string) — MAVLink connection, default udp:0.0.0.0:14550
    state_publish_rate  (float)  — telemetry publish rate Hz, default 2.0
    heartbeat_rate      (float)  — heartbeat publish rate Hz, default 1.0
"""

import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from minirov_msgs.msg import VehicleState, VehicleCommand

try:
    from pymavlink import mavutil
except ImportError:
    mavutil = None


class MavlinkNode(Node):
    def __init__(self):
        super().__init__('mavlink_node')

        # --- Parameters ---
        self.declare_parameter('connection_string', 'udp:0.0.0.0:14550')
        self.declare_parameter('state_publish_rate', 2.0)
        self.declare_parameter('heartbeat_rate', 1.0)

        self.connection_string = self.get_parameter('connection_string').get_parameter_value().string_value
        state_rate = self.get_parameter('state_publish_rate').get_parameter_value().double_value
        heartbeat_rate = self.get_parameter('heartbeat_rate').get_parameter_value().double_value

        # --- Publishers ---
        self.state_pub = self.create_publisher(VehicleState, '/minirov/state', 10)
        self.heartbeat_pub = self.create_publisher(Bool, '/minirov/heartbeat', 10)

        # --- Subscriber ---
        self.command_sub = self.create_subscription(
            VehicleCommand,
            '/minirov/commands',
            self.command_callback,
            10
        )

        # --- Timers ---
        self.state_timer = self.create_timer(1.0 / state_rate, self.publish_state)
        self.heartbeat_timer = self.create_timer(1.0 / heartbeat_rate, self.publish_heartbeat)

        # --- MAVLink state cache ---
        # Stores latest telemetry received from ArduSub
        # Updated by background thread, read by timer callbacks
        self._lock = threading.Lock()
        self._mode = ''
        self._armed = False
        self._depth = 0.0
        self._battery_voltage = 0.0
        self._roll = 0.0
        self._pitch = 0.0
        self._yaw = 0.0
        self._heading = 0.0
        self.connected = False
        self.mav = None

        # --- Connect to MAVLink in background thread ---
        # Connection blocks until heartbeat received so must not run on main thread
        self._connect_thread = threading.Thread(target=self._connect, daemon=True)
        self._connect_thread.start()

        self.get_logger().info(f'mavlink_node started — connecting to {self.connection_string}')

    def _connect(self):
        """Connect to ArduSub and start telemetry receive loop. Runs in background thread."""
        if mavutil is None:
            self.get_logger().error('pymavlink not installed — cannot connect to MAVLink')
            return

        try:
            self.get_logger().info(f'Waiting for MAVLink heartbeat on {self.connection_string}...')
            self.mav = mavutil.mavlink_connection(self.connection_string)
            self.mav.wait_heartbeat()
            self.connected = True
            self.get_logger().info('MAVLink heartbeat received — connected to ArduSub')

            # Request data streams from ArduSub
            self.mav.mav.request_data_stream_send(
                self.mav.target_system,
                self.mav.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL,
                10,  # 10Hz
                1    # start
            )

            # Continuous receive loop — updates state cache
            while rclpy.ok():
                self._receive_telemetry()

        except Exception as e:
            self.get_logger().error(f'MAVLink connection failed: {e}')
            self.connected = False

    def _receive_telemetry(self):
        """Read one MAVLink message and update state cache."""
        if self.mav is None:
            return

        msg = self.mav.recv_match(blocking=True, timeout=1.0)
        if msg is None:
            return

        msg_type = msg.get_type()

        with self._lock:
            if msg_type == 'ATTITUDE':
                self._roll = msg.roll
                self._pitch = msg.pitch
                self._yaw = msg.yaw

            elif msg_type == 'VFR_HUD':
                self._heading = msg.heading

            elif msg_type == 'SCALED_PRESSURE2':
                # Bar30 depth sensor — convert pressure to depth
                # Depth in metres = (pressure_mbar - surface_pressure) / (density * gravity)
                # Simplified: 1 mbar ≈ 0.01019 metres of seawater
                self._depth = -(msg.press_abs - 1013.25) * 0.01019

            elif msg_type == 'BATTERY_STATUS':
                if msg.voltages[0] != 65535:
                    self._battery_voltage = msg.voltages[0] / 1000.0

            elif msg_type == 'HEARTBEAT':
                self._armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                self._mode = mavutil.mode_string_v10(msg)
            elif msg_type == 'HEARTBEAT':
                self._armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                self._mode = mavutil.mode_string_v10(msg)

    def publish_state(self):
        """Read state cache and publish VehicleState — called at 2Hz by timer."""
        msg = VehicleState()
        msg.stamp = self.get_clock().now().to_msg()

        with self._lock:
            msg.mode = self._mode
            msg.armed = self._armed
            msg.depth = self._depth
            msg.battery_voltage = self._battery_voltage
            msg.roll = self._roll
            msg.pitch = self._pitch
            msg.yaw = self._yaw
            msg.heading = float(self._heading)

        self.state_pub.publish(msg)

    def publish_heartbeat(self):
        """Publish connection status — called at 1Hz by timer."""
        msg = Bool()
        msg.data = self.connected
        self.heartbeat_pub.publish(msg)

    def command_callback(self, msg: VehicleCommand):
        """Receive LLM command and send RC override to ArduSub."""
        if not self.connected or self.mav is None:
            self.get_logger().warn('Command received but not connected to MAVLink — ignoring')
            return

        self.get_logger().info(f'Executing command: {msg.action} speed={msg.speed}')

        # Map action to RC channel overrides
        # Channel 3 = throttle (vertical), Channel 4 = yaw
        # Channel 5 = forward/backward, Channel 6 = lateral
        # PWM range: 1100 (full reverse) to 1900 (full forward), 1500 = stop
        pwm_neutral = 1500
        pwm_range = 400  # 1500 ± 400

        channels = [pwm_neutral] * 18  # all channels neutral by default

        speed_factor = max(0.0, min(1.0, msg.speed if msg.speed > 0 else 0.5))
        pwm_value = int(pwm_neutral + (pwm_range * speed_factor))
        pwm_reverse = int(pwm_neutral - (pwm_range * speed_factor))

        if msg.action == 'descend':
            channels[2] = pwm_reverse  # channel 3 (index 2)
        elif msg.action == 'ascend':
            channels[2] = pwm_value
        elif msg.action == 'move_forward':
            channels[4] = pwm_value    # channel 5 (index 4)
        elif msg.action == 'move_backward':
            channels[4] = pwm_reverse
        elif msg.action == 'rotate_left':
            channels[3] = pwm_reverse  # channel 4 (index 3)
        elif msg.action == 'rotate_right':
            channels[3] = pwm_value
        elif msg.action == 'hold':
            pass  # all channels remain neutral
        elif msg.action == 'surface':
            channels[2] = pwm_value    # full ascent

        self.mav.mav.rc_channels_override_send(
            self.mav.target_system,
            self.mav.target_component,
            *channels[:8]
        )


def main(args=None):
    rclpy.init(args=args)
    node = MavlinkNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
