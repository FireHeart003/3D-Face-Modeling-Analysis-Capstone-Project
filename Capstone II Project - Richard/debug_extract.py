from face_renderer.make_head_only import make_head_only_obj, build_head_face_mask_by_y

OBJ_IN  = "tests/assets/makehuman_raw/mesh.obj"
OBJ_OUT = "out_face_milestone3/head_only.obj"

mask = build_head_face_mask_by_y(OBJ_IN, keep_top_percent=0.13)
make_head_only_obj(OBJ_IN, OBJ_OUT, mask)

print("Done: wrote", OBJ_OUT)