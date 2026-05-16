from pathlib import Path


def list_directory(path: str) -> dict:
    target = Path(path)
    entries = [
        {"name": entry.name, "is_dir": entry.is_dir()}
        for entry in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    ]
    return {"path": path, "entries": entries}
