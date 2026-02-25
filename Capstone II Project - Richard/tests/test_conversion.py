# test_conversion.py
import trimesh

# Load your existing meshi a
mesh = trimesh.load("assets/makehuman_raw/mesh.obj")

# Export as GLB
mesh.export("test_output.glb")

print("Conversion successful! Check test_output.glb")