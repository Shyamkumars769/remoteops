import subprocess


def run_command(command: str) -> dict:
    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
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
            "error_message": "Command timed out after 300 seconds.",
        }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "error_message": str(exc),
        }
