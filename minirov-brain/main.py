from llm.ollama_client import OllamaClient
from vehicle.commands import VehicleController
from vehicle.mavlink_client import MAVLinkClient
from vehicle.state import VehicleState
from logs.mission_logger import MissionLogger
from ui.operator import display_llm_response
import json


miniROV = VehicleState()
print("Vehicle state monitoring started...")
mavlink_connection = MAVLinkClient() # Start monitoring in a separate thread
miniROV.start(mavlink_connection) 
print("✓ MAVLink connected — heartbeat received. Receiving telemetry updates...") 
miniROV.update(mavlink_connection)  # Initial update to populate state
print(f"✓ Initial vehicle state populated — \n{miniROV.get_summary()}\n")
command_controller = VehicleController(mavlink_connection)
print("✓ Vehicle controller ready")
ollama = OllamaClient("testing")
print("✓ Ollama client ready")
session_name = None
session_description = None

try: 
    while True:
        if session_name is None:
            session_name = input("Enter session name: ")
            session_description = input("Enter mission description: ")
            logger = MissionLogger(session_name, session_description)
        logger.log_state(miniROV)  # Log initial state at the start of the session
        cmd = input("Enter a command: > ")
        print(f"_ONLY Vehicle state: {miniROV.get_summary()}")
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
        logger.log_command(cmd, parsed, confirm == "y")
except KeyboardInterrupt:
    print("Shutting down...")
    logger.close()
    mavlink_connection.disarm()