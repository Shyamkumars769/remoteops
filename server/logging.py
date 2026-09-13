import logging
import sys

from server.config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

server_logger = logging.getLogger("remoteops.server")
agents_logger = logging.getLogger("remoteops.agents")
tasks_logger = logging.getLogger("remoteops.tasks")
sessions_logger = logging.getLogger("remoteops.sessions")
auth_logger = logging.getLogger("remoteops.auth")
