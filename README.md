# minirov

A tethered underwater ROV with LLM-assisted supervised autonomy,
built for UK coastal and lake shore deployments.

A locally-hosted LLM (Ollama / qwen2.5:14b) running on an M4 Pro
Mac interprets natural language commands and executes them via
ROS 2 middleware. The operator retains full manual override
at all times.

---

## System Architecture

\
M4 Pro — Ollama + minirov-brain (operator interface)
        │
        │  ROS 2 over network
        │
Lenovo Ubuntu — ROS 2 Jazzy (serial bridge)
        │
        │  JSON over USB serial
        │
Pico 2W — custom flight controller (IMU + attitude + PWM)
        │
4× T200 thrusters
\

---

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Software foundations and SITL | ✅ Complete |
| 1 | Bench build and electronics | 🔄 In progress |
| 2 | Enclosure and frame assembly | 🔲 Pending |
| 3 | Pool and tank testing | 🔲 Pending |
| 4 | Field deployment | 🔲 Pending |

**Phase 0:** Full LLM → MAVLink pipeline verified against ArduSub SITL.
Natural language → Ollama (qwen2.5:14b) → JSON → pymavlink → 
ArduSub SITL → thruster RC override confirmed.

**Phase 1 (current):** Pico 2W flight controller in development.

---

## Hardware

| Component | Part |
|-----------|------|
| Topside compute | Apple M4 Pro MacBook |
| Middleware | Lenovo laptop — Ubuntu 24.04, ROS 2 Jazzy |
| Flight controller | Raspberry Pi Pico 2W (custom firmware) |
| IMU | GY-521 MPU-6050 |
| Thrusters | 4× Blue Robotics T200 |
| ESCs | Blue Robotics Basic ESC |
| Tether | Blue Robotics Fathom 50m |
| Tether interface | Blue Robotics Fathom-X ×2 |
| Enclosure | Blue Robotics 4" Watertight (acrylic) |

Full BOM: `docs/hardware/bom.md`

---

## Software Stack

| Layer | Technology |
|-------|------------|
| LLM inference | Ollama / qwen2.5:14b |
| Autonomy brain | Python — minirov-brain |
| Middleware | ROS 2 Jazzy |
| Serial bridge | ROS 2 node — JSON over USB |
| Flight controller | MicroPython — pico-fc |
| SITL comms | pymavlink (simulation only) |

---

## Author

Hari Aditya
[github.com/hariaditya97](https://github.com/hariaditya97)
