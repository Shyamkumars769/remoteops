from pathlib import Path
from typing import Any


def list_directory(path: str = ".") -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {"path": path, "error_message": "path not found", "entries": []}
    entries = [
        {"name": entry.name, "is_dir": entry.is_dir(), "size": entry.stat().st_size if entry.is_file() else None}
        for entry in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    ]
    return {"path": path, "entries": entries}


def read_file(path: str, max_bytes: int = 1_000_000) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {"error_message": "not a file"}
    data = p.read_bytes()[:max_bytes]
    try:
        text = data.decode("utf-8")
        return {"path": path, "content": text, "encoding": "utf-8", "truncated": len(data) == max_bytes}
    except UnicodeDecodeError:
        import base64
        return {"path": path, "content_b64": base64.b64encode(data).decode(), "encoding": "base64", "truncated": len(data) == max_bytes}
