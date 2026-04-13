"""
mission_logger.py — Session-based mission logging for miniROV operations.

Logs two parallel streams to a SQLite database for post-dive analysis:

    1. states table   — continuous timestamped telemetry written by the
                        background state update loop
    2. commands table — every operator prompt and LLM response, including
                        whether the command was executed or cancelled

Log files are stored in logs/<session_name>.db
"""
import json
import sqlite3
import os
from datetime import datetime
from vehicle.state import VehicleState


class MissionLogger:
    def __init__(self, session_name: str, mission_description: str = ""):
        # Build the file path — logs/ directory, named after the session
        # os.makedirs ensures the logs/ folder exists before we try to create the file
        os.makedirs("logs", exist_ok=True)
        self.db_path = f"logs/{session_name}.db"

        self.session_name = session_name
        self.mission_description = mission_description

        # Open a connection to the SQLite database file
        # SQLite creates the file automatically if it doesn't exist
        self.conn = sqlite3.connect(self.db_path)

        self._create_tables()
        self._log_session_start()

    def _create_tables(self):
        cursor = self.conn.cursor()

        # states table — one row per telemetry snapshot
        # Each column stores one piece of vehicle state as a typed value
        # This makes querying easy — e.g. SELECT * FROM states WHERE depth < -3.0
        cursor.execute("""
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

        # commands table — one row per operator command
        # Stores both the raw operator input and the full LLM response
        # executed = 1 means operator confirmed, 0 means cancelled
        cursor.execute("""
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

        self.conn.commit()

    def _log_session_start(self):
        # Write a record of when this session started and what it's for
        # Stored as a special row in the commands table for reference
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO commands 
            (timestamp, user_prompt, action, reasoning, executed)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            "SESSION_START",
            "none",
            self.mission_description,
            0
        ))
        self.conn.commit()

    def log_state(self, vehicle_state: VehicleState):
        # Called by the background state update loop every 500ms
        # Writes one row to the states table with current telemetry
        # armed is stored as 1 (True) or 0 (False) — SQLite has no boolean type
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO states
            (timestamp, mode, armed, depth, battery_voltage, roll, pitch, yaw, heading)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            vehicle_state.mode,
            int(vehicle_state.armed),
            vehicle_state.depth,
            vehicle_state.battery_voltage,
            vehicle_state.roll,
            vehicle_state.pitch,
            vehicle_state.yaw,
            vehicle_state.heading
        ))
        self.conn.commit()

    def log_command(self, user_prompt: str, llm_response: dict, executed: bool):
        # Called by main.py after every LLM response
        # llm_response is the parsed JSON dict from ollama_client
        # executed=True means operator confirmed with y, False means cancelled
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO commands
            (timestamp, user_prompt, action, speed, direction, 
             duration_sec, reasoning, safety_note, executed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            user_prompt,
            llm_response.get("action"),
            llm_response.get("speed"),
            llm_response.get("direction"),
            llm_response.get("duration_sec"),
            llm_response.get("reasoning"),
            llm_response.get("safety_note"),
            int(executed)
        ))
        self.conn.commit()

    def close(self):
        # Always call this on shutdown to flush and close the database cleanly
        self.conn.close()
        print(f"Mission log saved to {self.db_path}")