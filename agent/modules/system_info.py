import platform
import socket

import psutil


def collect_system_info() -> dict:
    interfaces: dict[str, list[str]] = {}
    for name, addrs in psutil.net_if_addrs().items():
        interfaces[name] = [addr.address for addr in addrs if addr.address]

    memory = psutil.virtual_memory()
    return {
        "os": {
            "name": platform.system(),
            "version": platform.version(),
            "release": platform.release(),
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
        "network": {"interfaces": interfaces},
    }
