"""
Generic JSON snapshot storage, namespaced per platform (currently just X).
"""

import json
from pathlib import Path
from typing import Any


def snapshot_path(snapshot_dir: str, platform: str) -> Path:
    return Path(snapshot_dir) / f"{platform}_snapshot.json"


def load_snapshot(snapshot_dir: str, platform: str) -> Any:
    path = snapshot_path(snapshot_dir, platform)
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_snapshot(snapshot_dir: str, platform: str, data: Any) -> None:
    path = snapshot_path(snapshot_dir, platform)
    path.write_text(json.dumps(data, indent=2))
