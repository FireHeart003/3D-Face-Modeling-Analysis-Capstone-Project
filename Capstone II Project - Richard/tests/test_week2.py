from pathlib import Path
from src.face import Face

OUT_DIR = Path("out_face_week2")

#  Makes sure the directory is clean and doesn't have pre-existing files
if OUT_DIR.exists():
    import shutil
    shutil.rmtree(OUT_DIR)

face = Face.from_makehuman_identity("tests/assets/makehuman_raw/identity_model.mhm")

face.add_makehuman_expression("tests/assets/makehuman_raw/expression_model.mhpose")

face.add_renderable(
    model="makehuman",
    name="default",
    mesh="tests/assets/makehuman_raw/mesh.obj",
    mtl="tests/assets/makehuman_raw/mesh.mtl",
    textures_dir="tests/assets/makehuman_raw/textures"
)

face.save(OUT_DIR)

'''
This is to test if validation will fail if mesh is missing
mesh_path = OUT_DIR / "models" / "makehuman" / "renderables" / "default" / "mesh.obj"
mesh_path.unlink()  # Delete the file

To test if texture is provided but OBJ has no UV's, delete the vt lines temporarily for testing 
'''

loaded = Face.load(OUT_DIR)
loaded.validate(OUT_DIR)

# Use export_assets = False to avoid recopying assets
loaded.save(OUT_DIR, export_assets=False)

mesh_path = OUT_DIR / "models" / "makehuman" / "renderables" / "default" / "mesh.obj"
textures_path = OUT_DIR / "models" / "makehuman" / "renderables" / "default" / "textures"

assert mesh_path.exists(), "Mesh was not copied"
assert textures_path.exists(), "Textures folder missing"

print("Week 2 PASS")