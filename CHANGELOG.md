# Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Added
- ROS 2 workspace (`minirov-ros2/`) with two packages:
  - `minirov_msgs` — custom message definitions for `VehicleState` and `VehicleCommand`
  - `minirov_bringup` — ROS 2 nodes package, starting with `mavlink_node`
- `mavlink_node` — bridges MAVLink telemetry from ArduSub to ROS 2 topics
  - Publishes `/minirov/state` (VehicleState) at 2Hz
  - Publishes `/minirov/heartbeat` (std_msgs/Bool) at 1Hz
  - Subscribes to `/minirov/commands` (VehicleCommand) for RC override execution
  - All behaviour configurable via ROS 2 parameters
  - MAVLink connection runs in background thread, non-blocking

### Verified
- `mavlink_node` tested against ArduSub SITL
- Real telemetry confirmed flowing: mode, armed status, battery voltage, attitude, heading
- `/minirov/heartbeat` publishing `true` on successful MAVLink connection
- Custom message types `VehicleState` and `VehicleCommand` building and introspectable via `ros2 interface show`

### Architecture
- ROS 2 workspace now lives in the GitHub repo — safe from VM loss
- VM clones the repo directly, pushes changes to GitHub via SSH


## [Unreleased]

## [v0.1.0] - 2026-04-10

### Added
- MAVLink client with connection management, heartbeat watchdog, and thread safety
- Vehicle state dataclass with live telemetry update loop (depth, attitude, battery, armed status, flight mode)
- Vehicle command layer with preflight arming and automatic mode switching
- LLM system prompts for ROV command interpretation and underwater vision analysis
- Ollama HTTP client with persistent conversation history across a dive session
- Operator control loop with LLM confirmation gate and structured action display
- ArduSub SITL integration — full LLM to MAVLink pipeline verified end-to-end
- GPL v3 licence
- Architecture Decision Records 