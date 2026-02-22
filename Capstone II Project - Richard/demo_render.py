from src.render_face import render_face

render_face(
    face_or_path="out_face_week2",
    out_path="preview.png",
    image_size=512,
    n_frames=1,
    yaw_degrees=20,
    pitch_degrees=0,
    roll_degrees=0,
    device="cpu"   # use cpu on Mac
)