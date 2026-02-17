from pathlib import Path
from src.face import Face

OUT_DIR = Path("out_face_week2")

if OUT_DIR.exists():
    import shutil
    shutil.rmtree(OUT_DIR)

face = Face.from_makehuman_identity("identity_model.mhm")

face.add_makehuman_expression("expression_model.mhpose")

face.add_renderable(
    model="makehuman",
    name="default",
    mesh="tests/assets/test_mesh.obj",
    textures_dir="tests/assets/textures"
)

face.save(OUT_DIR)

loaded = Face.load(OUT_DIR)

loaded.validate(OUT_DIR)

mesh_path = OUT_DIR / "models" / "makehuman" / "renderables" / "default" / "test_mesh.obj"
textures_path = OUT_DIR / "models" / "makehuman" / "renderables" / "default" / "textures"

assert mesh_path.exists(), "Mesh was not copied"
assert textures_path.exists(), "Textures folder missing"

print("Week 2 PASS")