# Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project uses [semantic versioning](https://semver.org/).

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