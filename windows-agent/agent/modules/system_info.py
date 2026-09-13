import platform
import socket
from typing import Any

import psutil


def collect_system_info() -> dict[str, Any]:
    interfaces: dict[str, list[str]] = {}
    for name, addrs in psutil.net_if_addrs().items():
        interfaces[name] = [addr.address for addr in addrs if addr.address]

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "os": {
            "name": platform.system(),
            "version": platform.version(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "hostname": socket.gethostname(),
        "cpu": {
            "cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "usage_percent": psutil.cpu_percent(interval=0.2),
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "used_percent": memory.percent,
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "used_percent": disk.percent,
        },
        "network": {"interfaces": interfaces},
    }
