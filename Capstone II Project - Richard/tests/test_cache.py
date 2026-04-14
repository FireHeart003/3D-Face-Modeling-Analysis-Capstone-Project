import sys
from pathlib import Path

sys.path.insert(0, ".")

from face_renderer.cache import get_cached_glb

path = get_cached_glb("tests/assets/makehuman_raw/mesh.obj")
print(f"GLB at: {path.name}")

path2 = get_cached_glb("tests/assets/makehuman_raw/mesh.obj")
print(f"GLB at: {path2}")

assert path == path2
print("Successful Cache Implementation")