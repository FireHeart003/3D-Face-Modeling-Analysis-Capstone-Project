"""
Run from project root:
  python3 diagnose.py out_face_milestone3/head_only.glb
"""
import sys
import pygltflib
import struct, base64, json
from pathlib import Path

glb_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out_face_milestone3/head_only.glb")
if not glb_path.exists():
    import glob
    hits = glob.glob(str(Path.home() / ".cache/face_renderer/*.glb"))
    glb_path = Path(hits[0]) if hits else None
    if not glb_path:
        print("No GLB found"); sys.exit(1)

gltf = pygltflib.GLTF2().load(str(glb_path))

print("=== Node hierarchy ===")
for i, node in enumerate(gltf.nodes):
    mesh_name = gltf.meshes[node.mesh].name if node.mesh is not None else None
    print(f"  Node[{i}] '{node.name}' mesh={mesh_name!r} "
          f"t={node.translation} s={node.scale} children={node.children}")

print("\n=== Mesh accessor min/max (vertex bounds) ===")
# Get binary buffer
blob = gltf.binary_blob()

for mi, mesh in enumerate(gltf.meshes):
    for pi, prim in enumerate(mesh.primitives):
        pos_idx = prim.attributes.POSITION
        if pos_idx is None:
            continue
        acc = gltf.accessors[pos_idx]
        print(f"  Mesh[{mi}] '{mesh.name}' prim[{pi}]: "
              f"POSITION min={acc.min}  max={acc.max}  count={acc.count}")