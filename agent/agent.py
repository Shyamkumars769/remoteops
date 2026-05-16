import socket
import time
from typing import Any

import requests

from agent import config
from agent.logging import agent_logger, task_logger
from agent.modules.executor import run_command
from agent.modules.filesystem import list_directory
from agent.modules.process import kill_process, list_processes
from agent.modules.system_info import collect_system_info


class Agent:
    def __init__(self, server_url: str | None = None, hostname: str | None = None) -> None:
        self.server_url = (server_url or config.SERVER_URL).rstrip("/")
        self.hostname   = hostname or config.AGENT_HOSTNAME or socket.gethostname()
        self.agent_id: str | None = None
        self.token: str | None    = None

    def register(self) -> None:
        response = requests.post(
            f"{self.server_url}/api/register",
            json={"hostname": self.hostname},
            timeout=10,
        )
        response.raise_for_status()
        data           = response.json()
        self.agent_id  = data["agent_id"]
        self.token     = data["token"]
        agent_logger.info("Registered agent_id=%s hostname=%s", self.agent_id, self.hostname)

    def get_next_task(self) -> dict[str, Any] | None:
        if not self.agent_id or not self.token:
            return None

        response = requests.get(
            f"{self.server_url}/api/tasks/{self.agent_id}",
            params={"token": self.token},
            timeout=10,
        )
        response.raise_for_status()
        task = response.json()
        if not task:
            return None
        task_logger.info("Received task_id=%s type=%s", task.get("task_id"), task.get("type"))
        return task

    def execute_task(self, task: dict[str, Any]) -> dict[str, Any]:
        started   = time.perf_counter()
        task_id   = task.get("task_id")
        task_type = task.get("type")
        payload   = task.get("payload") or {}

        try:
            # -------------------------------------------------------- #
            #  KNOWN TASK TYPES
            # -------------------------------------------------------- #
            if task_type == "system_info":
                result = collect_system_info()

            elif task_type == "run_command":
                result = run_command(str(payload.get("command", "")))

            elif task_type == "list_files":
                result = list_directory(str(payload.get("path", ".")))

            elif task_type == "list_processes":
                result = list_processes()

            elif task_type == "kill_process":
                result = kill_process(int(payload["pid"]))

            else:
                # ---------------------------------------------------- #
                #  FREE FORM — any unknown task type runs as a command
                #  Priority:
                #  1. payload has "command" key → use that
                #  2. otherwise → use task_type itself as the command
                # ---------------------------------------------------- #
                command = payload.get("command") or task_type
                task_logger.info(
                    "Free-form task task_id=%s running command: %s", task_id, command
                )
                result = run_command(str(command))

            latency_ms = int((time.perf_counter() - started) * 1000)
            status     = "error" if result.get("error_message") else "success"
            task_logger.info(
                "Executed task_id=%s type=%s status=%s latency=%sms",
                task_id, task_type, status, latency_ms
            )
            return {
                "task_id"   : task_id,
                "agent_id"  : self.agent_id,
                "status"    : status,
                "type"      : task_type,
                "latency_ms": latency_ms,
                "result"    : {**result, "latency_ms": latency_ms},
            }

        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            task_logger.exception("Task failed task_id=%s type=%s", task_id, task_type)
            return {
                "task_id"   : task_id,
                "agent_id"  : self.agent_id,
                "status"    : "error",
                "type"      : task_type,
                "latency_ms": latency_ms,
                "result"    : {"error_message": str(exc), "latency_ms": latency_ms},
            }

    def send_result(self, result: dict[str, Any]) -> None:
        response = requests.post(
            f"{self.server_url}/api/results",
            json=result,
            timeout=10
        )
        response.raise_for_status()
        task_logger.info(
            "Sent result task_id=%s status=%s",
            result.get("task_id"), result.get("status")
        )

    def run(self, poll_interval: float = 5.0) -> None:
        agent_logger.info(
            "Agent starting server_url=%s hostname=%s",
            self.server_url, self.hostname
        )
        while True:
            try:
                if not self.token:
                    self.register()
                task = self.get_next_task()
                if task:
                    self.send_result(self.execute_task(task))
            except requests.RequestException as exc:
                agent_logger.error("Network error: %s", exc)
                self.token = None
            except Exception as exc:
                agent_logger.exception("Unexpected agent error: %s", exc)
            time.sleep(poll_interval)


if __name__ == "__main__":
    Agent().run()