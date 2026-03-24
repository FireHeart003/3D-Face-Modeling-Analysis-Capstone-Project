import trimesh
from pathlib import Path
import shutil

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

    # Copy MTL and textures next to the OBJ so trimesh can find them
    _copy_materials(obj_path)

    scene = trimesh.load(str(obj_path), force="scene")
    scene.export(str(glb_path))

    print(f"Converted: {obj_path.name} to {glb_path.name}")

    return glb_path

def _copy_materials(obj_path):
    """
    Reads the mtllib line from the OBJ, finds the MTL file,
    then copies the MTL and all its textures next to the OBJ.
    """
    obj_path = Path(obj_path)
    obj_dir  = obj_path.parent

    # Find the mtllib line
    mtl_name = None
    with open(obj_path) as f:
        for line in f:
            if line.startswith("mtllib "):
                mtl_name = line.split(maxsplit=1)[1].strip()
                break

    if not mtl_name:
        print("No mtllib found, skipping material copy")
        return

    # Search for the MTL file — check next to OBJ first, then assets folder
    search_dirs = [
        obj_dir,
        Path("tests/assets/makehuman_raw"),
    ]

    mtl_path = None
    for d in search_dirs:
        candidate = d / mtl_name
        if candidate.exists():
            mtl_path = candidate
            break

    if not mtl_path:
        print(f"MTL file {mtl_name} not found, skipping material copy")
        return

    # Copy MTL next to OBJ if not already there
    dest_mtl = obj_dir / mtl_name
    if not dest_mtl.exists():
        shutil.copy(mtl_path, dest_mtl)
        print(f"Copied {mtl_name}")

    # tex_name is e.g. "textures/skin.png" — relative to where MTL lives
    asset_root = mtl_path.parent

    with open(mtl_path) as f:
        for line in f:
            if line.strip().lower().startswith("map_"):
                tex_name = line.split(maxsplit=1)[1].strip()
                tex_src  = asset_root / tex_name
                tex_dst  = obj_dir / tex_name

                if tex_src.exists() and not tex_dst.exists():
                    tex_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(tex_src, tex_dst)
                    print(f"Copied texture: {tex_name}")