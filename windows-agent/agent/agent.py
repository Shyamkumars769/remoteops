"""RemoteOps agent — task polling + full interactive sessions."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Optional

import requests

from agent import config
from agent.logging import agent_logger, task_logger, session_logger
from agent.modules.executor import run_command
from agent.modules.filesystem import list_directory
from agent.modules.process import kill_process, list_processes
from agent.modules.system_info import collect_system_info
from agent.session_handler import SessionHandler

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore


class Agent:
    def __init__(self) -> None:
        self.server_url = config.SERVER_URL
        self.hostname = config.AGENT_HOSTNAME
        self.agent_id: Optional[str] = None
        self.token: Optional[str] = None
        self._load_state()

    def _state_path(self) -> Path:
        return Path(config.STATE_FILE)

    def _load_state(self) -> None:
        p = self._state_path()
        if p.exists():
            try:
                data = json.loads(p.read_text())
                self.agent_id = data.get("agent_id")
                self.token = data.get("token")
                agent_logger.info("Loaded state agent_id=%s", self.agent_id)
            except Exception:
                pass

    def _save_state(self) -> None:
        p = self._state_path()
        p.write_text(json.dumps({"agent_id": self.agent_id, "token": self.token}))

    def register(self) -> None:
        response = requests.post(
            f"{self.server_url}/api/register",
            json={
                "hostname": self.hostname,
                "enrollment_key": config.ENROLLMENT_KEY,
                "version": config.AGENT_VERSION,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        self.agent_id = data["agent_id"]
        self.token = data["token"]
        self._save_state()
        agent_logger.info("Registered agent_id=%s hostname=%s", self.agent_id, self.hostname)

    def get_next_task(self) -> dict[str, Any] | None:
        if not self.agent_id or not self.token:
            return None
        response = requests.get(
            f"{self.server_url}/api/tasks/{self.agent_id}",
            params={"token": self.token},
            timeout=15,
        )
        response.raise_for_status()
        task = response.json()
        if not task:
            return None
        task_logger.info("Received task_id=%s type=%s", task.get("task_id"), task.get("type"))
        return task

    def execute_task(self, task: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        task_id = task.get("task_id")
        task_type = task.get("type")
        payload = task.get("payload") or {}
        timeout = int(task.get("timeout_seconds") or 300)

        try:
            if task_type == "system_info":
                result = collect_system_info()
            elif task_type == "run_command":
                result = run_command(str(payload.get("command", "")), timeout=timeout)
            elif task_type == "list_files":
                result = list_directory(str(payload.get("path", ".")))
            elif task_type == "list_processes":
                result = list_processes()
            elif task_type == "kill_process":
                result = kill_process(int(payload["pid"]))
            else:
                # Free-form: unrestricted command (kept as requested)
                command = payload.get("command") or task_type
                task_logger.info("Free-form task task_id=%s command=%s", task_id, command)
                result = run_command(str(command), timeout=timeout)

            latency_ms = int((time.perf_counter() - started) * 1000)
            status = "error" if result.get("error_message") else "success"
            return {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "status": status,
                "type": task_type,
                "latency_ms": latency_ms,
                "result": {**result, "latency_ms": latency_ms},
            }
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            task_logger.exception("Task failed task_id=%s", task_id)
            return {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "status": "error",
                "type": task_type,
                "latency_ms": latency_ms,
                "result": {"error_message": str(exc), "latency_ms": latency_ms},
            }

    def send_result(self, result: dict[str, Any]) -> None:
        response = requests.post(f"{self.server_url}/api/results", json=result, timeout=30)
        response.raise_for_status()
        task_logger.info("Sent result task_id=%s status=%s", result.get("task_id"), result.get("status"))

    def check_pending_session(self) -> str | None:
        if not config.SESSION_ENABLED or not self.agent_id or not self.token:
            return None
        try:
            r = requests.get(
                f"{self.server_url}/api/sessions/pending/{self.agent_id}",
                params={"token": self.token},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            return data.get("session_id")
        except Exception as e:
            agent_logger.debug("session poll error: %s", e)
            return None

    async def run_interactive_session(self, session_id: str) -> None:
        if websockets is None:
            session_logger.error("websockets package not installed")
            return

        ws_base = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        uri = f"{ws_base}/api/ws/session/agent/{session_id}?agent_id={self.agent_id}&token={self.token}"
        session_logger.info("Connecting interactive session_id=%s", session_id)

        handler: SessionHandler | None = None

        async def send_fn(msg: dict) -> None:
            await ws.send(json.dumps(msg))

        try:
            async with websockets.connect(uri, max_size=8_000_000) as ws:
                handler = SessionHandler(session_id, send_fn)
                # Auto-start shell
                handler.start_shell()
                await ws.send(json.dumps({"type": "agent_ready"}))

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if msg.get("type") == "session_closed":
                        break
                    reply = handler.handle_message(msg)
                    if reply:
                        await ws.send(json.dumps(reply))
        except Exception as e:
            session_logger.error("Session error session_id=%s: %s", session_id, e)
        finally:
            if handler:
                handler.stop()
            session_logger.info("Session ended session_id=%s", session_id)

    def run(self) -> None:
        agent_logger.info(
            "Agent starting server=%s hostname=%s version=%s",
            self.server_url, self.hostname, config.AGENT_VERSION,
        )
        backoff = config.POLL_INTERVAL

        while True:
            try:
                if not self.token:
                    self.register()
                    backoff = config.POLL_INTERVAL

                # Prefer interactive session if one is pending
                sid = self.check_pending_session()
                if sid:
                    asyncio.run(self.run_interactive_session(sid))
                    continue

                task = self.get_next_task()
                if task:
                    self.send_result(self.execute_task(task))
                    backoff = config.POLL_INTERVAL
                else:
                    time.sleep(backoff)
            except requests.RequestException as exc:
                agent_logger.error("Network error: %s", exc)
                self.token = None  # force re-register after revoke/network issues
                backoff = min(backoff * 1.5, 60)
                time.sleep(backoff)
            except Exception as exc:
                agent_logger.exception("Unexpected error: %s", exc)
                time.sleep(backoff)


if __name__ == "__main__":
    Agent().run()
