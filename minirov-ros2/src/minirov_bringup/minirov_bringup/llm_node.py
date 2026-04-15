#!/usr/bin/env python3
"""
llm_node.py — ROS 2 node providing LLM-assisted supervisory control for miniROV.
"""

import json
import threading
import requests
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import CompressedImage
from minirov_msgs.msg import VehicleState, LLMResponse, LLMObservation

COMMAND_SYSTEM_PROMPT = """You are the AI control system for a miniROV.
Current vehicle state:
{vehicle_state}

Environment context:
{environment}

Respond with valid JSON only:
{{
    "action": "hold|ascend|descend|move_forward|move_backward|rotate_left|rotate_right|surface",
    "speed": 0.0,
    "direction": "",
    "duration_sec": 0,
    "reasoning": "brief explanation",
    "safety_note": "any safety concerns"
}}

Safety rules:
- Never exceed speed 0.8
- Always recommend surfacing if battery below 20%
- Always recommend holding if depth exceeds 50 metres
- If unsafe or unclear, respond with action: hold
"""

MONITOR_SYSTEM_PROMPT = """You are monitoring a miniROV underwater vehicle.
Current vehicle state:
{vehicle_state}

Respond with valid JSON only:
{{
    "observation": "what you notice",
    "recommended_action": "what the operator should consider",
    "severity": "INFO|WARNING|CRITICAL"
}}

Flag WARNING for: battery below 30%, heading drift, depth instability.
Flag CRITICAL for: battery below 20%, depth exceeding limits.
"""

VISION_SYSTEM_PROMPT = """You are analysing a camera frame from a miniROV.
Vehicle state when anomaly detected:
{vehicle_state}

Anomaly detected:
{anomaly}

Respond with valid JSON only:
{{
    "observation": "what you see in the frame",
    "recommended_action": "what the operator should do",
    "severity": "INFO|WARNING|CRITICAL"
}}
"""


class LLMNode(Node):
    def __init__(self):
        super().__init__('llm_node')

        self.declare_parameter('ollama_host', 'http://172.16.52.1:11434')
        self.declare_parameter('ollama_model', 'qwen2.5:14b')
        self.declare_parameter('ollama_vision_model', 'llama3.2-vision:11b')
        self.declare_parameter('monitor_interval', 10.0)
        self.declare_parameter('history_window', 10)

        self.ollama_host = self.get_parameter('ollama_host').get_parameter_value().string_value
        self.model = self.get_parameter('ollama_model').get_parameter_value().string_value
        self.vision_model = self.get_parameter('ollama_vision_model').get_parameter_value().string_value
        self.monitor_interval = self.get_parameter('monitor_interval').get_parameter_value().double_value
        self.history_window = self.get_parameter('history_window').get_parameter_value().integer_value

        self.response_pub = self.create_publisher(LLMResponse, '/minirov/llm_response', 10)
        self.observation_pub = self.create_publisher(LLMObservation, '/minirov/observations', 10)

        self.state_sub = self.create_subscription(
            VehicleState, '/minirov/state', self.state_callback, 10)
        self.input_sub = self.create_subscription(
            String, '/minirov/user_input', self.input_callback, 10)
        self.camera_sub = self.create_subscription(
            CompressedImage, '/minirov/camera', self.camera_callback, 10)

        self._lock = threading.Lock()
        self._latest_state = None
        self._latest_frame = None
        self._chat_history = []
        self._last_battery = 100.0
        self._last_depth = 0.0
        self._last_heading = 0.0
        self._vision_triggered = False

        self.monitor_timer = self.create_timer(self.monitor_interval, self.monitor_callback)

        self.get_logger().info(
            f'llm_node started — model={self.model} host={self.ollama_host}')

    def state_callback(self, msg: VehicleState):
        with self._lock:
            self._latest_state = msg
            self._check_anomalies(msg)

    def camera_callback(self, msg: CompressedImage):
        with self._lock:
            self._latest_frame = msg

    def input_callback(self, msg: String):
        user_prompt = msg.data.strip()
        if not user_prompt:
            return
        self.get_logger().info(f'Operator input: {user_prompt}')
        with self._lock:
            state = self._latest_state
        if state is None:
            self.get_logger().warn('No vehicle state available')
            return
        thread = threading.Thread(
            target=self._process_command,
            args=(user_prompt, state),
            daemon=True
        )
        thread.start()

    def _process_command(self, user_prompt: str, state: VehicleState):
        state_summary = self._state_to_string(state)
        system_prompt = COMMAND_SYSTEM_PROMPT.format(
            vehicle_state=state_summary,
            environment='No additional environmental context available.'
        )
        with self._lock:
            history = list(self._chat_history)
        history.append({'role': 'user', 'content': user_prompt})
        try:
            response_text = self._call_ollama(system_prompt, history)
            parsed = json.loads(response_text)
            with self._lock:
                self._chat_history.append({'role': 'user', 'content': user_prompt})
                self._chat_history.append({'role': 'assistant', 'content': response_text})
                max_entries = self.history_window * 2
                if len(self._chat_history) > max_entries:
                    self._chat_history = self._chat_history[-max_entries:]
            msg = LLMResponse()
            msg.stamp = self.get_clock().now().to_msg()
            msg.user_prompt = user_prompt
            msg.action = parsed.get('action', 'hold')
            msg.speed = float(parsed.get('speed', 0.0))
            msg.direction = parsed.get('direction', '')
            msg.duration_sec = int(parsed.get('duration_sec', 0))
            msg.reasoning = parsed.get('reasoning', '')
            msg.safety_note = parsed.get('safety_note', '')
            self.response_pub.publish(msg)
            self.get_logger().info(f'LLM proposed: {msg.action} speed={msg.speed}')
        except json.JSONDecodeError as e:
            self.get_logger().error(f'LLM returned invalid JSON: {e}')
        except Exception as e:
            self.get_logger().error(f'LLM call failed: {e}')

    def monitor_callback(self):
        with self._lock:
            state = self._latest_state
        if state is None:
            return
        thread = threading.Thread(
            target=self._run_monitor,
            args=(state,),
            daemon=True
        )
        thread.start()

    def _run_monitor(self, state: VehicleState):
        state_summary = self._state_to_string(state)
        system_prompt = MONITOR_SYSTEM_PROMPT.format(vehicle_state=state_summary)
        try:
            response_text = self._call_ollama(system_prompt, [])
            parsed = json.loads(response_text)
            msg = LLMObservation()
            msg.stamp = self.get_clock().now().to_msg()
            msg.observation = parsed.get('observation', '')
            msg.recommended_action = parsed.get('recommended_action', '')
            msg.severity = parsed.get('severity', 'INFO')
            self.observation_pub.publish(msg)
            if msg.severity != 'INFO':
                self.get_logger().warn(
                    f'[{msg.severity}] {msg.observation} — {msg.recommended_action}')
        except Exception as e:
            self.get_logger().error(f'Monitor LLM call failed: {e}')

    def _check_anomalies(self, state: VehicleState):
        anomaly = None
        if state.battery_voltage > 0 and state.battery_voltage < 11.0:
            anomaly = f'Battery voltage critical: {state.battery_voltage:.1f}V'
        heading_drift = abs(state.heading - self._last_heading)
        if heading_drift > 30.0 and self._last_heading != 0.0:
            anomaly = f'Heading drift detected: {heading_drift:.1f} degrees'
        depth_change = abs(state.depth - self._last_depth)
        if depth_change > 2.0 and self._last_depth != 0.0:
            anomaly = f'Unexpected depth change: {depth_change:.1f}m'
        self._last_battery = state.battery_voltage
        self._last_depth = state.depth
        self._last_heading = state.heading
        if anomaly and not self._vision_triggered and self._latest_frame is not None:
            self._vision_triggered = True
            thread = threading.Thread(
                target=self._run_vision_analysis,
                args=(state, anomaly),
                daemon=True
            )
            thread.start()

    def _run_vision_analysis(self, state: VehicleState, anomaly: str):
        import base64
        with self._lock:
            frame = self._latest_frame
        if frame is None:
            self._vision_triggered = False
            return
        try:
            state_summary = self._state_to_string(state)
            system_prompt = VISION_SYSTEM_PROMPT.format(
                vehicle_state=state_summary,
                anomaly=anomaly
            )
            image_b64 = base64.b64encode(frame.data.tobytes()).decode('utf-8')
            response = requests.post(
                f'{self.ollama_host}/api/generate',
                json={
                    'model': self.vision_model,
                    'prompt': system_prompt,
                    'images': [image_b64],
                    'stream': False,
                    'format': 'json'
                },
                timeout=30
            )
            response.raise_for_status()
            parsed = json.loads(response.json()['response'])
            msg = LLMObservation()
            msg.stamp = self.get_clock().now().to_msg()
            msg.observation = f'[VISION] {parsed.get("observation", "")}'
            msg.recommended_action = parsed.get('recommended_action', '')
            msg.severity = parsed.get('severity', 'INFO')
            self.observation_pub.publish(msg)
            self.get_logger().info(f'Vision analysis: {msg.observation}')
        except Exception as e:
            self.get_logger().error(f'Vision analysis failed: {e}')
        finally:
            self._vision_triggered = False

    def _call_ollama(self, system_prompt: str, messages: list) -> str:
        payload = {
            'model': self.model,
            'messages': [{'role': 'system', 'content': system_prompt}] + messages,
            'stream': False,
            'format': 'json'
        }
        response = requests.post(
            f'{self.ollama_host}/api/chat',
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()['message']['content']

    def _state_to_string(self, state: VehicleState) -> str:
        return (
            f'Mode: {state.mode}, Armed: {state.armed}, '
            f'Depth: {state.depth:.2f}m, Battery: {state.battery_voltage:.1f}V, '
            f'Roll: {state.roll:.1f}°, Pitch: {state.pitch:.1f}°, '
            f'Yaw: {state.yaw:.1f}°, Heading: {state.heading:.0f}°'
        )


def main(args=None):
    rclpy.init(args=args)
    node = LLMNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
