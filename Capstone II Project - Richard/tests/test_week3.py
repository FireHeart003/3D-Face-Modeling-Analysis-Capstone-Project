import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.make_head_only import make_head_only_obj
from src.render_face import render_face
from src.face import Face
import torch
import shutil

print("========== WEEK 3 FULL TEST ==========")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "tests" / "assets"
OUT_DIR = PROJECT_ROOT / "out_face_week2"

# ----------------------------------------
# MILESTONE 3A — HEAD-ONLY OBJ GENERATION
# ----------------------------------------

print("\n[1] Testing head-only OBJ generation...")

IN_OBJ = ASSETS_DIR / "test_mesh.obj"
HEAD_OBJ = ASSETS_DIR / "test_head.obj"

if HEAD_OBJ.exists():
    HEAD_OBJ.unlink()

make_head_only_obj(
    in_obj_path=str(IN_OBJ),
    out_obj_path=str(HEAD_OBJ),
    face_mask=[0]  # keep first face (minimal test)
)

assert HEAD_OBJ.exists(), "Head-only OBJ was not created."

print("Head-only OBJ generation PASS")


# ----------------------------------------
# MILESTONE 3B — LOAD FACE + RENDER
# ----------------------------------------

print("\n[2] Testing PyTorch3D rendering...")

if not OUT_DIR.exists():
    raise RuntimeError("out_face_week2 does not exist. Run Week 2 test first.")

print("CUDA available:", torch.cuda.is_available())

# Single frame render
render_face(
    face_or_path=str(OUT_DIR),
    model="makehuman",
    renderable="default",
    out_path="preview.png",
    image_size=512,
    n_frames=1,
    yaw_degrees=0.0,
    pitch_degrees=0.0,
    roll_degrees=0.0,
    device="cuda"
)

assert Path("preview.png").exists(), "Single frame render failed."

print("Single frame render PASS")


# ----------------------------------------
# MILESTONE 3C — MULTI-FRAME ORBIT
# ----------------------------------------

print("\n[3] Testing orbit render (multi-frame)...")

render_face(
    face_or_path=str(OUT_DIR),
    model="makehuman",
    renderable="default",
    out_path="orbit.png",
    image_size=512,
    n_frames=5,
    yaw_degrees=45.0,
    pitch_degrees=0.0,
    roll_degrees=0.0,
    device="cuda"
)

for i in range(5):
    frame_path = Path(f"orbit_{i:03d}.png")
    assert frame_path.exists(), f"Missing orbit frame {i}"

print("Multi-frame orbit render PASS")


print("\n========== WEEK 3 COMPLETE ==========")