import logging
from pathlib import Path


def _build_logger(name: str) -> logging.Logger:
    Path("logs").mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler("logs/server.log")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


server_logger = _build_logger("server")
agents_logger = _build_logger("agents")
tasks_logger = _build_logger("tasks")
