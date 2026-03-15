from pathlib import Path
from face_renderer.make_head_only import build_head_face_mask_by_y, make_head_only_obj
from face_renderer.obj_to_glb import obj_to_glb_cached

SCRIPT_DIR = Path(__file__).resolve().parent
base = SCRIPT_DIR / "makehuman_raw"     # scripts/makehuman_raw
full_obj = base / "mesh.obj"
head_obj = base / "head_only.obj"

mask = build_head_face_mask_by_y(full_obj, keep_top_percent=0.22)
make_head_only_obj(full_obj, head_obj, mask)

glb = obj_to_glb_cached(head_obj)
print("GLB:", glb)