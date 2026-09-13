import os
import socket

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000").rstrip("/")
AGENT_HOSTNAME = os.getenv("AGENT_HOSTNAME") or socket.gethostname()
ENROLLMENT_KEY = os.getenv("ENROLLMENT_KEY", "dev-enrollment-key")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "5"))
SESSION_ENABLED = os.getenv("SESSION_ENABLED", "true").lower() in {"1", "true", "yes"}
STATE_FILE = os.getenv("AGENT_STATE_FILE", "agent_state.json")
AGENT_VERSION = "2.0.0"
