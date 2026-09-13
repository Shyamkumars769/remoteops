"""Interactive full-access session handler for the agent.

Provides real PTY shell + file operations over the WebSocket bridge.
"""
from __future__ import annotations

import asyncio
import base64
import os
import struct
import threading
from pathlib import Path
from typing import Any, Optional

from agent.logging import session_logger

try:
    import pty
    import select
    import termios
    import tty
    HAS_PTY = True
except ImportError:
    HAS_PTY = False


class SessionHandler:
    """Handles one interactive session: shell + file ops."""

    def __init__(self, session_id: str, send_fn):
        """
        send_fn: async callable that accepts a dict and sends it to the server.
        """
        self.session_id = session_id
        self.send = send_fn
        self._master_fd: Optional[int] = None
        self._pid: Optional[int] = None
        self._running = False
        self._shell_thread: Optional[threading.Thread] = None

    def start_shell(self, shell: str | None = None) -> None:
        if not HAS_PTY:
            asyncio.get_event_loop().create_task(
                self.send({"type": "error", "message": "PTY not available on this platform"})
            )
            return

        shell = shell or os.environ.get("SHELL", "/bin/bash")
        pid, master_fd = pty.fork()
        if pid == 0:
            # Child
            os.execvp(shell, [shell])
        else:
            self._pid = pid
            self._master_fd = master_fd
            self._running = True
            self._shell_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._shell_thread.start()
            session_logger.info("PTY started session_id=%s pid=%s", self.session_id, pid)

    def _read_loop(self) -> None:
        assert self._master_fd is not None
        loop = asyncio.new_event_loop()
        while self._running:
            try:
                r, _, _ = select.select([self._master_fd], [], [], 0.2)
                if not r:
                    continue
                data = os.read(self._master_fd, 4096)
                if not data:
                    break
                text = data.decode("utf-8", errors="replace")
                loop.run_until_complete(self.send({"type": "stdout", "data": text}))
            except OSError:
                break
        self._running = False
        loop.run_until_complete(self.send({"type": "shell_exit"}))

    def write_shell(self, data: str) -> None:
        if self._master_fd is not None and self._running:
            try:
                os.write(self._master_fd, data.encode("utf-8", errors="replace"))
            except OSError as e:
                session_logger.error("write_shell error: %s", e)

    def resize(self, rows: int, cols: int) -> None:
        if self._master_fd is None:
            return
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            import fcntl
            fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

    def stop(self) -> None:
        self._running = False
        if self._pid:
            try:
                os.kill(self._pid, 9)
            except OSError:
                pass
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass

    # ----- file operations (full access) -----

    def handle_message(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        t = msg.get("type")
        if t == "stdin":
            self.write_shell(msg.get("data", ""))
            return None
        if t == "resize":
            self.resize(int(msg.get("rows", 24)), int(msg.get("cols", 80)))
            return None
        if t == "start_shell":
            self.start_shell(msg.get("shell"))
            return {"type": "shell_started"}
        if t == "list_dir":
            return self._list_dir(msg.get("path", "."))
        if t == "read_file":
            return self._read_file(msg.get("path", ""), int(msg.get("max_bytes", 1_000_000)))
        if t == "write_file":
            return self._write_file(msg.get("path", ""), msg.get("content", ""), msg.get("encoding", "utf-8"))
        if t == "delete_path":
            return self._delete(msg.get("path", ""))
        if t == "download_file":
            return self._download(msg.get("path", ""))
        return {"type": "error", "message": f"unknown type {t}"}

    def _list_dir(self, path: str) -> dict:
        p = Path(path)
        if not p.exists():
            return {"type": "list_dir_result", "path": path, "error": "not found"}
        entries = []
        for e in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                st = e.stat()
                entries.append({
                    "name": e.name,
                    "is_dir": e.is_dir(),
                    "size": st.st_size if e.is_file() else None,
                    "mode": oct(st.st_mode)[-3:],
                })
            except OSError:
                continue
        return {"type": "list_dir_result", "path": path, "entries": entries}

    def _read_file(self, path: str, max_bytes: int) -> dict:
        p = Path(path)
        if not p.is_file():
            return {"type": "read_file_result", "error": "not a file"}
        data = p.read_bytes()[:max_bytes]
        try:
            return {"type": "read_file_result", "path": path, "content": data.decode("utf-8"), "encoding": "utf-8"}
        except UnicodeDecodeError:
            return {
                "type": "read_file_result",
                "path": path,
                "content_b64": base64.b64encode(data).decode(),
                "encoding": "base64",
            }

    def _write_file(self, path: str, content: str, encoding: str) -> dict:
        p = Path(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if encoding == "base64":
                p.write_bytes(base64.b64decode(content))
            else:
                p.write_text(content, encoding="utf-8")
            return {"type": "write_file_result", "path": path, "ok": True}
        except Exception as e:
            return {"type": "write_file_result", "path": path, "ok": False, "error": str(e)}

    def _delete(self, path: str) -> dict:
        p = Path(path)
        try:
            if p.is_dir():
                import shutil
                shutil.rmtree(p)
            else:
                p.unlink()
            return {"type": "delete_result", "path": path, "ok": True}
        except Exception as e:
            return {"type": "delete_result", "path": path, "ok": False, "error": str(e)}

    def _download(self, path: str) -> dict:
        p = Path(path)
        if not p.is_file():
            return {"type": "download_result", "error": "not a file"}
        # For large files this should stream; simple version loads into memory with limit
        data = p.read_bytes()[:5_000_000]
        return {
            "type": "download_result",
            "path": path,
            "name": p.name,
            "content_b64": base64.b64encode(data).decode(),
            "size": len(data),
        }
