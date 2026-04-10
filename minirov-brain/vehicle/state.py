from dataclasses import dataclass, field, asdict
from datetime import datetime
import time
import threading
from vehicle.mavlink_client import MAVLinkClient

@dataclass
class VehicleState:
    armed: bool = False
    depth: float = 0.0
    battery_voltage: float = 0.0
    mode: str = "MANUAL"
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    heading: float = 0.0
    last_updated : datetime = field(default_factory=datetime.now) # A timestamp so you can detect stale state. 

# The LLM is reading natural language, not parsing data structures. An f string will read as natural language
    def get_summary(self) -> str:
        return (f"Mode: {self.mode}, Armed: {self.armed}, Depth: {self.depth:.1f}m, Battery: {self.battery_voltage:.2f}V, "
                f"Roll: {self.roll:.1f}°, Pitch: {self.pitch:.1f}°, Yaw: {self.yaw:.1f}°, Heading: {self.heading:.1f}°")
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def start(self, client: MAVLinkClient):
        self._client = client
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    def _update_loop(self):
        while True:
            self.update(self._client)
            time.sleep(0.5)  # update every 500ms

    def update(self, client: MAVLinkClient):
        armed = client.get_armed_status()
        if armed is not None:
            client.last_heartbeat = datetime.now()  # update watchdog timestamp
            # print(f"Armed status update: {'Armed' if armed else 'Disarmed'}")
            self.armed = armed
        
        self.mode = client.get_mode() or self.mode
        mode = client.get_mode()
        if mode is not None:
            self.mode = mode

        depth = client.get_depth()
        if depth is not None:
            # print(f"Depth update: {depth:.2f}m")
            self.depth = depth
            
        battery_voltage = client.get_battery_voltage()
        if battery_voltage is not None:
            # print(f"Battery voltage update: {battery_voltage:.2f}V")
            self.battery_voltage = battery_voltage

        attitude = client.get_attitude()
        if attitude is not None:
            # print(f"Attitude update: Roll={attitude['roll']:.1f}°, Pitch={attitude['pitch']:.1f}°, Yaw={attitude['yaw']:.1f}°")
            self.roll = attitude['roll']
            self.pitch = attitude['pitch']
            self.yaw = attitude['yaw']

        self.last_updated = datetime.now()