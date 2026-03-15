from face_renderer.obj_to_glb import convert_obj_to_glb
from face_renderer import _renderer
from PIL import Image

# Convert the MakeHuman face
glb = convert_obj_to_glb("tests/assets/makehuman_raw/mesh.obj")

# Render it at higher resolution
renderer = _renderer.FilamentRenderer()
img = renderer.render(str(glb), 512, 512)

Image.fromarray(img, 'RGBA').save('results/face_rendered.png')
print("Face rendered to results/face_rendered.png!")