from face_renderer import _renderer
from PIL import Image
import traceback

try:
    print("Creating renderer...")
    renderer = _renderer.FilamentRenderer()
    
    print("Starting render...")
    img = renderer.render('results/test_mesh.glb', 256, 256)
    
    print(f"Render complete! Image shape: {img.shape}")
    
    # Save the image
    Image.fromarray(img, 'RGBA').save('results/rendered_output.png')
    print('Saved to results/rendered_output.png')
    
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()