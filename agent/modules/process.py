import os
import signal

import psutil


def list_processes() -> dict:
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info.get("name"),
                    "cpu_percent": info.get("cpu_percent"),
                    "memory_percent": info.get("memory_percent"),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {"processes": processes}


def kill_process(pid: int) -> dict:
    try:
        process = psutil.Process(pid)
        process.terminate()
        try:
            process.wait(timeout=5)
        except psutil.TimeoutExpired:
            os.kill(pid, signal.SIGTERM)
        return {"success": True, "pid": pid}
    except Exception as exc:
        return {"success": False, "pid": pid, "error_message": str(exc)}
