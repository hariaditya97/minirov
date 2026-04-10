# minirov

A tethered underwater ROV with LLM-assisted supervised autonomy, built for UK coastal and lake shore deployments.

ArduSub on a  Navigator handles low-level stabilisation. A locally-hosted LLM (Ollama) running on a Mac interprets natural language commands and executes them via MAVLink. The operator retains full manual override at all times.

## System

M4 Pro (Ollama + minirov-brain) → 50m tether → Raspberry Pi 5 → Navigator + ArduSub → 4× T200 thrusters

## Status

**Phase 0 complete** — full LLM → MAVLink pipeline working against ArduSub SITL.

Natural language command → Ollama (qwen2.5:14b) → structured JSON → pymavlink → ArduSub SITL → thruster RC override confirmed.

Pending: hardware acquisition, bench build, pool testing, field deployment.

## Phases

- **0** ✅ Software foundations and SITL simulation
- **1** Electronics bench build
- **2** Enclosure and frame assembly
- **3** Pool and tank testing
- **4** Field deployment

## Phases

- **0** — Software foundations and simulation
- **1** — Electronics bench build
- **2** — Enclosure and frame assembly  
- **3** — Pool and tank testing
- **4** — Field deployment

## Author

Hari Aditya