# minirov Roadmap

## Current status
Phase 0 complete — full LLM to MAVLink pipeline working against ArduSub SITL.

## Phase 0 — Software foundations ✅
- MAVLink client with heartbeat watchdog and connection safety
- Live vehicle state with background telemetry update loop
- High-level vehicle command layer with preflight arming
- LLM system prompts for command interpretation and vision analysis
- Ollama HTTP client with persistent conversation history
- Operator loop with LLM confirmation gate
- ArduSub SITL integration verified end-to-end

## Phase 1 — Electronics bench build
- Raspberry Pi 5 running Raspberry Pi OS Lite
- Pixhawk 4 Mini flashed with ArduSub firmware
- MAVProxy running on Pi, forwarding MAVLink to Mac
- minirov-brain connecting to real Pi over ethernet
- Camera streaming Pi to Mac via GStreamer
- Bar30 depth sensor verified over I2C
- All systems communicating on bench, dry

## Phase 2 — Enclosure and frame assembly
- Blue Robotics 4" enclosure housing Pi + Pixhawk
- Cable penetrators installed and vacuum tested
- Frame assembled with thruster mounts
- T200 thrusters wired and bench tested
- Full vacuum test passed at −10 inHg for 15 minutes

## Phase 3 — Pool and tank testing
- Neutral buoyancy achieved with foam and trim weights
- ArduSub PID tuned in STABILIZE and DEPTH_HOLD modes
- LLM commands executing in real water
- Camera stream quality assessed
- Full battery discharge cycle measured

## Phase 4 — Field deployment
- Lake deployment (calm water, controlled access)
- Natural language mission execution logged
- Vision model analysing real underwater frames
- Coastal deployment

## Future directions
- ROS 2 refactor of minirov-brain middleware
- Mission planner with LLM step generation
- LoRA fine-tuning on logged command/response pairs
- Hybrid buoyancy-thruster vehicle (v2)
- Full autonomy mode with operator supervision only at mission level