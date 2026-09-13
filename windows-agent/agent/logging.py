import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

agent_logger = logging.getLogger("remoteops.agent")
task_logger = logging.getLogger("remoteops.agent.task")
session_logger = logging.getLogger("remoteops.agent.session")
