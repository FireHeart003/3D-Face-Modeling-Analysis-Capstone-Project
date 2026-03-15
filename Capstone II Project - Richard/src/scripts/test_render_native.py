import numpy as np
from pathlib import Path

from face_renderer.obj_to_glb import obj_to_glb_cached
from face_renderer._native_renderer import Renderer

# Use the GLB you already know works:
glb = obj_to_glb_cached(Path(__file__).resolve().parent / "makehuman_raw" / "head_only.obj")
print("GLB:", glb)

r = Renderer(512, 512)
r.load_model(str(glb))

img = r.render(yaw=0, pitch=0, roll=0)  # (H,W,4) uint8
print(img.shape, img.dtype)

# Save quick png (optional)
try:
    from PIL import Image
    Image.fromarray(img, mode="RGBA").save("native_render.png")
    print("Saved native_render.png")
except Exception as e:
    print("Install pillow to save PNG:", e)