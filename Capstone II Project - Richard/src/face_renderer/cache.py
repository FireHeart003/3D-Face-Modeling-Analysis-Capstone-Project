# face_renderer/cache.py
from __future__ import annotations

import hashlib
import os
from pathlib import Path


def default_cache_dir() -> Path:
    # Cross-platform cache location
    root = os.environ.get("XDG_CACHE_HOME")
    if root:
        return Path(root) / "face_renderer"
    return Path.home() / ".cache" / "face_renderer"


def sha256_file(path: str | Path) -> str:
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()