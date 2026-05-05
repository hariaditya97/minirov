# minirov — Roadmap

## Current Status

Phase 0 complete. Phase 1 in progress.

Full LLM → MAVLink pipeline verified against ArduSub SITL.
Pico 2W flight controller in active development.

---

## Phase 0 — Software Foundations ✅

- MAVLink client with heartbeat watchdog and connection safety
- Live vehicle state with background telemetry update loop
- High-level vehicle command layer with preflight arming
- LLM system prompts for command interpretation and vision analysis
- Ollama HTTP client with persistent conversation history
- Operator loop with LLM confirmation gate
- Dedicated mission logger 
- ArduSub SITL integration verified end-to-end

---

## Phase 1 — Bench Build 🔄

Two parallel tracks, both must be complete before Phase 2.

**Track A — Pico flight controller**
- IMU (GY-521 MPU-6050) attitude estimation — verified in simulation
- Complementary filter (roll + pitch) — verified in simulation
- PWM output to ESCs — verified in simulation
- Four-thruster mixer
- Serial command input from ROS 2 (Lenovo)
- State machine with FAILSAFE mode
- Hardware validation on physical Pico + GY-521

**Track B — Software stack integration**
- Lenovo running Ubuntu 24.04 + ROS 2 Jazzy
- ROS 2 nodes communicating with minirov-brain on Mac
- Serial bridge between ROS 2 and Pico FC
- End-to-end bench test: Mac → Lenovo → Pico → ESC signal confirmed

---

## Phase 2 — Vehicle Build

- Frame designed and fabricated
- Blue Robotics 4" enclosure with cable penetrators
- Vacuum test passed
- T200 thrusters mounted and bench tested
- Full system integration — all components in final configuration 
- Safety checks

---

## Phase 3 — Pool Testing

- Operator checks prior to deployment
- Neutral buoyancy achieved
- Flight controller tuned in water
- LLM commands executing on real vehicle
- Safety and functional test checklist completed
- Camera stream assessed

---

## Phase 4 — Field Deployment

- Calm water lake deployment
- Natural language mission execution
- Vision pipeline on real underwater frames

---

## Future

- Kalman filter replacing complementary filter
- MAVLink protocol replacing serial JSON
- Mission planner with LLM step generation
- Depth hold with Bar30
- v2 vehicle with improved frame and enclosure