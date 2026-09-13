import os
import signal
from typing import Any

import psutil


def list_processes() -> dict[str, Any]:
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "username"]):
        try:
            info = proc.info
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info.get("name"),
                    "cpu_percent": info.get("cpu_percent"),
                    "memory_percent": info.get("memory_percent"),
                    "username": info.get("username"),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {"processes": processes}


def kill_process(pid: int) -> dict[str, Any]:
    try:
        process = psutil.Process(pid)
        process.terminate()
        try:
            process.wait(timeout=5)
        except psutil.TimeoutExpired:
            os.kill(pid, signal.SIGKILL)
        return {"success": True, "pid": pid}
    except Exception as exc:
        return {"success": False, "pid": pid, "error_message": str(exc)}
