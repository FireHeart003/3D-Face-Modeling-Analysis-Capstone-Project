import trimesh
from pathlib import Path
import hashlib

def convert_obj_to_glb(obj_path, output_path=None):
    """
    Convert OBJ file to GLB format.
    
    Args:
        obj_path: Path to input .obj file
        output_path: Path for output .glb file (optional)
    
    Returns:
        Path to the generated GLB file
    """
    obj_path = Path(obj_path)
    
    if output_path is None:
        # Save GLB in results folder
        output_path = Path("results") / obj_path.with_suffix('.glb').name
    
    output_path = Path(output_path)
    
    # Load mesh
    mesh = trimesh.load(str(obj_path))
    
    # Export as GLB
    mesh.export(str(output_path))
    
    return output_path

# Test it
if __name__ == "__main__":
    result = convert_obj_to_glb("tests/assets/test_mesh.obj")
    print(f"Created: {result}")