import trimesh
from pathlib import Path

'''
obj_path = input obj file
glb_path = output glb file

Use trimesh to convert obj file to glb format
Trimesh is great for converting files into different formats
'''
def obj_to_glb(obj_path, glb_path):
    obj_path = Path(obj_path)
    glb_path = Path(glb_path)

    glb_path.parent.mkdir(parents=True, exist_ok=True)

    mesh = trimesh.load(str(obj_path))
    mesh.export(str(glb_path))

    print(f"Converted: {obj_path.name} to {glb_path.name}")

    return glb_path