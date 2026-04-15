#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime
import rclpy
from rclpy.node import Node
from minirov_msgs.msg import VehicleState, VehicleCommand, LLMResponse, LLMObservation


class LoggerNode(Node):

    def __init__(self):
        super().__init__("logger_node")

        # Mirror mission_logger.py — same db location, same schema
        log_dir = os.path.expanduser("~/minirov/field-logs")
        os.makedirs(log_dir, exist_ok=True)
        session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_path = os.path.join(log_dir, f"{session_name}.db")

        self._conn = sqlite3.connect(db_path)
        self._create_tables()
        self._log_session_start()
        self.get_logger().info(f"Logging to {db_path}")

        self.create_subscription(VehicleState,   "/minirov/vehicle_state", self._on_vehicle_state, 10)
        self.create_subscription(VehicleCommand, "/minirov/commands",      self._on_command,       10)
        self.create_subscription(LLMResponse,    "/minirov/llm_response",  self._on_llm_response,  10)
        self.create_subscription(LLMObservation, "/minirov/observations",  self._on_observation,   10)

    def _create_tables(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                mode TEXT,
                armed INTEGER,
                depth REAL,
                battery_voltage REAL,
                roll REAL,
                pitch REAL,
                yaw REAL,
                heading REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_prompt TEXT,
                action TEXT,
                speed REAL,
                direction TEXT,
                duration_sec INTEGER,
                reasoning TEXT,
                safety_note TEXT,
                executed INTEGER
            )
        """)
        self._conn.commit()

    def _log_session_start(self):
        self._conn.execute("""
            INSERT INTO commands (timestamp, user_prompt, action, reasoning, executed)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), "SESSION_START", "none", "ROS 2 session", 0))
        self._conn.commit()

    def _on_vehicle_state(self, msg):
        self._conn.execute("""
            INSERT INTO states
            (timestamp, mode, armed, depth, battery_voltage, roll, pitch, yaw, heading)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            msg.mode, int(msg.armed), msg.depth, msg.battery_voltage,
            msg.roll, msg.pitch, msg.yaw, msg.heading,
        ))
        self._conn.commit()

    def _on_llm_response(self, msg):
        # LLM proposed — not yet confirmed, executed=0
        self._conn.execute("""
            INSERT INTO commands
            (timestamp, user_prompt, action, speed, direction, duration_sec, reasoning, safety_note, executed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            "llm_proposed", msg.action, msg.speed, msg.direction,
            msg.duration_sec, msg.reasoning, msg.safety_note, 0,
        ))
        self._conn.commit()

    def _on_command(self, msg):
        # Operator confirmed — update the last matching unexecuted row
        self._conn.execute("""
            UPDATE commands SET executed=1
            WHERE action=? AND executed=0
            ORDER BY id DESC LIMIT 1
        """, (msg.action,))
        self._conn.commit()

    def _on_observation(self, msg):
        self._conn.execute("""
            INSERT INTO commands
            (timestamp, user_prompt, action, reasoning, executed)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            "observation", "none", msg.observation, 0,
        ))
        self._conn.commit()

    def destroy_node(self):
        self._conn.close()
        self.get_logger().info("Database closed")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = LoggerNode()
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