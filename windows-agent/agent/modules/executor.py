import subprocess
from typing import Any


def run_command(command: str, timeout: int = 300) -> dict[str, Any]:
    """Unrestricted shell execution — kept as requested."""
    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "return_code": completed.returncode,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "return_code": -1,
            "error_message": f"Command timed out after {timeout} seconds.",
        }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error_message": str(exc),
        }
