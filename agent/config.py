import os
import socket

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8080")
AGENT_HOSTNAME = os.getenv("AGENT_HOSTNAME", socket.gethostname() or "default-hostname")
