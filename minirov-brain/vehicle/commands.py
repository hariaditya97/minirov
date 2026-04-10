from vehicle.mavlink_client import MAVLinkClient
from config import MODE_DEPTH_HOLD, MODE_MANUAL, MODE_STABILIZE, RC_NEUTRAL, RC_MIN, RC_MAX, RC_CHANNEL_THROTTLE, RC_CHANNEL_YAW, RC_CHANNEL_FORWARD

class VehicleController:
    def __init__(self, mavlink_client: MAVLinkClient):
        self.client = mavlink_client
    
    def hold(self):
        self.client.set_mode(MODE_DEPTH_HOLD)
    
    def ascend(self, speed: float):
       self.client.send_rc_override({RC_CHANNEL_THROTTLE: self._speed_to_rc(speed, reverse=False)}) # throttle channel

    def descend(self, speed: float):
        self._preflight()
        self.client.send_rc_override({RC_CHANNEL_THROTTLE: self._speed_to_rc(speed, reverse=True)}) # reverse throttle channel

    def move_forward(self, speed: float):
        self.client.send_rc_override({RC_CHANNEL_FORWARD: self._speed_to_rc(speed, reverse=False)}) # forward channel

    def move_backward(self, speed: float):
        self.client.send_rc_override({RC_CHANNEL_FORWARD: self._speed_to_rc(speed, reverse=True)}) # reverse forward channel

    def rotate(self, direction: str, speed: float):
        if direction == "left":
            self.client.send_rc_override({RC_CHANNEL_YAW: self._speed_to_rc(speed, reverse=True)}) # yaw channel
        else:
            self.client.send_rc_override({RC_CHANNEL_YAW: self._speed_to_rc(speed, reverse=False)}) # yaw channel

    def surface(self):
        self.client.set_mode(MODE_MANUAL)  # no PID interference
        self.client.send_rc_override({RC_CHANNEL_THROTTLE: self._speed_to_rc(1.0, reverse=False)})

    def _preflight(self):
        if self.client.get_mode() != MODE_STABILIZE:
            self.client.set_mode(MODE_STABILIZE)
        if not self.client.get_armed_status():
            self.client.arm()

    def execute_action(self, response: str):
        import json
        action = json.loads(response)
        actions = {
            "hold":         lambda: self.hold(),
            "ascend":       lambda: self.ascend(action["speed"]),
            "descend":      lambda: self.descend(action["speed"]),
            "move_forward": lambda: self.move_forward(action["speed"]),
            "move_backward": lambda: self.move_backward(action["speed"]),
            "rotate":       lambda: self.rotate(action["direction"], action["speed"]),
            "surface":      lambda: self.surface()
        }
        if action["action"] in actions:
            actions[action["action"]]()
        else:
            print(f"Unknown action: {action['action']}")
        
    def _speed_to_rc(self, speed: float, reverse: bool = False) -> int:
        # Convert speed (-1.0 to 1.0) to RC value (1100 to 1900)
        if reverse:
            speed = -speed
        rc_value = int(RC_NEUTRAL + speed * (RC_MAX - RC_NEUTRAL))
        return max(RC_MIN, min(RC_MAX, rc_value))
    
