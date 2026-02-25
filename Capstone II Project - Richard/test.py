from face_renderer import _renderer
from PIL import Image

# Create renderer
renderer = _renderer.FilamentRenderer()

# Render the GLB
img = renderer.render('results/test_mesh.glb', 256, 256)

# Save the image
Image.fromarray(img, 'RGBA').save('results/rendered_output.png')
print(f'Rendered image: {img.shape}')
print('Saved to results/rendered_output.png')