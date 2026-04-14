import hashlib
import os
from pathlib import Path

from face_renderer.obj_to_glb import obj_to_glb
from face_renderer.make_head_only import make_head_only_obj, build_head_face_mask_by_y

CACHE_DIR = Path(os.environ.get("FACE_RENDERER_CACHE", Path.home() / ".cache" / "face_renderer"))


def _file_sha256(path: Path, chunk: int = 1 << 20) -> str:
    """Return SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def get_cached_head_obj(obj_path: Path, keep_top_percent: float = 0.13) -> Path:
    """
    Return path to a head-only OBJ, building it if not already cached.
    Cache key = sha256(source OBJ) + keep_top_percent.
    """
    obj_path = Path(obj_path)
    src_hash = _file_sha256(obj_path)
    pct_str  = f"{keep_top_percent:.4f}".replace(".", "p")
    cache_key = f"{src_hash[:16]}_{pct_str}"

    head_obj = CACHE_DIR / "objs" / f"{cache_key}_head.obj"

    if head_obj.exists():
        print(f"Cache hit  - reusing head OBJ {head_obj.name}")
        return head_obj

    print(f"Cache miss - building head OBJ from {obj_path.name}")
    head_obj.parent.mkdir(parents=True, exist_ok=True)
    mask = build_head_face_mask_by_y(str(obj_path), keep_top_percent=keep_top_percent)
    make_head_only_obj(str(obj_path), str(head_obj), mask)
    return head_obj


def get_cached_glb(obj_path: Path) -> Path:
    """
    Return path to a GLB, converting from OBJ if not already cached.
    Cache key = sha256(OBJ file).
    """
    obj_path = Path(obj_path)
    src_hash = _file_sha256(obj_path)
    cached_glb = CACHE_DIR / "glbs" / f"{src_hash[:16]}.glb"

    if cached_glb.exists():
        print(f"Cache hit  - reusing GLB {cached_glb.name}")
        return cached_glb

    print(f"Cache miss - converting {obj_path.name} → {cached_glb.name}")
    cached_glb.parent.mkdir(parents=True, exist_ok=True)
    obj_to_glb(obj_path, cached_glb)
    return cached_glb