import requests
import base64
from config import OLLAMA_COMMAND_MODEL, OLLAMA_VISION_MODEL, OLLAMA_BASE_URL, OLLAMA_TIMEOUT
from llm.prompts import COMMAND_SYSTEM_PROMPT, VISION_SYSTEM_PROMPT
from vehicle.state import VehicleState


class OllamaClient:
    def __init__(self, environment: str):
        self.environment = environment
        self.chat_history = []
        self.model_name = OLLAMA_COMMAND_MODEL

    def chat(self, user_message: str, vehicle_state: VehicleState) -> dict:
        formatted_system_prompt = COMMAND_SYSTEM_PROMPT.format(
            environment=self.environment,
            vehicle_state=vehicle_state.get_summary()
        )
        messages = [
            {"role": "system", "content": formatted_system_prompt},
            *self.chat_history,
            {"role": "user", "content": user_message}
        ]
        self.chat_history.append({"role": "user", "content": user_message})
        response = self.post_message(messages)
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def post_message(self, messages: list) -> str:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": self.model_name,
                "messages": messages,
                "stream": False
            },
            timeout=OLLAMA_TIMEOUT
        )
        return response.json()['message']['content'] 
    

    def post_vision(self, frame_bytes: bytes) -> dict:
        img_b64 = base64.b64encode(frame_bytes).decode('utf-8')
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_VISION_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": VISION_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": "Analyse this frame",
                        "images": [img_b64]
                    }
                ],
                "stream": False
            },
            timeout=OLLAMA_TIMEOUT
        )
        return response.json()['message']['content']
    
    def vision(self, frame_bytes: bytes) -> dict:
        vision_response = self.post_vision(frame_bytes)
        # base64 encode frame, POST to vision model, return dict
        return vision_response
    
    def reset_chat_history(self):
        self.chat_history = []