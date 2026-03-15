# face_renderer/obj_to_glb.py
from __future__ import annotations

from pathlib import Path
import trimesh

from .cache import default_cache_dir, sha256_file


class ObjToGlbError(RuntimeError):
    pass


def obj_to_glb_cached(obj_path: str | Path, cache_dir: str | Path | None = None) -> Path:
    obj_path = Path(obj_path)
    if not obj_path.exists():
        raise FileNotFoundError(f"OBJ not found: {obj_path}")

    cache_root = Path(cache_dir) if cache_dir is not None else default_cache_dir()
    cache_root.mkdir(parents=True, exist_ok=True)

    key = sha256_file(obj_path)
    out_glb = cache_root / f"{obj_path.stem}-{key[:16]}.glb"

    if out_glb.exists() and out_glb.stat().st_size > 0:
        return out_glb

    # Load OBJ (as scene or mesh)
    try:
        loaded = trimesh.load(obj_path, force="scene")
    except Exception as e:
        raise ObjToGlbError(f"Failed to load OBJ via trimesh: {e}") from e

    if loaded is None:
        raise ObjToGlbError("trimesh.load returned None")

    # Export to GLB
    try:
        glb_bytes = loaded.export(file_type="glb")
    except Exception as e:
        raise ObjToGlbError(
            "Failed to export GLB. "
            "Try: pip install pygltflib, or ensure materials/textures are valid."
            f" Original error: {e}"
        ) from e

    if not glb_bytes:
        raise ObjToGlbError("GLB export produced empty output")

    out_glb.write_bytes(glb_bytes)
    return out_glb