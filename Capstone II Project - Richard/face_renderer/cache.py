import hashlib
from pathlib import Path
from face_renderer.obj_to_glb import obj_to_glb

CACHE_DIR = Path.home() / ".cache" / "face_renderer"

# Create the file only if it is not cached. If it is cached, return the path
def get_cached_glb(obj_path):
    obj_path = Path(obj_path)

    # Hash the obj file to create unique cache path
    hash = hashlib.sha256(obj_path.read_bytes()).hexdigest()

    cached_glb = CACHE_DIR / f"{hash}.glb"

    if cached_glb.exists():
        print(f"Cache hit - reusing {cached_glb.name}")
    else:
        print(f"Cache miss - converting {obj_path.name} to {cached_glb.name}")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        obj_to_glb(obj_path, cached_glb)
    return cached_glb

    