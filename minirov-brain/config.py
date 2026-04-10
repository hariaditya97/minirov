# This file contains all the configuration constants for the miniROV

# ─── Network ───────────────────────────────────────────────────────────────
SURFACE_IP = "192.168.2.1"       # M4Pro MacBook
ROV_IP     = "192.168.2.2"       # Raspberry Pi 5

MAVLINK_UDP_PORT  = 14550        # QGroundControl + rov-brain
MAVLINK_UDP_PORT2 = 14551        # Secondary MAVLink output
CAMERA_UDP_PORT   = 5600         # GStreamer H264 stream

# ─── MAVLink ───────────────────────────────────────────────────────────────
MAVLINK_CONNECTION = "udp:0.0.0.0:14550"
MAVLINK_BAUD       = 115200
HEARTBEAT_TIMEOUT  = 5           # seconds before declaring connection lost

# ─── Vehicle limits ────────────────────────────────────────────────────────
MAX_DEPTH_M        = 45.0        # LLM hard limit — never command below this
MAX_SPEED          = 0.8         # LLM hard limit in confined spaces
BATTERY_CUTOFF_V   = 14.0        # Surface if voltage drops to this
BATTERY_WARNING_V  = 14.4        # Warn operator at this voltage

# ─── RC channel mapping ────────────────────────────────────────────────────
RC_NEUTRAL  = 1500               # Stopped
RC_MIN      = 1100               # Full reverse
RC_MAX      = 1900               # Full forward

RC_CHANNEL_PITCH   = 1
RC_CHANNEL_ROLL    = 2
RC_CHANNEL_THROTTLE = 3          # Heave (up/down)
RC_CHANNEL_YAW     = 4
RC_CHANNEL_FORWARD = 5          # Surge (forward/back)
RC_CHANNEL_LATERAL = 6          # Sway (left/right)
RC_CHANNEL_AUX1   = 7           # Unused
RC_CHANNEL_AUX2   = 8           # Unused

# ─── Flight modes ──────────────────────────────────────────────────────────
MODE_MANUAL     = "MANUAL"
MODE_STABILIZE  = "STABILIZE"
MODE_DEPTH_HOLD = "DEPTH_HOLD"
MODE_AUTO       = "AUTO"

# ─── Ollama ────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL      = "http://localhost:11434"
OLLAMA_COMMAND_MODEL = "qwen2.5:14b"
OLLAMA_VISION_MODEL  = "llama3.2-vision:11b"
OLLAMA_TIMEOUT       = 30        # seconds before giving up on LLM response

# ─── Camera ────────────────────────────────────────────────────────────────
CAMERA_WIDTH   = 1920
CAMERA_HEIGHT  = 1080
CAMERA_FPS     = 30
CAMERA_BITRATE = 2000000         # 2 Mbps H264

# ─── Logging ───────────────────────────────────────────────────────────────
LOG_DIR      = "logs"
LOG_LEVEL    = "INFO"