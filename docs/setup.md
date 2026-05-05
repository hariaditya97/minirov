# Setup Guide

## Topside (Mac)

Requires: Python 3.11+, Ollama

\```bash
ollama pull qwen2.5:14b
cd software/minirov-brain
pip install -r requirements.txt
\```

## Middleware (Lenovo — Ubuntu 24.04)

\```bash
sudo apt install ros-jazzy-desktop
source /opt/ros/jazzy/setup.bash
\```

## SITL

Requires: ArduSub SITL installed and on PATH.

\```bash
sim_vehicle.py -v ArduSub --console --map
python software/minirov-brain/main.py --sitl
\```

## Pico Flight Controller

Requires: mpremote

\```bash
pip install mpremote
mpremote cp software/pico-fc/src/imu.py :imu.py
mpremote cp software/pico-fc/src/attitude.py :attitude.py
mpremote cp software/pico-fc/src/controller.py :controller.py
mpremote cp software/pico-fc/src/main.py :main.py
\```

Full Wokwi simulation: see \`software/pico-fc/sim/\`