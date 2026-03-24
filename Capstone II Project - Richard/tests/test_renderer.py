import sys
from pathlib import Path
sys.path.insert(0, ".")

from face_renderer.filament_renderer import FaceRenderer
from face_renderer.make_head_only import make_head_only_obj, build_head_face_mask_by_y
from face_renderer.obj_to_glb import obj_to_glb
from PIL import Image

OBJ_IN  = "tests/assets/makehuman_raw/mesh.obj"
OBJ_OUT = "out_face_milestone3/head_only.obj"
GLB_OUT = "out_face_milestone3/head_only.glb"

# Step 1: build head-only GLB
print("Building head-only mesh...")
mask = build_head_face_mask_by_y(OBJ_IN, keep_top_percent=0.13)
make_head_only_obj(OBJ_IN, OBJ_OUT, mask)
obj_to_glb(OBJ_OUT, GLB_OUT)
print("✅ GLB ready")

# Step 2: create renderer
print("Creating renderer...")
renderer = FaceRenderer(512, 512, "filament_dist")
print("✅ Renderer created")

# Step 3: load model
print("Loading model...")
renderer.load_model(GLB_OUT)
print("✅ Model loaded")

# Step 4: set camera
print("Setting camera...")
renderer.set_camera(yaw=0.0, pitch=0.0, radius=150.0)
print("✅ Camera set")

# Step 5: render
print("Rendering...")
image = renderer.render(512, 512)
print(f"✅ Got image: shape={image.shape} dtype={image.dtype}")

# Step 6: save
img = Image.fromarray(image, 'RGBA')
img.save("out_face_milestone3/preview.png")
print("✅ Saved preview.png")