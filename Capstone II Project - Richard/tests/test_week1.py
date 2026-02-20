from src.face import Face

# Run test using: PYTHONPATH=. python3 tests/test_week1.py  

# Save JSON file
face = Face.from_makehuman_identity("tests/assets/identity_model.mhm")
face.save("out_face_week1/saved_json_file")

# Load that JSON file and save in other folder
face2 = Face.load("out_face_week1/saved_json_file")
face2.save("out_face_week1/load_json_file")

# Test if the first face and the second face are the same
if face.data == face2.data:
    print("Week 1 PASS")
else:
    print("Week 1 FAIL")