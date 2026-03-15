import sys
from pathlib import Path

sys.path.insert(0, ".")

from face_renderer.obj_to_glb import obj_to_glb

obj_to_glb("tests/assets/makehuman_raw/mesh.obj", "out_face_milestone3/test_output.glb")

'''
To verify successful conversion, run the following command where your Filament folder with GLTF Viewer is:
./filament/bin/gltf_viewer "/FullPathTo/Capstone 2/3D-Face-Modeling-Analysis-Capstone-Project/Capstone II Project - Richard/out_face_milestone3/test_output.glb"

'''