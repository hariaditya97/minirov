from llm.ollama_client import OllamaClient
from vehicle.commands import VehicleController
from vehicle.mavlink_client import MAVLinkClient
from vehicle.state import VehicleState
from ui.operator import display_llm_response
import json


miniROV = VehicleState()
# print("Vehicle state monitoring started. Initial state: {}".format(miniROV.get_summary()))
mavlink_connection = MAVLinkClient()
miniROV.start(mavlink_connection)  # Start monitoring in a separate thread
miniROV.update(mavlink_connection)  # Initial update to populate state
command_controller = VehicleController(mavlink_connection)
ollama = OllamaClient("testing")

try: 
    while True:
        cmd = input("> ")
        print(f"DEBUG state: {miniROV.get_summary()}")
        response = ollama.chat(cmd, miniROV)
        parsed = json.loads(response)
        display_llm_response(parsed)
        confirm = input("Execute? (y/n): ")
        if confirm == "y":
            try:
                command_controller.execute_action(response)
            except ConnectionError as e:
                print(f"Error executing command: {e}")
        else:
            print("Command execution cancelled.")
except KeyboardInterrupt:
    print("Shutting down...")
    mavlink_connection.disarm()