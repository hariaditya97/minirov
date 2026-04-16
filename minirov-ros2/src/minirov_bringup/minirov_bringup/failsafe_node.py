# Monitors system health and enforces the miniROV failsafe hierarchy.

import threading
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from minirov_msgs.msg import VehicleState, VehicleCommand, LLMObservation


# Thresholds (seconds)
HEARTBEAT_WARNING_TIMEOUT  = 5.0
HEARTBEAT_CRITICAL_TIMEOUT = 10.0
OPERATOR_INACTIVITY_TIMEOUT = 60.0

# Failsafe levels
LEVEL_OK       = "OK"
LEVEL_DEGRADED = "DEGRADED"
LEVEL_WARNING  = "WARNING"
LEVEL_CRITICAL = "CRITICAL"


class FailsafeNode(Node):

    def __init__(self):
        super().__init__("failsafe_node")

        # ── State ──────────────────────────────────────────────────────────
        self._last_heartbeat    = time.time()
        self._last_llm_activity = time.time()
        self._last_operator_activity = time.time()
        self._current_level     = LEVEL_OK
        self._lock              = threading.Lock()

        # ── Subscriptions ──────────────────────────────────────────────────
        self.create_subscription(
            VehicleState, "/minirov/vehicle_state",
            self._on_vehicle_state, 10)

        self.create_subscription(
            LLMObservation, "/minirov/observations",
            self._on_observation, 10)

        self.create_subscription(
            String, "/minirov/user_input",
            self._on_user_input, 10)

        self.create_subscription(
            String, "/minirov/system_status",
            self._on_system_status, 10)

        # ── Publishers ─────────────────────────────────────────────────────
        self._commands_pub       = self.create_publisher(
            VehicleCommand, "/minirov/commands", 10)
        self._observations_pub   = self.create_publisher(
            LLMObservation, "/minirov/observations", 10)
        self._failsafe_status_pub = self.create_publisher(
            String, "/minirov/failsafe_status", 10)

        # ── Watchdog timer — runs every second ─────────────────────────────
        self.create_timer(1.0, self._watchdog)

        self.get_logger().info("failsafe_node started")

    # ── Subscription callbacks ─────────────────────────────────────────────

    def _on_vehicle_state(self, msg):
        """Any VehicleState message = MAVLink is alive."""
        with self._lock:
            self._last_heartbeat = time.time()

    def _on_observation(self, msg):
        """Not used for logic — just keeps track of LLM activity."""
        with self._lock:
            self._last_llm_activity = time.time()

    def _on_user_input(self, msg):
        """Reset operator inactivity timer on any input."""
        with self._lock:
            self._last_operator_activity = time.time()

    def _on_system_status(self, msg):
        """Receive health reports from other nodes (future use)."""
        self.get_logger().debug(f"system_status: {msg.data}")

    # ── Watchdog ───────────────────────────────────────────────────────────

    def _watchdog(self):
        now = time.time()

        with self._lock:
            heartbeat_age  = now - self._last_heartbeat
            operator_age   = now - self._last_operator_activity

        # ── Level 3 / 4 — Critical: heartbeat lost > 10s ──────────────────
        if heartbeat_age > HEARTBEAT_CRITICAL_TIMEOUT:
            if self._current_level != LEVEL_CRITICAL:
                self._escalate_to_critical(heartbeat_age)
            return

        # ── Level 2 — Warning: heartbeat lost 5–10s ───────────────────────
        if heartbeat_age > HEARTBEAT_WARNING_TIMEOUT:
            if self._current_level not in (LEVEL_WARNING, LEVEL_CRITICAL):
                self._escalate_to_warning(heartbeat_age)
            return

        # ── Level 4 — Emergency: operator inactive > 60s ──────────────────
        if operator_age > OPERATOR_INACTIVITY_TIMEOUT:
            if self._current_level == LEVEL_OK:
                self._operator_timeout(operator_age)

        # ── Recovery: heartbeat restored ──────────────────────────────────
        if self._current_level in (LEVEL_WARNING, LEVEL_CRITICAL):
            self._recover()

    # ── Escalation handlers ────────────────────────────────────────────────

    def _escalate_to_warning(self, age):
        self._current_level = LEVEL_WARNING
        msg = f"MAVLink heartbeat lost for {age:.1f}s — commands frozen"
        self.get_logger().warn(msg)
        self._publish_observation(msg, severity="WARNING")
        self._publish_status(LEVEL_WARNING)

    def _escalate_to_critical(self, age):
        self._current_level = LEVEL_CRITICAL
        msg = f"MAVLink heartbeat lost for {age:.1f}s — sending DISARM"
        self.get_logger().error(msg)
        self._publish_observation(msg, severity="CRITICAL")
        self._publish_disarm()
        self._publish_status(LEVEL_CRITICAL)

    def _operator_timeout(self, age):
        msg = f"Operator inactive for {age:.0f}s — pending command auto-rejected"
        self.get_logger().warn(msg)
        self._publish_observation(msg, severity="WARNING")
        self._publish_status(LEVEL_DEGRADED)

    def _recover(self):
        self._current_level = LEVEL_OK
        msg = "MAVLink heartbeat restored — system nominal"
        self.get_logger().info(msg)
        self._publish_observation(msg, severity="INFO")
        self._publish_status(LEVEL_OK)

    # ── Publish helpers ────────────────────────────────────────────────────

    def _publish_disarm(self):
        cmd = VehicleCommand()
        cmd.action       = "disarm"
        cmd.speed        = 0.0
        cmd.direction    = "none"
        cmd.duration_sec = 0
        cmd.reasoning    = "failsafe_node: heartbeat lost"
        cmd.safety_note  = "automatic DISARM — restore MAVLink before resuming"
        cmd.header.stamp = self.get_clock().now().to_msg()
        self._commands_pub.publish(cmd)
        self.get_logger().error("DISARM command published")

    def _publish_observation(self, text, severity="WARNING"):
        msg = LLMObservation()
        msg.observation = f"[FAILSAFE] {text}"
        msg.recommended_action = ""
        msg.severity = severity
        msg.stamp = self.get_clock().now().to_msg()
        self._observations_pub.publish(msg)

    def _publish_status(self, level):
        msg = String()
        msg.data = level
        self._failsafe_status_pub.publish(msg)


# ── Entry point ────────────────────────────────────────────────────────────

def main(args=None):
    rclpy.init(args=args)
    node = FailsafeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()