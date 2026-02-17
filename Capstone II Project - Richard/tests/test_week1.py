from src.face import Face

face = Face.from_makehuman_identity("identity_model.mhm")
face.save("out_face_week1")

face2 = Face.load("out_face_week1")

print("Week 1 PASS")