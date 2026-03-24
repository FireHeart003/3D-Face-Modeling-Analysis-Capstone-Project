import sys
from pathlib import Path

sys.path.insert(0, ".")

from face_renderer.obj_to_glb import obj_to_glb
from face_renderer.make_head_only import make_head_only_obj, build_head_face_mask_by_y

OBJ_IN = "tests/assets/makehuman_raw/mesh.obj"
OBJ_OUT = "out_face_milestone3/head_only.obj"
GLB_OUT = "out_face_milestone3/test_output.glb"
FOLDER_OUT = "out_face_milestone3"

'''
To verify successful conversion, run the following command where your Filament folder with GLTF Viewer is:
./filament/bin/gltf_viewer "/FullPathTo/Capstone 2/3D-Face-Modeling-Analysis-Capstone-Project/Capstone II Project - Richard/out_face_milestone3/test_output.glb"

'''

# Step 1: build face mask
print("Building face mask...")
mask = build_head_face_mask_by_y(OBJ_IN, keep_top_percent=0.22)
print(f"✅ {len(mask)} head faces selected")

# Step 2: generate head-only OBJ
print("\nGenerating head-only OBJ...")
make_head_only_obj(OBJ_IN, OBJ_OUT, mask)
print(f"✅ Written to {OBJ_OUT}")

# Step 3: verify OBJ indices are correct
print("\nVerifying OBJ indices...")
verts, uvs, faces = [], [], []
with open(OBJ_OUT) as f:
    for line in f:
        if line.startswith("v "):   verts.append(line)
        elif line.startswith("vt "): uvs.append(line)
        elif line.startswith("f "):  faces.append(line)

errors = []
for fl in faces:
    for tok in fl.split()[1:]:
        parts = tok.split("/")
        vi  = int(parts[0])
        vti = int(parts[1]) if len(parts) > 1 and parts[1] else None
        if vi > len(verts):
            errors.append(f"vertex index {vi} out of bounds")
        if vti is not None and vti > len(uvs):
            errors.append(f"UV index {vti} out of bounds")

if errors:
    print(f"❌ {len(errors)} index errors found!")
    for e in errors[:5]:
        print(f"   {e}")
else:
    print(f"✅ All indices valid ({len(verts)} verts, {len(uvs)} UVs, {len(faces)} faces)")

# Step 4: convert to GLB
print("\nConverting to GLB...")
obj_to_glb(OBJ_OUT, GLB_OUT)
print(f"✅ GLB written to {GLB_OUT}")

# Step 5: verify GLB exists and has content
glb = Path(GLB_OUT)
assert glb.exists(), "❌ GLB file was not created"
assert glb.stat().st_size > 1000, "❌ GLB file is suspiciously small"
print(f"✅ GLB size: {glb.stat().st_size / 1024:.1f} KB")

print("\n✅ Full head conversion pipeline working!")
print(f"\nTo verify visually, run from your Downloads folder:")
print(f'./filament/bin/gltf_viewer "{Path(GLB_OUT).resolve()}"')